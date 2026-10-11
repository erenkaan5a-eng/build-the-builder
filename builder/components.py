"""Fixed, parameterized platform components -> workflow JSON.

Every platform mechanic lives here and is the same on every build; bank-specific values, verbatim rule text and the
API field names come from policy.json (spec_extract.py). Mechanics observed on Freya (see research/deney-gunlugu.md):
- re-entered conversation nodes need on_enter_first_entry_only, or the entry line repeats (v6 identity loop);
- a list in a response is only available as flattened keys <node>_response.data.<list>.<i>.<field> (v4);
- tool arguments are stored as <tool>_args.<field>; hooks do not run when a call ends in an HTTP error;
- routing after a tool result needs a preceding assistant message (preSpeech provides one) (G1 probe);
- a code_exec tool receives its arguments in `params` (G1 probe).
"""
import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "runtime"))
import date_tool  # noqa: E402  (kept for its tests; the negotiation runtime supersedes it in the workflow)
import negotiation as NG  # noqa: E402

MAX_TURNS = 40


def embed(code, cfg):
    cfg_json = json.dumps(cfg, indent=1)
    out = code.replace("__CFG__", cfg_json)
    if "{{" in out or "}}" in out or '"""' in cfg_json:
        raise ValueError("generated code would contain '{{', '}}' or triple quotes")
    return out


def code_node(name, code, transitions, default):
    return {"name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": default, "on_enter": {"type": "silent"},
            "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {
                "code": {"type": "string", "default": code}, "timeout_ms": {"type": "number", "default": 10000}}}}}],
            "transitions": transitions + [{"target_node": default, "description": "always", "condition": {"operator": "always"}}]}


def cond(var, op, val):
    return {"logic": "or", "conditions": [{"variable": var, "operator": op, "operand": val}]}


def cond_true(*vars_):
    return {"logic": "or", "conditions": [{"variable": v, "operator": "equals", "operand": s} for v in vars_ for s in ("true", "True")]}


def conv(name, task, tools, transitions, on_enter=None, extraction=None):
    n = {"name": name, "node_type": "conversation", "task_message": task, "tools": tools,
         "on_enter": on_enter or {"type": "llm"}, "on_enter_first_entry_only": True,
         "max_node_turns": MAX_TURNS, "max_turn_transition": "wrap_up" if name != "wrap_up" else "hangup",
         "transitions": transitions + [{"target_node": name, "description": "stay", "condition": {"operator": "always"}}]}
    if extraction:
        n["extraction_schema"] = extraction
    return n


def api_tool(ts, op, body, desc, config=None, pre=None, post=None):
    o = ts["ops"][op]
    props = {"url": {"type": "string", "default": o["url"]}, "method": {"type": "string", "default": "POST"},
             "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
             "body": {"type": "object", "properties": body, "required": [k for k in o["required"] if k in body]}}
    t = {"type": "function", "config": config or {"timeoutMs": 12000, "maxRetries": 0},
         "function": {"name": op, "handler": "__function__:api_call", "description": desc, "parameters": {"type": "object", "properties": props}}}
    if pre:
        t["pre_process_code"] = pre
    if post:
        t["post_process_code"] = post
    return t


def model_field(ts, op, field, desc):
    s = ts["ops"][op]["request"][field]
    leaf = {"type": s.get("type", "string"), "description": desc + (" One of: " + ", ".join(s["enum"]) + "." if s.get("enum") else ""), "default": "{{" + field + "}}"}
    if s.get("enum"):
        leaf["enum"] = s["enum"]
    return leaf


# ---------------------------------------------------------------- code snippets (no '{{' or '}}' allowed inside)
CAL_HELPERS = r'''
import json, datetime, re
CFG = json.loads(r"""__CFG__""")
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
def sp(d):
    return DAYS[d.weekday()] + ' ' + str(d.day) + ' ' + MONTHS[d.month - 1] + ' ' + str(d.year)
def isbd(d):
    return d.weekday() not in CFG['weekend_days'] and d.isoformat() not in CFG['holidays']
def nbd(d):
    d = d + datetime.timedelta(days=1)
    while not isbd(d):
        d = d + datetime.timedelta(days=1)
    return d
def add_bd(d, n):
    for i in range(int(n)):
        d = nbd(d)
    return d
def last_bd(monday):
    best = None
    for i in range(7):
        x = monday + datetime.timedelta(days=i)
        if isbd(x):
            best = x
    return best
def now_dt():
    raw = str(vars.get(CFG['now_var']) or '')
    return datetime.datetime.strptime(raw[:16].replace(' ', 'T'), '%Y-%m-%dT%H:%M')
'''

SETUP_CODE = CAL_HELPERS + r'''
try:
    now = now_dt()
    t = now.date()
    mon = t - datetime.timedelta(days=t.weekday())
    lines = ['Today is ' + sp(t) + ' = ' + t.isoformat() + ', time ' + now.strftime('%H:%M') + ('' if isbd(t) else ' (today is not a business day)') + '.']
    for label, off in (('This calendar week', 0), ('Next calendar week', 7), ('The week after next', 14), ('Three weeks from now', 21)):
        m = mon + datetime.timedelta(days=off)
        days = []
        for i in range(7):
            x = m + datetime.timedelta(days=i)
            days.append(DAYS[i] + ' ' + str(x.day) + ' ' + MONTHS[x.month - 1] + ' = ' + x.isoformat() + ('' if isbd(x) else ' (not a business day)'))
        lines.append(label + ': ' + '; '.join(days) + '.')
    lines.append('Next business day: ' + sp(nbd(t)) + ' = ' + nbd(t).isoformat() + '.')
    vars['cal_text'] = '\n'.join(lines)
    cb = CFG.get('callback')
    if cb:
        hm = now.strftime('%H:%M')
        opts = []
        if 'today' in cb['days'] and isbd(t) and hm < cb['window_end']:
            opts.append('today ' + sp(t) + ' = ' + t.isoformat() + ', a time later than ' + hm + ' and from ' + cb['window_start'] + ' to ' + cb['window_end'])
        if 'next_business_day' in cb['days']:
            opts.append(sp(nbd(t)) + ' = ' + nbd(t).isoformat() + ', from ' + cb['window_start'] + ' to ' + cb['window_end'])
        vars['cb_text'] = 'A callback can be booked only for: ' + ' or '.join(opts) + ' (both times included). Any other day or time is outside the window.' if opts else 'No callback day is available.'
    else:
        vars['cb_text'] = 'The brief defines no callback window.'
    vars['dates_state'] = 'ok'
except Exception as e:
    vars['cal_text'] = 'The calendar is not available.'
    vars['cb_text'] = 'The callback window is not available.'
    vars['dates_state'] = 'missing'
    vars['setup_error'] = str(e)[:120]
'''

DEAL_CODE = CAL_HELPERS + r'''
import math
class Strict(dict):
    def __missing__(self, k):
        raise ValueError('naming field missing: ' + k)
def money(x):
    return '%.2f' % float(x)
def num(x, what):
    v = float(str(x))
    if not math.isfinite(v) or v < 0:
        raise ValueError(what + ' not a finite amount')
    return v
try:
    if str(vars.get(CFG['ok_var']) or '').strip().lower() != 'true':
        raise ValueError('account call not successful')
    t = now_dt().date()
    rx = re.compile('^' + re.escape(CFG['prefix']) + r'\.(\d+)\.(\w+)$')
    items = dict()
    for k in list(vars.keys()):
        m = rx.match(str(k))
        if m:
            items.setdefault(int(m.group(1)), dict())[m.group(2)] = vars.get(k)
    prods, lines, seen = [], [], set()
    for i in sorted(items):
        it = dict((k, ('' if v is None else str(v))) for k, v in items[i].items())
        pid = it.get(CFG['id'], '').strip()
        if not pid or pid in seen:
            raise ValueError('empty or repeated product id')
        seen.add(pid)
        typ = it.get(CFG['type'], '').strip()
        lr = float(it.get(CFG['days_late']))
        if not lr.is_integer():
            raise ValueError('days_late not a whole number')
        late = int(lr)
        due = num(it.get(CFG['past_due']), 'past_due')
        ff = CFG['floor_field'].get(typ)
        floor = num(it.get(ff), 'floor') if ff and it.get(ff, '') != '' else None
        if ff and floor is None:
            raise ValueError('floor field empty for ' + typ)
        for k in list(it.keys()):
            if 'last4' in k.lower() and it[k].isdigit() and len(it[k]) < 4:
                it[k] = it[k].zfill(4)
        band = [b for b in CFG['bands'] if b['min'] <= late <= b['max']]
        if not band:
            raise ValueError('no band for days_late ' + str(late))
        band = band[0]
        deadline = add_bd(t, band['deadline_business_days'])
        tmpl = CFG['naming'].get(typ)
        if not tmpl:
            raise ValueError('no spoken name for product type ' + typ)
        name = tmpl.format_map(Strict(it))
        p = dict(id=pid, type=typ, name=name, past_due=due, days_late=late, floor=floor, deadline=deadline.isoformat(), attempts=band.get('attempts'))
        line = ('- product_id ' + pid + ': ' + name + '; past-due amount ' + money(due) + '; days late ' + str(late)
                + ('; floor (lowest amount that can be recorded) ' + money(floor) if floor is not None else '')
                + '; deadline (latest promise date) ' + sp(deadline) + ' = ' + deadline.isoformat())
        prods.append(p)
        lines.append(line)
    if not prods:
        raise ValueError('no products in the account result')
    s = CFG['say']
    qa = s.get('answer_' + str(vars.get('pending_question') or '').strip().lower()) or ''
    sent = [qa, s['debt_intro']] + [s['product_line'].format(name=p['name'], amount=money(p['past_due']), days=str(p['days_late'])) for p in prods]
    sent.append(s['first_ask_one'] if len(prods) == 1 else s['first_ask_all'])
    vars['products_json'] = json.dumps(prods)
    vars['deal_text'] = '\n'.join(lines)
    vars['debt_say'] = ' '.join(x.strip() for x in sent if x and x.strip())
    vars['hardship_done'] = 'no'
    vars['hardship_early'] = 'yes' if str(vars.get('hardship_seen') or '').strip().lower() == 'yes' else 'no'
    vars['offer_named'] = 'no'
    vars['acct_state'] = 'ok'
except Exception as e:
    vars['deal_text'] = 'The account data is not available.'
    vars['acct_state'] = 'error'
    vars['acct_error'] = str(e)[:160]
'''

VERIFY_POST = r'''
import json
CFG = json.loads(r"""__CFG__""")
def yes(x):
    return str(x).strip().lower() == 'true'
try:
    if isinstance(result, dict):
        result.pop('header', None)
        d = result.get('data')
        if isinstance(d, dict):
            hint = d.get(CFG['hint']) if CFG.get('hint') else None
            rem = d.get(CFG['remaining']) if CFG.get('remaining') else None
            if hint and str(hint) in CFG['hints']:
                msg = 'Not a wrong answer. ' + CFG['hints'][str(hint)]
            elif not yes(d.get(CFG['ok'])):
                msg = 'The answer was not checked (it could not be read or the service refused it). It does not count as wrong. Ask for the same answer again.'
            elif yes(d.get(CFG['all_verified'])):
                msg = 'All security questions are passed. Say one short thank-you sentence and nothing about the account yet. Do not call a tool now.'
            elif yes(d.get(CFG['verified'])):
                msg = 'This answer is correct. Ask the next security question.'
            elif rem is not None and str(rem).strip() in ('0', '0.0'):
                msg = 'This answer is wrong and no tries are left: the identity check has failed. Follow the brief for a failed check.'
            else:
                msg = 'This answer is wrong' + ((', tries left: ' + str(rem)) if rem is not None else '') + '. Follow the brief: ask the same question again.'
            d['what_to_do_next'] = msg
except Exception:
    pass
'''

PROMISE_POST = r'''
import json
CFG = json.loads(r"""__CFG__""")
try:
    if isinstance(result, dict):
        result.pop('header', None)
        d = result.get('data')
        if isinstance(d, dict):
            if str(d.get(CFG['ok'])).strip().lower() == 'true':
                vars['promises_recorded'] = str(int(float(vars.get('promises_recorded') or 0)) + 1)
                d['what_to_do_next'] = 'The promise IS recorded.' + ((' Say exactly: "' + CFG['sentence'] + '"') if CFG['sentence'] else '') + ' Then continue as the brief says.'
            else:
                d['what_to_do_next'] = 'The promise was NOT recorded (the bank refused it). Do not call create_promise again for this product. Say plainly that it could not be recorded and follow the brief.'
except Exception:
    pass
'''

SIMPLE_POST = r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
except Exception:
    pass
'''

CLOSE_PRE = r'''
import json
CFG = json.loads(r"""__CFG__""")
try:
    b = config.get('body')
    if isinstance(b, dict):
        q = str(vars.get('transfer_to_agent_args.' + CFG['queue_field']) or '')
        t_ok = str(vars.get('transfer_to_agent_response.data.' + CFG['ok']) or '').lower() == 'true'
        rec = int(float(vars.get('promises_recorded') or 0))
        o, r = CFG['outcome'], CFG['reason']
        if t_ok and q in CFG['queue_reason']:
            b[o] = CFG['transferred']
            b[r] = CFG['queue_reason'][q]
        elif rec > 0:
            b[o] = CFG['promise']
        elif b.get(o) == CFG['promise']:
            fb = CFG['unrecorded']
            b[o] = fb['outcome']
            b[r] = fb['reason']
        if b.get(o) in CFG['no_reason']:
            b.pop(r, None)
        vars['close_sent'] = str(b.get(o)) + '/' + str(b.get(r, ''))
except Exception:
    pass
'''


# ---------------------------------------------------------------- the workflow
def rules_block(pol, *stages):
    out = []
    for s in stages:
        out += (pol.get("rules") or {}).get(s) or []
    return "\n".join("- " + r for r in out)


def build(pol, ts):
    B = pol["api_binding"]
    cv = pol["call_variables"]
    cid = "{{" + cv["customer_id"] + "}}"
    ok = B["success_field"]
    cal_cfg = {"now_var": cv["now"], "weekend_days": pol["calendar"]["weekend_days"], "holidays": pol["calendar"]["holidays"]}

    # tools
    def body_with_cid(op, extra):
        return {B["customer_id_param"]: {"type": "string", "default": cid}, **extra}

    v = B["verify"]
    verify_cfg = {"ok": ok, "verified": v["verified"], "all_verified": v["all_verified"], "remaining": v.get("remaining"),
                  "hint": v.get("hint"), "hints": (pol.get("identity") or {}).get("hints") or {}}
    qs = pol["identity"]["questions"]
    t_verify = api_tool(ts, "verify_identity", body_with_cid("verify_identity", {
        v["field_param"]: model_field(ts, "verify_identity", v["field_param"], "Which security question this answer is for."),
        v["answer_param"]: model_field(ts, "verify_identity", v["answer_param"], "The customer's answer, in the format the question needs: "
                                       + "; ".join(f"{q['field']}: {q.get('answer_format', '')}" for q in qs) + ".")}),
        "CALL it every time the customer answers a security question, once per answer. Then follow what_to_do_next in the result.",
        post=embed(VERIFY_POST, verify_cfg))
    pb = B["promise"]
    retries = int((pol.get("write_retries") or {}).get("create_promise") or 0)
    c = pol["closing"]
    close_cfg = {"outcome": B["close"]["outcome"], "reason": B["close"]["reason"], "ok": ok, "queue_field": B["transfer"]["queue"],
                 "queue_reason": c["queue_reason"], "transferred": c["transferred_outcome"], "promise": c["promise_outcome"],
                 "unrecorded": c["unrecorded_promise_fallback"], "no_reason": c.get("outcomes_without_reason") or []}
    t_close = api_tool(ts, "close_call", body_with_cid("close_call", {
        B["close"]["outcome"]: model_field(ts, "close_call", B["close"]["outcome"], "The outcome from the brief's closing table."),
        B["close"]["reason"]: model_field(ts, "close_call", B["close"]["reason"], "The reason from the brief's closing table (leave empty where the table lists none).")}),
        "CALL it exactly once, as the very last tool call. The goodbye line is spoken automatically when you call it; do not say goodbye yourself.",
        config={"timeoutMs": 12000, "maxRetries": 0, "preSpeech": {"mode": "static", "message": pol.get("goodbye_line") or "Thank you for your time. Goodbye.", "interruptible": False}},
        pre=embed(CLOSE_PRE, close_cfg), post=SIMPLE_POST)
    t_transfer = api_tool(ts, "transfer_to_agent", body_with_cid("transfer_to_agent", {
        B["transfer"]["queue"]: model_field(ts, "transfer_to_agent", B["transfer"]["queue"], "The queue the brief names for this case.")}),
        "CALL it only when the brief says to transfer the call, with the queue the brief names.", post=SIMPLE_POST)
    cb = B["callback"]
    t_callback = api_tool(ts, "schedule_callback", body_with_cid("schedule_callback", {
        cb["date"]: model_field(ts, "schedule_callback", cb["date"], "Callback date as YYYY-MM-DD, inside the window in your instructions."),
        cb["time"]: model_field(ts, "schedule_callback", cb["time"], "Callback time as HH:MM, inside the window.")}),
        "CALL it once when the person gave a day and time inside the callback window.", post=SIMPLE_POST)
    acct_node = "fetch_account"

    done = {"target_node": "hangup", "description": "the call was closed", "condition": cond("close_call_success_count", "greater_than", 0)}
    sysp = (f"You are {pol['bank_name']}'s digital assistant on a phone call. Speak {pol.get('language', 'English')}. At most two short sentences per turn. "
            "First answer any question in the customer's last message in one short sentence, as the rules require, then continue with your step. "
            "Call at most one tool per message, and after every tool result speak to the customer or call the next tool. "
            "Never invent figures, dates, ids or reasons. Never say an action was done unless its tool returned success; when a tool fails, say plainly that it was not done. "
            "When the brief says the call ends: thank the customer, say goodbye, then call close_call.\n"
            "RULES THAT ALWAYS APPLY (from the bank's brief, verbatim):\n" + rules_block(pol, "global"))

    first_q = qs[0]["ask"] if qs else "the first security question"
    ng = pol["negotiation"]
    hd = ng.get("hardship_definition") or "a hardship the bank's rules name"
    hardship_x = {"name": "hardship_seen", "type": "string", "enum_values": ["yes", "no"], "min_confidence": 0.7,
                  "description": "'yes' if the customer has said anywhere in this call that they face " + hd + "; otherwise 'no'."}
    # a date or an amount the customer names in the same message as a hardship must reach the negotiation code (A32 last
    # sentence): then the dialogue model sends the events and the code answers the hardship; otherwise code answers at once
    offer_x = {"name": "offer_named", "type": "string", "enum_values": ["yes", "no"], "min_confidence": 0.7,
               "description": "'yes' if the customer's LAST message names a day or an amount they could pay, or says they will pay today; otherwise 'no'."}
    hardship_route = {"target_node": "hardship_go", "description": "a hardship was mentioned and not yet answered, and no date or amount was named with it",
                      "condition": {"logic": "or", "conditions": [{"logic": "and", "conditions": [
                          {"variable": flag, "operator": "equals", "operand": "yes"},
                          {"variable": "hardship_done", "operator": "equals", "operand": "no"},
                          {"variable": "offer_named", "operator": "not_equals", "operand": "yes"}]} for flag in ("hardship_seen", "hardship_early")]}}
    nodes = {}
    nodes["setup"] = code_node("setup", embed(SETUP_CODE, {**cal_cfg, "callback": pol.get("callback")}),
                               [{"target_node": "setup_error", "description": "dates missing", "condition": cond("dates_state", "equals", "missing")}], "opening")
    te = c["technical_error"]
    nodes["setup_error"] = conv("setup_error", f"The current date is not available, so the call cannot continue. Do not mention any account. Say you are sorry there is a technical problem, thank them, say goodbye, then call close_call with outcome {te['outcome']} and reason {te['reason']}.",
                                [t_close], [done])
    speaker = [{"name": "speaker", "type": "string", "enum_values": ["self", "other"], "min_confidence": 0.7,
                "description": "'self' only when the person clearly confirmed being the customer the way these rules require; 'other' when someone else answered. Empty otherwise. Rules: "
                               + " ".join((pol.get("rules") or {}).get("opening") or [])[:1500]}]
    nodes["opening"] = conv("opening", "Stage: who is on the line. Your opening line was already said. Follow these rules:\n" + rules_block(pol, "opening")
                            + "\nWhen the brief says the call ends here, say what the brief requires, thank them, say goodbye, then call close_call with the brief's outcome and reason.",
                            [t_transfer, t_close],
                            [done, {"target_node": "identity", "description": "the customer confirmed", "condition": cond("speaker", "equals", "self")},
                             {"target_node": "third_party", "description": "someone else answered", "condition": cond("speaker", "equals", "other")}],
                            on_enter={"type": "tts", "text": pol["opening_line"]}, extraction=speaker)
    nodes["third_party"] = conv("third_party", "Stage: someone other than the customer is on the line. Callback window (computed): {{cb_text}}\nFollow these rules:\n"
                                + rules_block(pol, "third_party") + "\nCall schedule_callback only for a day and time inside the window. When the brief says the call ends, thank them, say goodbye, then call close_call with the brief's outcome and reason.",
                                [t_callback, t_transfer, t_close],
                                [done, {"target_node": "identity", "description": "the customer is now on the line", "condition": cond("speaker", "equals", "self")}],
                                on_enter={"type": "llm", "prompt": "Respond as the rules for this stage require, in one or two short sentences, without saying why you are calling."},
                                extraction=speaker)
    nodes["identity"] = conv("identity", "Stage: identity. Ask the security questions one at a time, in this order: "
                             + " ".join(f"({i + 1}) {q['ask']} [field {q['field']}, answer as {q.get('answer_format', '')}]" for i, q in enumerate(qs))
                             + ". After each answer CALL verify_identity and follow what_to_do_next. You cannot see the account yet.\nFollow these rules:\n" + rules_block(pol, "identity"),
                             [t_verify, t_transfer, t_close],
                             [done, {"target_node": acct_node, "description": "identity verified",
                                     "condition": cond_true(f"verify_identity_response.data.{v['all_verified']}")}],
                             on_enter={"type": "tts", "text": first_q},
                             extraction=[{"name": "pending_question", "type": "string", "enum_values": ["robot", "scam", "none"], "min_confidence": 0.6,
                                          "description": "What the customer's LAST message asks, if anything: 'robot' if it asks whether they are talking to a robot, a machine or an AI; "
                                                         "'scam' if it asks whether this call is a scam or genuine; otherwise 'none'."}, hardship_x])
    lst = B["account"]["list"]
    nodes[acct_node] = {"name": acct_node, "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "build_deal", "on_enter": {"type": "silent"},
                        "pre_actions": [{"type": "function", "config": {"timeoutMs": 12000, "maxRetries": 2}, "function": {"name": "get_account", "handler": "__function__:api_call", "description": "Get the account.",
                                         "parameters": {"type": "object", "properties": {"url": {"type": "string", "default": ts["ops"]["get_account"]["url"]}, "method": {"type": "string", "default": "POST"},
                                                                                         "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                                                                                         "body": {"type": "object", "properties": {B["customer_id_param"]: {"type": "string", "default": cid}}, "required": []}}}}}],
                        "transitions": [{"target_node": "build_deal", "description": "always", "condition": {"operator": "always"}}]}
    deal_cfg = {**cal_cfg, "prefix": f"{acct_node}_response.data.{lst}", "ok_var": f"{acct_node}_response.data.{ok}", "type": B["account"]["type"],
                "id": B["account"]["id"], "days_late": B["account"]["days_late"], "past_due": B["account"]["past_due"],
                "floor_field": pol["products"]["floor_field"], "naming": pol["products"]["naming"], "bands": pol["bands"],
                "say": {**{k: ng["say"][k] for k in ("debt_intro", "product_line", "first_ask_one", "first_ask_all")},
                        "answer_robot": ng["say"].get("robot_answer") or "", "answer_scam": ng["say"].get("scam_answer") or ""}}
    nodes["build_deal"] = code_node("build_deal", embed(DEAL_CODE, deal_cfg),
                                    [{"target_node": "account_error", "description": "account data missing", "condition": cond("acct_state", "equals", "error")}], "negotiate")
    nodes["account_error"] = conv("account_error", f"The account data could not be loaded. Do not state any amount. Say you are sorry you cannot access the account details now, thank them, say goodbye, then call close_call with outcome {te['outcome']} and reason {te['reason']}.",
                                  [t_close], [done])
    neg_cfg = {**cal_cfg, "turn_vars": ["negotiate.total_turns", "neg_relay.total_turns"], "ladder": ng["ladder"], "vague_asks": int(pol.get("vague_asks_before_deadline", 1)),
               "shared_date_clamps": bool(ng.get("shared_date_clamps_to_deadline")), "say": ng["say"],
               "rec_node": "record_one", "note_node": "note_one", "ok": ok, "retries": retries, "queue_field": B["transfer"]["queue"],
               "queue_reason": c["queue_reason"], "transferred": c["transferred_outcome"], "promise": c["promise_outcome"],
               "paid": c["paid_outcome"], "no_promise": c["no_promise_outcome"], "statuses": pol["statuses"],
               "no_reason": c.get("outcomes_without_reason") or [], "uses_notes": bool(pol.get("uses_notes")) and "add_note" in ts["ops"],
               "after_promise_sentence": pol.get("after_promise_sentence") or "", "goodbye": pol.get("goodbye_line") or "",
               "technical": te, "stop_close": int(pol.get("stop_statements_to_close") or 1)}
    t_event = {"type": "function", "config": {"timeoutMs": 10000, "preSpeech": {"mode": "static", "message": ng["say"]["checking"], "interruptible": False}},
               "function": {"name": "negotiation_event", "handler": "__function__:code_exec",
                            "description": "CALL it for every customer message about paying (see EVENTS in your instructions). The code decides the reply, which is read out after the call.",
                            "parameters": {"type": "object", "properties": {
                                "code": {"type": "string", "default": embed(NG.ENGINE, neg_cfg)}, "timeout_ms": {"type": "number", "default": 8000},
                                "events": {"type": "array", "description": "One item per product and statement, in the order the customer said them.",
                                           "items": {"type": "object", "properties": {
                                               "product_id": {"type": "string", "description": "product_id from FACTS, or 'all' when the customer clearly speaks about every product"},
                                               "type": {"type": "string", "enum": NG.EVENT_TYPES},
                                               "date": {"type": "string", "description": "YYYY-MM-DD read from CALENDAR, 'vague' for a period without an exact day, or empty"},
                                               "amount": {"type": "string", "description": "the amount the customer named, digits only, or empty"}},
                                               "required": ["product_id", "type"]}},
                                "answer": {"type": "string", "description": "only if the customer's message also asked a question the rules let you answer (for example whether you are a robot, or whether this is a scam): your one-sentence answer, without amounts or dates. Otherwise empty."}},
                                "required": ["events"]}}}
    t_transfer_neg = api_tool(ts, "transfer_to_agent", body_with_cid("transfer_to_agent", {
        B["transfer"]["queue"]: model_field(ts, "transfer_to_agent", B["transfer"]["queue"], "The queue the brief names for this case.")}),
        "CALL it only when the brief says to transfer the call, with the queue the brief names.",
        config={"timeoutMs": 12000, "maxRetries": 0, "preSpeech": {"mode": "static", "message": pol.get("transfer_line") or ng["say"]["checking"], "interruptible": False}},
        post=SIMPLE_POST)
    events_doc = ("EVENTS (one item per product and statement): pays_today = will pay today; refuses = says no or gives no answer to the offer just made, "
                  "with no date and no amount; too_much = says the full amount is too much; proposes = names a date and/or an amount (date YYYY-MM-DD from CALENDAR or 'vague', amount as digits); "
                  "accepts = yes to the offer just made; confirms = yes to the read-back just made; changes = changes the date or amount at the read-back; "
                  "hardship = mentions a hardship the rules name; declines_support = declines the support offer; dispute = says the debt is not theirs or the product was closed or paid off in the past; "
                  "paid = says this amount is already paid; stop = does not want to continue. A date or amount the customer names is proposes, never refuses.")
    nodes["negotiate"] = conv("negotiate",
                              "Stage: identity is verified; the debt and the promise.\nFACTS (from the account tool):\n{{deal_text}}\nCALENDAR (to turn the customer's words into YYYY-MM-DD):\n{{cal_text}}\n"
                              "YOUR JOB IN THIS STAGE: turn what the customer says about paying into events and CALL negotiation_event. The code decides every offer, amount, date, read-back and "
                              "recording, and its words are read out after the call. Never propose an amount or a date yourself, never say whether a date is allowed, never ask how much the customer can pay, "
                              "never say that anything is recorded. When you call negotiation_event, say nothing yourself in that message: the code's reply is read out right after the call. "
                              "If the customer's message also asked a question, put your one-sentence answer in the tool's answer field. For a hardship (also one mentioned earlier in the call), a dispute or an 'already paid' "
                              "statement, never answer it yourself: send the event; the code says the brief's sentences.\n" + events_doc + "\n"
                              "TRANSFER: when the rules say to transfer (for example a request for a new plan, a customer who insists on a person, or a customer who accepts the support offer), CALL transfer_to_agent with the rules' queue.\n"
                              "Questions that are not about paying: answer only the question, in one sentence, from FACTS and the rules, without a tool; never add an offer, a date, an amount to pay or a question about paying.\nRules for this stage (verbatim):\n" + rules_block(pol, "negotiate", "closing"),
                              [t_event, t_transfer_neg],
                              [hardship_route,
                               {"target_node": "rec_next", "description": "confirmed read-back", "condition": cond("neg_flag", "equals", "record")},
                               {"target_node": "finish_prep", "description": "nothing left to negotiate", "condition": cond("neg_flag", "equals", "finish")},
                               {"target_node": "neg_consume", "description": "a decision to read out", "condition": cond("neg_flag", "equals", "new")},
                               {"target_node": "finish_prep", "description": "the call was transferred", "condition": cond_true(f"transfer_to_agent_response.data.{ok}")}],
                              on_enter={"type": "tts", "text": "{{debt_say}}"},
                              extraction=[hardship_x, offer_x])
    nodes["neg_consume"] = code_node("neg_consume", "vars['neg_flag'] = 'used'\n", [], "neg_relay")
    relay = "Do not call any tool. Do not add anything to what was just said."
    rb_extract = [hardship_x, offer_x, {"name": "rb_answer", "type": "string", "enum_values": ["yes", "no"], "min_confidence": 0.7,
                   "description": "Only if the agent's last message was a read-back ending with the confirmation question: 'yes' when the customer clearly confirms it with no change, "
                                  "'no' when they reject or change it. Empty in every other case."}]
    nodes["neg_relay"] = {"name": "neg_relay", "node_type": "conversation", "on_enter": {"type": "tts", "text": "{{neg_say}}"}, "task_message": relay,
                          "extraction_schema": rb_extract, "max_node_turns": 5, "max_turn_transition": "negotiate",
                          "transitions": [hardship_route,
                                          {"target_node": "neg_confirm", "description": "the read-back was confirmed",
                                           "condition": {"logic": "or", "conditions": [{"logic": "and", "conditions": [
                                               {"variable": "rb_answer", "operator": "equals", "operand": "yes"},
                                               {"variable": "neg_phase", "operator": "equals", "operand": "readback"}]}]}},
                                          {"target_node": "negotiate", "description": "always", "condition": {"operator": "always"}}]}
    nodes["neg_confirm"] = code_node("neg_confirm", embed(NG.CONFIRM, neg_cfg),
                                     [{"target_node": "rec_next", "description": "confirmation of the current read-back", "condition": cond("neg_flag", "equals", "record")}], "negotiate")
    nodes["hardship_go"] = code_node("hardship_go", embed(NG.HARDSHIP, neg_cfg), [], "neg_relay")
    nodes["rec_next"] = code_node("rec_next", embed(NG.REC_NEXT, neg_cfg),
                                  [{"target_node": "record_one", "description": "a promise to send", "condition": cond("rec_go", "equals", "yes")},
                                   {"target_node": "negotiate", "description": "no confirmed package: nothing may be written", "condition": cond("rec_go", "equals", "blocked")}], "finish_prep")
    amt_f = pb["amount"]
    nodes["record_one"] = {"name": "record_one", "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "rec_next", "on_enter": {"type": "silent"},
                           "pre_actions": [api_tool(ts, "create_promise", body_with_cid("create_promise", {
                               pb["product"]: {"type": "string", "default": "{{rec_product}}"},
                               pb["amount"]: {"type": "number", "default": "{{rec_amount}}"},
                               pb["date"]: {"type": "string", "default": "{{rec_date}}"}}), "Record one confirmed promise.",
                               config={"timeoutMs": 12000, "maxRetries": 0},
                               pre="try:\n    b = config.get('body')\n    if isinstance(b, dict):\n        b['" + amt_f + "'] = float(str(vars.get('rec_amount')))\nexcept Exception:\n    pass\n")],
                           "transitions": [{"target_node": "rec_next", "description": "always", "condition": {"operator": "always"}}]}
    nodes["finish_prep"] = code_node("finish_prep", embed(NG.FINISH, neg_cfg),
                                     [{"target_node": "negotiate", "description": "products still unresolved: not ready to close", "condition": cond("fin_ready", "equals", "no")}], "finish_say")
    nodes["finish_say"] = {"name": "finish_say", "node_type": "conversation", "passthrough": True, "passthrough_default_transition": "notes_next",
                           "on_enter": {"type": "tts", "text": "{{fin_say}}"}, "task_message": "Do not call any tool.",
                           "transitions": [{"target_node": "notes_next", "description": "always", "condition": {"operator": "always"}}]}
    note_tr = []
    if neg_cfg["uses_notes"]:
        nb = B["note"]
        note_tr = [{"target_node": "note_one", "description": "a note to send", "condition": cond("note_go", "equals", "yes")}]
        nodes["note_one"] = {"name": "note_one", "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "notes_next", "on_enter": {"type": "silent"},
                             "pre_actions": [api_tool(ts, "add_note", body_with_cid("add_note", {nb["product"]: {"type": "string", "default": "{{note_product}}"},
                                                                                                 nb["reason"]: {"type": "string", "default": "{{note_reason}}"}}),
                                                      "Record one note.", config={"timeoutMs": 12000, "maxRetries": 0})],
                             "transitions": [{"target_node": "notes_next", "description": "always", "condition": {"operator": "always"}}]}
    nodes["notes_next"] = code_node("notes_next", embed(NG.NOTES_NEXT, neg_cfg), note_tr, "close_one")
    rf = B["close"]["reason"]
    nodes["close_one"] = {"name": "close_one", "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "close_check", "on_enter": {"type": "silent"},
                          "pre_actions": [api_tool(ts, "close_call", body_with_cid("close_call", {B["close"]["outcome"]: {"type": "string", "default": "{{fin_outcome}}"},
                                                                                                    rf: {"type": "string", "default": "{{fin_reason}}"}}),
                                                   "Close the call.", config={"timeoutMs": 12000, "maxRetries": 0},
                                                   pre="try:\n    b = config.get('body')\n    if isinstance(b, dict):\n        r = str(b.get('" + rf + "') or '').strip()\n        if not r or r.startswith('{'):\n            b.pop('" + rf + "', None)\nexcept Exception:\n    pass\n")],
                          "transitions": [{"target_node": "close_check", "description": "always", "condition": {"operator": "always"}}]}
    nodes["close_check"] = code_node("close_check", embed(NG.CLOSE_CHECK, neg_cfg), [], "hangup")
    nodes["wrap_up"] = conv("wrap_up", "The call must end now. Thank the customer, say goodbye, then call close_call with the outcome and reason from the brief's table that matches what happened.",
                            [t_close], [done])
    nodes["hangup"] = {"name": "hangup", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
                       "terminal": {"type": "function", "function": {"name": "call_closed", "handler": "__function__:end_call",
                                                                      "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}}}
    tv = {k: str(x) for k, x in (pol.get("test_variables") or {}).items() if k != cv["customer_id"]}
    return {"initial_node": "setup", "system_prompt": sysp, "nodes": nodes, "global_nodes": {}, "test_variables": tv}


def support_boundary(pol):
    """What the generated agent enforces in code and what it leaves to the dialogue model (for the manifest)."""
    ng = pol.get("negotiation") or {}
    return {
        "code": ["deadline per band (Nth business day after now, calendar from the policy)", "promise date validity (past / after deadline / non-business day)",
                 "vague period: ask " + str(int(pol.get("vague_asks_before_deadline", 1))) + " time(s), then the deadline",
                 "amount: full first, floor offer after 'too much' or a below-floor amount, accept floor..full",
                 "persuasion ladder per product: " + ", ".join(f"{x.get('amount')}@{x.get('date')}" for x in ng.get("ladder") or []),
                 "shared date clamped to each product's deadline" if ng.get("shared_date_clamps_to_deadline") else "shared date not clamped (policy)",
                 "read-back of the whole package, confirmation bound to that package, writes only from the confirmed package",
                 "create_promise retries: " + str(int((pol.get("write_retries") or {}).get("create_promise") or 0)) + " (single layer)",
                 "hardship: one code-owned sympathy+support offer, no persuasion afterwards, customer's own date/amount kept",
                 "stop statements before close: " + str(int(pol.get("stop_statements_to_close") or 1)),
                 "notes per product (" + ("used" if pol.get("uses_notes") else "not used by this brief") + "), none after a transfer; close outcome from recorded/transfer/product results",
                 "goodbye -> notes -> exactly one close_call in the negotiation path"],
        "model": ["turning the customer's words into events and dates into YYYY-MM-DD (calendar table given)",
                  "identity question order, re-asks, declines (bank result routes to the account step)",
                  "opening confirmation and its re-ask count", "third party, callback window validity and re-ask",
                  "transfer decision and queue (close mapping is code)", "questions outside payment (robot/scam answers come from the policy)"],
        "unsupported_by_code": [r.get("text") for r in pol.get("extra_rules") or [] if r.get("kind") in ("computational", "structural")],
    }


def known_gaps(pol):
    """Rules the generator leaves to the dialogue model (honest list for the trace)."""
    gaps = ["turning the customer's words into negotiation events (and dates into YYYY-MM-DD) is done by the dialogue model; offers, counters, dates, amounts, read-back, recording, notes and the close are code",
            "callback window validity is decided by the dialogue model from code-computed window facts (not code)",
            "identity flow (which question, re-asks, declines) follows the dialogue model with the bank's verification results"]
    for r in pol.get("extra_rules") or []:
        if r.get("kind") in ("computational", "stateful", "structural", "unknown"):
            gaps.append(f"extra rule ({r.get('kind')}, stage {r.get('stage')}): {r.get('text')} - left to the dialogue model's prompt")
    for cfl in pol.get("unresolved_conflicts") or []:
        gaps.append(f"unresolved conflict: {cfl.get('topic')}: chose {cfl.get('chosen')!r} ({cfl.get('why')})")
    return gaps

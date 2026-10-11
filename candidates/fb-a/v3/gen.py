import json, subprocess, sys, os

ROOT = r"C:\Users\ASUS\OneDrive\Masaüstü\build-the-builder"
WD = os.path.join(ROOT, "out", "fb-a-20261010-234939")
BASE = json.load(open(os.path.join(ROOT, "tools", "openapi.json"), encoding="utf-8"))["servers"][0]["url"]
HOL = ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"]

SYSTEM = """You are the digital assistant of Freya Bank on an outbound phone call. Speak English, one or two short sentences per turn, calm and polite. Address the customer as title plus last name.
- Call one tool per message. After every tool result you must speak to the customer or call the next tool; never end a turn with nothing. Follow the what_to_do_next line of every tool result.
- Never say an action is done unless the tool result says ok. If a call failed or returned no result, say plainly that nothing was saved.
- If asked whether you are a robot or an AI: say you are Freya Bank's digital assistant and continue.
- If asked whether this is a scam: say they can verify the call by phoning Freya Bank's customer service number, and continue.
- A question you cannot answer from the tools: say you do not have that information. Never invent figures, dates or reasons.
- Never offer a discount, a waiver, an instalment plan or any term that is not in your instructions."""


def t(s):
    return s


def api_fn(name, fields, desc, post, mapping=None, retries=0, tool=True):
    props = {}
    req = []
    for f in fields:
        n, typ, d, enum, default = f
        p = {"type": typ}
        if d:
            p["description"] = d
        if enum:
            p["enum"] = enum
        p["default"] = default
        props[n] = p
        if default.startswith("{{") and n not in ("customer_id",) and not default.startswith("{{prod") and not default.startswith("{{cb_"):
            req.append(n)
    fn = {
        "type": "function",
        "config": {"timeoutMs": 12000, "maxRetries": retries},
        "function": {
            "name": name, "handler": "__function__:api_call",
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "default": BASE + "/" + name},
                "method": {"type": "string", "default": "POST"},
                "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                "body": {"type": "object", "required": req, "properties": props}}},
        },
        "post_process_code": post,
    }
    if tool:
        fn["function"]["description"] = desc
    if mapping and tool:
        fn["response_mapping"] = mapping
    return fn


CID = ("customer_id", "string", "", None, "{{customer_id}}")

POST_HEAD = ("try:\n    if isinstance(result, dict):\n        result.pop('header', None)\n"
             "        d = result.get('data')\n        if not isinstance(d, dict):\n            d = dict()\n            result['data'] = d\n"
             "        ok = str(d.get('ok')).lower() == 'true'\n")
POST_TAIL = "except Exception:\n    pass\n"


def post(body):
    lines = "".join("        " + l + "\n" for l in body.strip("\n").split("\n"))
    return POST_HEAD + lines + POST_TAIL


POST_VERIFY = post("""
left = d.get('wrong_answers_left')
if d.get('hint') == 'day_month_swapped':
    d['what_to_do_next'] = 'Day and month look swapped. Ask the customer to say the month as a word and ask the same question again. This retry is not counted as a wrong answer.'
elif not ok:
    d['what_to_do_next'] = 'The answer was not accepted or the service failed. Nothing was counted. Ask the customer to say it again (date of birth with the month as a word).'
elif str(d.get('all_verified')).lower() == 'true':
    d['what_to_do_next'] = 'Both answers are verified. Say a short thank you and nothing about the account; the call moves on by itself.'
elif str(d.get('verified')).lower() == 'true':
    d['what_to_do_next'] = 'This answer is correct. Ask the next security question that has not been answered yet (phone last four digits after the date of birth).'
else:
    if str(left) == '0':
        d['what_to_do_next'] = 'Wrong answer and no tries are left. The check has ended: say the customer should use the mobile app or a branch, do not state any debt; the call closes by itself.'
    else:
        d['what_to_do_next'] = 'Wrong answer. ' + str(left) + ' wrong answers left. Ask the same question again.'
""")

POST_ACCT = post("""
if ok:
    d['what_to_do_next'] = 'Account loaded. The call moves on by itself.'
else:
    d['what_to_do_next'] = 'The account could not be loaded. Nothing was done.'
""")

POST_PROMISE = post("""
if ok:
    d['what_to_do_next'] = 'The promise IS recorded. The call moves on by itself and closes with the confirmation sentence.'
else:
    n = int(vars.get('promise_fail_n') or 0) + 1
    vars['promise_fail_n'] = str(n)
    if n >= 2:
        d['what_to_do_next'] = 'The promise was NOT recorded (nothing saved) and this was the second failure. The call closes by itself.'
    else:
        d['what_to_do_next'] = 'The promise was NOT recorded (nothing saved). Say you will try once more and call create_promise again with the same values.'
""")

POST_SIMPLE = post("""
if ok:
    d['what_to_do_next'] = 'Done. The call moves on by itself.'
else:
    d['what_to_do_next'] = 'Not done: nothing was saved.'
""")

POST_CLOSE = "try:\n    if isinstance(result, dict):\n        result.pop('header', None)\nexcept Exception:\n    pass\n"


def node(name, ntype="conversation", **kw):
    n = {"name": name, "node_type": ntype}
    n.update(kw)
    return n


def cond(var, op="equals", operand=None):
    c = {"variable": var, "operator": op}
    if operand is not None:
        c["operand"] = operand
    return c


def tr(target, desc, *conds, tool_call=False, intent=None):
    if intent:
        t_ = {"target_node": target, "description": desc, "condition": {"operator": "matches_intent", "description": intent}}
        if tool_call:
            t_["is_tool_call"] = True
        return t_
    flat = []
    for c in conds:
        flat.append(c)
    return {"target_node": target, "description": desc, "condition": {"logic": "or", "conditions": flat}}


def tf(target, desc, var):  # true / True on a variable (or several)
    vs = var if isinstance(var, list) else [var]
    cs = []
    for v in vs:
        cs.append(cond(v, "equals", "true"))
        cs.append(cond(v, "equals", "True"))
    return tr(target, desc, *cs)


def ff(target, desc, var):
    vs = var if isinstance(var, list) else [var]
    cs = []
    for v in vs:
        cs.append(cond(v, "equals", "false"))
        cs.append(cond(v, "equals", "False"))
    return tr(target, desc, *cs)


ALWAYS = lambda tgt: {"target_node": tgt, "description": "always", "condition": {"operator": "always"}}


def code_fn(code):
    assert "{{" not in code and "}}" not in code, code
    return {"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {
        "code": {"type": "string", "default": code}, "timeout_ms": {"type": "number", "default": 8000}}}}}


def code_node(name, code, nxt, transitions=None):
    return node(name, "code", passthrough=True, passthrough_default_transition=nxt, on_enter={"type": "silent"},
                disable_inactivity_monitor=True, pre_actions=[code_fn(code)],
                transitions=(transitions or []) + [ALWAYS(nxt)])


def api_node(name, fn, mapping, transitions, nxt):
    return node(name, "api_request", passthrough=True, passthrough_default_transition=nxt, on_enter={"type": "silent"},
                disable_inactivity_monitor=True, pre_actions=[fn], response_mapping=mapping, transitions=transitions + [ALWAYS(nxt)])


def ext(name, typ, desc, enum=None):
    e = {"name": name, "type": typ, "description": desc, "min_confidence": 0.65}
    if enum:
        e["enum_values"] = enum
    return e


def end_node(name, fname, msg):
    return node(name, "end_call", on_enter={"type": "silent"}, disable_inactivity_monitor=True, transitions=[],
                terminal={"type": "function", "function": {"name": fname, "handler": "__function__:end_call", "parameters": {"type": "object", "properties": {
                    "message_mode": {"type": "string", "default": "custom"}, "spoken_message": {"type": "string", "default": msg}}}}})


nodes = {}


def close_path(key, outcome, reason, msg):
    code = "try:\n    vars['outcome'] = %r\n    vars['reason'] = %r\nexcept Exception:\n    pass\n" % (outcome, reason)
    nodes["close_" + key] = code_node("close_" + key, code, "end_" + key)
    nodes["end_" + key] = end_node("end_" + key, "ended_" + key, msg)


BYE = " Thank you, goodbye."
close_path("promise", "promise", "", "Your promise is recorded. You will receive a text message confirming this promise." + BYE)
close_path("paid", "paid", "", "Payments can take one business day to appear, so I will not take a promise now." + BYE)
close_path("restructuring", "transferred", "restructuring", "I am transferring you to a colleague who can help with that." + BYE)
close_path("human", "transferred", "human", "I am transferring you to a colleague now." + BYE)
close_path("support", "transferred", "support", "I am transferring you to our customer support team now." + BYE)
close_path("refused", "no_promise", "refused", "I understand. I have not recorded any promise today." + BYE)
close_path("hardship", "no_promise", "hardship", "I understand. I have not recorded any promise today. Take care." + " Goodbye.")
close_path("dispute", "no_promise", "dispute", "I understand. I will not take a promise on this call." + BYE)
close_path("service_error", "no_promise", "service_error", "I am sorry, I could not complete that right now and nothing was saved. Please use the mobile app or a branch." + BYE)
close_path("promise_failed", "no_promise", "service_error", "I am sorry, I could not record your promise, nothing was saved. Please use the mobile app or a branch." + BYE)
close_path("failed", "not_verified", "failed", "I cannot continue because the security check was not passed. Please use the mobile app or a branch." + BYE)
close_path("declined", "not_verified", "declined", "I understand. I cannot continue without the security check. Please use the mobile app or a branch if you need help." + " Goodbye.")
close_path("callback", "not_reached", "callback", "Thank you, we will call back at the time you gave. Goodbye.")
close_path("no_callback", "not_reached", "no_callback", "I was not able to book a callback. Goodbye.")
close_path("wrong_number", "not_reached", "wrong_number", "I am sorry for the disturbance. Goodbye.")
close_path("deceased", "not_reached", "deceased", "I am sorry for your loss.")
close_path("unclear", "not_reached", "unclear", "I could not confirm who I am speaking with, so I will end the call. Goodbye.")

# ---------------- init -----------------
INIT = r'''
import datetime
HOL = %r
DN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
def sp(d):
    return DN[d.weekday()] + ' ' + str(d.day) + ' ' + MN[d.month - 1]
def isbd(d):
    return d.weekday() < 5 and d.isoformat() not in HOL
def nbd(d):
    d = d + datetime.timedelta(days=1)
    while not isbd(d):
        d = d + datetime.timedelta(days=1)
    return d
try:
    raw = str(vars.get('now') or '').strip()
    today = datetime.datetime.strptime(raw[:10], '%%Y-%%m-%%d').date()
    tm = raw[11:16] if len(raw) >= 16 else '00:00'
    monday = today - datetime.timedelta(days=today.weekday())
    lines = []
    lines.append('Today is ' + sp(today) + ' ' + str(today.year) + ' (' + today.isoformat() + '), current time ' + tm + '. Today is ' + ('' if isbd(today) else 'NOT ') + 'a business day.')
    lines.append('Tomorrow: ' + sp(today + datetime.timedelta(days=1)) + ' (' + (today + datetime.timedelta(days=1)).isoformat() + ').')
    for i in range(7):
        a = monday + datetime.timedelta(days=i)
        b = a + datetime.timedelta(days=7)
        lines.append('This ' + DN[i] + ' = ' + a.isoformat() + ' ; next ' + DN[i] + ' = ' + b.isoformat())
    lines.append('Next business day after today: ' + sp(nbd(today)) + ' (' + nbd(today).isoformat() + ').')
    lines.append('Business days are Monday to Friday except these bank holidays: ' + ', '.join(HOL) + '.')
    sunday = monday + datetime.timedelta(days=6)
    d = sunday
    while not isbd(d):
        d = d - datetime.timedelta(days=1)
    if d <= today:
        sunday = sunday + datetime.timedelta(days=7)
        d = sunday
        while not isbd(d):
            d = d - datetime.timedelta(days=1)
    vars['attempt1_iso'] = d.isoformat()
    vars['attempt1_spoken'] = sp(d)
    vars['cal_text'] = chr(10).join(lines)
    vars['now_date'] = today.isoformat()
    vars['now_time'] = tm
    vars['init_state'] = 'ok'
except Exception:
    vars['init_state'] = 'error'
    vars['outcome'] = 'no_promise'
    vars['reason'] = 'service_error'
    vars['cal_text'] = ''
''' % (HOL,)
INIT = INIT.replace("%%", "%")
nodes["init"] = code_node("init", INIT, "opening", [tr("end_error", "now missing or unreadable", cond("init_state", "equals", "error"))])
nodes["end_error"] = end_node("end_error", "ended_error", "I am sorry, I cannot continue this call right now." + " Goodbye.")

# ---------------- opening -----------------
LS = "line_status"
nodes["opening"] = node("opening", on_enter={"type": "tts", "text": "Hello, I am a digital assistant calling from Freya Bank, and this call is recorded. Am I speaking with {{title}} {{last_name}}?"},
    on_enter_first_entry_only=True,
    task_message=("Goal: find out who is on the line. Do not say 'collections', 'debt', 'payment' or the product. Do not say why you are calling. No tool call is allowed in this turn.\n"
                  "Only a clear 'yes', 'that's me', 'speaking' or the customer's own name counts as confirmation. 'Hello', 'go ahead' and 'who is this' do NOT count: answer any question briefly (a robot/AI question: you are Freya Bank's digital assistant), then ask once more: 'Am I speaking with {{title}} {{last_name}}?'. You may ask at most twice in total.\n"
                  "If someone else answers, do not say why you are calling. If they say the number is wrong or the customer has died, just listen; the call moves on."),
    extraction_schema=[ext(LS, "string", "Who is on the line. customer: the person clearly confirmed they are the customer (yes, that's me, speaking, or said their own name). other_person: someone else answered (relative, colleague, 'he is not here'). wrong_number: says the number does not belong to the customer / wrong number. deceased: says the customer has died. unclear_final: the assistant already asked twice who they are and the answer is still not a clear confirmation. Empty otherwise.",
                        ["customer", "other_person", "wrong_number", "deceased", "unclear_final"])],
    max_node_turns=8, max_turn_transition="close_unclear",
    transitions=[tr("identity", "customer confirmed", cond(LS, "equals", "customer")),
                 tr("third_party", "someone else", cond(LS, "equals", "other_person")),
                 tr("close_wrong_number", "wrong number", cond(LS, "equals", "wrong_number")),
                 tr("close_deceased", "deceased", cond(LS, "equals", "deceased")),
                 tr("close_unclear", "unclear after two asks", cond(LS, "equals", "unclear_final")),
                 ALWAYS("opening")])

# ---------------- third party -----------------
CBX = [ext("cb_day_word", "string", "Day the other person offers for a callback, as one of: today, tomorrow, a weekday name (monday..friday, optionally with 'next'), or YYYY-MM-DD. Empty if none given."),
       ext("cb_time", "string", "Time offered for the callback as 24-hour HH:MM (for example 15:00). Empty if none given."),
       ext(LS, "string", "customer: the person on the line now says they ARE the customer. wrong_number: says the number does not belong to the customer. deceased: says the customer has died. Empty otherwise.", ["customer", "other_person", "wrong_number", "deceased"])]
CB_READY = {"logic": "or", "conditions": [{"logic": "and", "conditions": [cond("cb_day_word", "is_set"), cond("cb_day_word", "not_equals", ""), cond("cb_time", "is_set"), cond("cb_time", "not_equals", "")]}]}
cb_trs = [tr("identity", "turns out to be the customer", cond(LS, "equals", "customer")),
          tr("close_wrong_number", "wrong number", cond(LS, "equals", "wrong_number")),
          tr("close_deceased", "deceased", cond(LS, "equals", "deceased")),
          {"target_node": "cb_check", "description": "day and time offered", "condition": CB_READY}]
nodes["third_party"] = node("third_party", on_enter={"type": "tts", "text": "When would be a good time to reach {{title}} {{last_name}}?"},
    task_message=("Someone other than the customer is on the line. Never say why you are calling and never mention the account, debt, payment or product; do not answer security questions; even if they offer to pay, say nothing about it. Only find out when the customer can be reached: you need a day and a time. No tool call is allowed in this turn.\n"
                  "If the person says the number is wrong or the customer has died, just listen; the call moves on."),
    extraction_schema=CBX, max_node_turns=6, max_turn_transition="close_no_callback",
    transitions=cb_trs + [ALWAYS("third_party")])
nodes["cb_retry"] = node("cb_retry", on_enter={"type": "tts", "text": "That time is not possible for a callback. We can call back today or the next business day, between 10:00 and 19:00. Which day and time would suit?"},
    task_message="Get one day and one time for the callback from the person. Say nothing about the account. No tool call is allowed in this turn.",
    extraction_schema=CBX, max_node_turns=4, max_turn_transition="close_no_callback",
    transitions=cb_trs + [ALWAYS("cb_retry")])

CBCODE = r'''
import datetime, re
HOL = %r
def isbd(d):
    return d.weekday() < 5 and d.isoformat() not in HOL
def nbd(d):
    d = d + datetime.timedelta(days=1)
    while not isbd(d):
        d = d + datetime.timedelta(days=1)
    return d
state = 'give_up'
outd = ''
outt = ''
try:
    n = int(vars.get('cb_attempts') or 0) + 1
    vars['cb_attempts'] = str(n)
    today = datetime.datetime.strptime(str(vars.get('now_date'))[:10], '%%Y-%%m-%%d').date()
    nowt = str(vars.get('now_time') or '00:00')[:5]
    w = str(vars.get('cb_day_word') or '').strip().lower().replace('next ', '').replace('this ', '').replace('on ', '')
    tt = str(vars.get('cb_time') or '').strip().lower()
    day = None
    names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    if w == 'today':
        day = today
    elif w == 'tomorrow':
        day = today + datetime.timedelta(days=1)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', w):
        day = datetime.date.fromisoformat(w)
    elif w in names:
        k = names.index(w)
        day = today + datetime.timedelta(days=(k - today.weekday()) %% 7)
    m = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$', tt)
    hh = mm = None
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2) or 0)
        if m.group(3) == 'pm' and hh < 12:
            hh += 12
        if m.group(3) == 'am' and hh == 12:
            hh = 0
    ok = False
    if day is not None and hh is not None and 0 <= hh < 24 and 0 <= mm < 60:
        allowed = [nbd(today)]
        if isbd(today):
            allowed.append(today)
        tmin = hh * 60 + mm
        nmin = int(nowt[:2]) * 60 + int(nowt[3:5])
        ok = day in allowed and 600 <= tmin <= 1140 and (day != today or tmin > nmin)
        outd = day.isoformat()
        outt = '%%02d:%%02d' %% (hh, mm)
    if ok:
        state = 'valid'
    elif n < 2:
        state = 'retry'
    else:
        state = 'give_up'
except Exception:
    state = 'give_up'
vars['cb_state'] = state
vars['cb_date_out'] = outd
vars['cb_time_out'] = outt
vars['cb_day_word'] = ''
vars['cb_time'] = ''
''' % (HOL,)
CBCODE = CBCODE.replace("%%", "%")
nodes["cb_check"] = code_node("cb_check", CBCODE, "close_no_callback",
    [tr("cb_schedule", "valid", cond("cb_state", "equals", "valid")), tr("cb_retry", "retry", cond("cb_state", "equals", "retry"))])
SCB = api_fn("schedule_callback", [CID, ("date", "string", "", None, "{{cb_date_out}}"), ("time", "string", "", None, "{{cb_time_out}}")], "", POST_SIMPLE, tool=False)
nodes["cb_schedule"] = api_node("cb_schedule", SCB, [{"path": "data.ok", "variable": "cb_ok"}],
    [tf("close_callback", "callback booked", ["cb_ok", "schedule_callback_response.data.ok"])], "close_no_callback")

# ---------------- identity -----------------
IDF = [CID, ("field", "string", "Which security answer this is.", ["date_of_birth", "phone_last4"], "{{field}}"),
       ("answer", "string", "date_of_birth as YYYY-MM-DD (whatever way the customer said it; numbers only are read day, then month, then year). phone_last4 as four digits.", None, "{{answer}}")]
VERIFY = api_fn("verify_identity", IDF,
    "CALL it every time the customer answers a security question (once per answer). Never use it for anything else.", POST_VERIFY,
    mapping=[{"path": "data.all_verified", "variable": "idv_all"}, {"path": "data.wrong_answers_left", "variable": "idv_left"}])
nodes["identity"] = node("identity", on_enter={"type": "tts", "text": "Thank you. For your security I need to ask two questions. First, what is your date of birth?"},
    on_enter_first_entry_only=True, tools=[VERIFY],
    task_message=("Verify identity. You do not know and must not say why the bank is calling: never say 'collections', 'debt', 'payment' or the product. If asked what the call is about, say you can explain after the security questions.\n"
                  "Ask two questions, one at a time: first the date of birth (already asked), then the last four digits of the phone number on file. After each answer CALL verify_identity (field date_of_birth or phone_last4). Send the date of birth as YYYY-MM-DD, whatever way the customer said it; a date given only in numbers is read day, then month, then year.\n"
                  "A wrong answer may be asked again; three wrong answers in total end the check (the tool result tells you how many are left). If the result has hint day_month_swapped, ask the customer to say the month as a word; that retry is not a wrong answer.\n"
                  "If the customer does not want to answer, explain once that the questions protect their account. If they still decline, call transition_to_close_declined. Asking what the call is about instead of answering counts as declining; a second refusal or second such question ends the call the same way. If the customer says twice that they do not want to talk, do the same.\n"
                  "If the customer asks for a human, first ask once whether you can help; if they insist, call transition_to_transfer_general.\n"
                  "Never speak about the account or debt. Follow what_to_do_next."),
    max_node_turns=30, max_turn_transition="close_declined",
    transitions=[tf("get_account", "both answers verified", ["idv_all", "verify_identity_response.data.all_verified"]),
                 tr("close_failed", "three wrong answers", cond("idv_left", "equals", "0"), cond("verify_identity_response.data.wrong_answers_left", "equals", "0")),
                 tr("close_declined", "customer declines the security questions after one explanation, or says twice they do not want to talk", tool_call=True,
                    intent="The customer declined to answer after being told once that the questions protect their account, or said twice they do not want to talk"),
                 tr("transfer_general", "customer insists on a human after being offered help first", tool_call=True,
                    intent="The customer insists on speaking to a human after the assistant offered to help first"),
                 ALWAYS("identity")])

# ---------------- account -----------------
def acct_fn():
    return api_fn("get_account", [CID], "", POST_ACCT, tool=False)
amap = [{"path": "data.products", "variable": "products"}, {"path": "data.ok", "variable": "acct_ok"}]
nodes["get_account"] = api_node("get_account", acct_fn(), amap,
    [tf("prep_account", "account loaded", ["acct_ok", "get_account_response.data.ok"])], "get_account_retry")
nodes["get_account_retry"] = api_node("get_account_retry", acct_fn(), amap,
    [tf("prep_account", "account loaded", ["acct_ok", "get_account_response.data.ok"])], "close_service_error")

PREP = r'''
import datetime, json
HOL = %r
def isbd(d):
    return d.weekday() < 5 and d.isoformat() not in HOL
def addbd(d, k):
    c = 0
    while c < k:
        d = d + datetime.timedelta(days=1)
        if isbd(d):
            c += 1
    return d
DN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
def sp(d):
    return DN[d.weekday()] + ' ' + str(d.day) + ' ' + MN[d.month - 1]
def money(x):
    f = float(x)
    return str(int(f)) if f == int(f) else '%%.2f' %% f
vars['acct_state'] = 'error'
try:
    v = vars.get('products')
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            import ast
            v = ast.literal_eval(v)
    if not isinstance(v, list) or not v:
        found = dict()
        import re
        for k in list(vars.keys()):
            m = re.search(r'products\.(\d+)\.(\w+)$', str(k))
            if m:
                found.setdefault(int(m.group(1)), dict())[m.group(2)] = vars.get(k)
        v = [found[i] for i in sorted(found.keys())]
    p = v[0]
    typ = str(p.get('type'))
    late = int(float(p.get('days_late')))
    due = float(p.get('past_due'))
    if typ == 'credit_card':
        name = 'credit card ending ' + str(p.get('card_last4'))
        floor = float(p.get('minimum_payment'))
    elif typ == 'personal_loan':
        name = 'personal loan'
        floor = float(p.get('instalment_amount'))
    else:
        name = 'car loan'
        floor = float(p.get('instalment_amount'))
    if 1 <= late <= 7:
        band, dl, att = 'early', 12, 1
    elif 8 <= late <= 45:
        band, dl, att = 'late', 7, 2
    else:
        raise ValueError('band')
    today = datetime.date.fromisoformat(str(vars.get('now_date')))
    dead = addbd(today, dl)
    vars['prod_id'] = str(p.get('product_id'))
    vars['prod_name'] = name
    vars['past_due_text'] = money(due)
    vars['floor_text'] = money(floor)
    vars['days_text'] = str(late) + (' day' if late == 1 else ' days')
    vars['band'] = band
    vars['max_attempts'] = str(att)
    vars['deadline_iso'] = dead.isoformat()
    vars['deadline_spoken'] = sp(dead)
    vars['acct_state'] = 'ok'
except Exception:
    vars['acct_state'] = 'error'
''' % (HOL,)
PREP = PREP.replace("%%", "%")
nodes["prep_account"] = code_node("prep_account", PREP, "close_service_error", [tr("negotiate", "account ready", cond("acct_state", "equals", "ok"))])

# ---------------- negotiate -----------------
CREATE = api_fn("create_promise", [CID, ("product_id", "string", "", None, "{{prod_id}}"),
                                    ("amount", "number", "Amount the customer confirmed, as a number (no currency sign).", None, "{{amount}}"),
                                    ("date", "string", "Confirmed payment day as YYYY-MM-DD.", None, "{{date}}")],
    "CALL it only after you read the product, amount and date back and the customer clearly said yes to 'Do you confirm?'. Never call it before that, and at most once per confirmed offer (again only if the result says it was not recorded).",
    POST_PROMISE, mapping=[{"path": "data.promise_id", "variable": "promise_id"}])
TRANSFER_SPEC = None
NEG_TASK = """You are on a collections call with {{title}} {{last_name}}, whose identity is verified. Facts from the account tool (never change them):
- product_id {{prod_id}}; product: {{prod_name}}; full past-due amount: {{past_due_text}}; days late: {{days_text}}; band: {{band}}.
- FLOOR (lowest amount you can record): {{floor_text}}.
- DEADLINE (latest promise date): {{deadline_spoken}} ({{deadline_iso}}).
- Persuasion attempts allowed: {{max_attempts}}.
- Attempt-1 proposal date (last business day of this week, or of next week if today is that day): {{attempt1_spoken}} ({{attempt1_iso}}).
Calendar for turning the customer's words into YYYY-MM-DD ('this <weekday>' is in the current calendar week, 'next <weekday>' in the following week):
{{cal_text}}

You already stated the debt and asked 'Can you make this payment today?'. Never ask 'how much can you pay'; YOU propose every amount.
DATES: for every day or period the customer names, CALL check_payment_date (date = YYYY-MM-DD from the calendar, or 'vague' for a vague period like 'next week', 'end of the month', 'when my salary comes'; product_id {{prod_id}}). Never say yourself whether a day is allowed. The tool's answer is read out to the customer; then continue from the last decision: {{date_decision}} (ok / not_business_day / after_deadline / past / ask_exact / propose_deadline / error); the date to use is {{date_proposed}}. If the customer refuses the deadline date, that is a flat refusal. If the decision is error, say you could not check the date and call it again once.
AMOUNTS: full amount {{past_due_text}} first. If the customer says it is too much, offer the floor {{floor_text}} once and say the rest stays overdue; if they refuse the floor it is a flat refusal. A customer amount from the floor up to the full amount (both included) is accepted. Below the floor: say it cannot be recorded and offer the floor once; if not accepted it is a flat refusal. Attempt 2 may name the floor again.
A date or amount the customer proposes is never a refusal; handle it as above.
PERSUASION: a flat refusal or non-answer (a no to paying today with no date and no amount) uses one attempt. Attempt 1: propose the full amount (or the floor if they already said the full amount is too much) on {{attempt1_spoken}}. Attempt 2 (only if allowed attempts is 2): propose the floor {{floor_text}} on the deadline {{deadline_spoken}}. Do not repeat an offer already refused. When all attempts are used and the customer refuses, say a short goodbye line and call transition_to_close_refused.
SPECIAL: illness, a death in the family or job loss: one short sentence of sympathy, NO persuasion; offer to connect them with the customer support team; if they accept call transition_to_transfer_support; if they decline call transition_to_close_hardship (if they still name a date or amount themselves, record that promise as usual). 'I already paid' (this past-due amount): say payments can take one business day to appear and call transition_to_close_paid. 'Not my debt' / 'never had this product' / product closed or paid off in the past: do not argue, no promise, call transition_to_close_dispute. Request for a new payment plan or lower instalments: describe nothing, call transition_to_transfer_restructuring. Request for a human: ask once whether you can help first; if they insist call transition_to_transfer_general. If the customer says twice they do not want to talk, call transition_to_close_refused. Never offer discounts, waivers or plans.
CONFIRM: once amount and date are agreed and the date check said ok (or the customer accepted the proposed date), read back the product, the amount and the date and ask 'Do you confirm?'. Call create_promise ONLY after a clear yes, with the exact amount and the YYYY-MM-DD date. If the customer changes date or amount, re-check it with the rules above and read it back again. One promise per product; after it is recorded the call closes by itself. If asked to change or cancel a recorded promise: they can change it in the mobile app.
Say a promise is recorded only if create_promise returned ok. If create_promise fails, say you will try once more and call it again. Follow what_to_do_next."""
DATE_CFG = json.load(open(os.path.join(WD, "date_config.json"), encoding="utf-8"))
dt = json.loads(subprocess.check_output([sys.executable, os.path.join(ROOT, "builder", "runtime", "date_tool.py"), os.path.join(WD, "date_config.json"), "negotiate"]))

DEBT = "Thank you, that is verified. I am calling from the collections team about a late payment on your {{prod_name}}. The past-due amount is {{past_due_text}} and it is {{days_text}} late. Can you make this payment today?"
neg_trs = [dt["transition"],
           tf("close_promise", "promise recorded", ["create_promise_response.data.ok", "promise_ok"]),
           tr("close_promise_failed", "promise failed twice", cond("promise_fail_n", "greater_than", 1), cond("create_promise_failure_count", "greater_than", 1)),
           tr("close_paid", "customer says they already paid this past-due amount", tool_call=True, intent="The customer says they already paid this past-due amount"),
           tr("close_dispute", "customer says the debt is not theirs, they never had the product, or it was closed/paid off in the past", tool_call=True, intent="The customer disputes the debt or says they never had the product"),
           tr("transfer_restructuring", "customer asks for a new payment plan or lower instalments", tool_call=True, intent="The customer asks for a new payment plan or lower instalments"),
           tr("transfer_general", "customer insists on a human after being offered help first", tool_call=True, intent="The customer insists on speaking to a human"),
           tr("transfer_support", "hardship and the customer accepts support team", tool_call=True, intent="The customer mentioned illness, death in the family or job loss and accepted a connection to the support team"),
           tr("close_hardship", "hardship and the customer declines support team", tool_call=True, intent="The customer mentioned illness, death in the family or job loss and declined the support team"),
           tr("close_refused", "all persuasion attempts used and refused, or customer twice does not want to talk", tool_call=True, intent="All allowed persuasion attempts were used and the customer still refuses, or the customer twice said they do not want to talk")]
nodes["negotiate"] = node("negotiate", on_enter={"type": "tts", "text": DEBT}, on_enter_first_entry_only=True,
    tools=[dt["tool"], CREATE], task_message=NEG_TASK, extraction_schema=[],
    max_node_turns=40, max_turn_transition="close_refused", transitions=neg_trs + [ALWAYS("negotiate")])
nodes.update(dt["nodes"])
nodes["date_relay"]["transitions"] = [ALWAYS("negotiate")]

# ---------------- transfers -----------------
for key, queue, closer in (("restructuring", "restructuring", "close_restructuring"), ("general", "general", "close_human"), ("support", "support", "close_support")):
    fn = api_fn("transfer_to_agent", [CID, ("queue", "string", "", None, queue)], "", POST_SIMPLE, tool=False)
    nodes["transfer_" + key] = api_node("transfer_" + key, fn, [{"path": "data.ok", "variable": "transfer_ok"}],
        [tf(closer, "transfer ok", ["transfer_to_agent_response.data.ok"])], "close_service_error")
    # clear stale flag by using per-node response key only

# fix: transfer_ok mapping not used for routing (response key is shared, set on each call)

CLOSE = {
    "type": "function", "config": {"timeoutMs": 12000, "maxRetries": 0, "alwaysRunsAt": ["end_of_call"]},
    "function": {"name": "close_call", "handler": "__function__:api_call", "description": "Record how the call ended, from the conversation.",
                 "parameters": {"type": "object", "properties": {
                     "url": {"type": "string", "default": BASE + "/close_call"}, "method": {"type": "string", "default": "POST"},
                     "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                     "body": {"type": "object", "required": ["outcome"], "properties": {
                         "reason": {"type": "string", "default": "{{reason}}", "description": "Required for every outcome except promise and paid."},
                         "outcome": {"type": "string", "enum": ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"], "default": "{{outcome}}", "description": "How the call ended."},
                         "customer_id": {"type": "string", "default": "{{customer_id}}"}}}}}},
    "pre_process_code": "try:\n    b = config.get('body')\n    if isinstance(b, dict) and b.get('outcome') in ('promise', 'paid'):\n        b.pop('reason', None)\nexcept Exception:\n    pass\n",
    "post_process_code": POST_CLOSE,
}

wf = {"initial_node": "init", "system_prompt": SYSTEM, "nodes": nodes, "global_nodes": {}, "tools": [CLOSE],
      "test_variables": {"customer_id": "c_test", "first_name": "Daniel", "last_name": "Reyes", "title": "Mr", "now": "2026-10-14T11:00"}}
json.dump(wf, open(os.path.join(WD, "workflow.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("written")

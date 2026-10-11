import json, sys, textwrap, subprocess, os
ROOT = r"C:\Users\ASUS\OneDrive\Masaüstü\build-the-builder"
WD = os.path.join(ROOT, "out", "fb-a-20261010-235820")
BASE = "https://freya-bank-mock.freyavoice.workers.dev/v1/"
cfg = json.load(open(os.path.join(WD, "date_config.json"), encoding="utf-8"))
HOL = cfg["holidays"]

dt = subprocess.run([sys.executable, os.path.join(ROOT, "builder", "runtime", "date_tool.py"),
                     os.path.join(WD, "date_config.json"), "negotiate"], capture_output=True, text=True, encoding="utf-8")
DT = json.loads(dt.stdout)

# ---------- helpers ----------
def hook(body):
    b = textwrap.indent(textwrap.dedent(body).strip("\n"), " " * 8)
    return ("try:\n    if isinstance(result, dict):\n        result.pop('header', None)\n        d = result.get('data')\n"
            "        if not isinstance(d, dict):\n            d = dict()\n            result['data'] = d\n"
            "        ok = str(d.get('ok')).lower() == 'true'\n" + b + "\nexcept Exception:\n    pass\n")

def tool(name, path, props, required, desc, body, mapping=None, retries=0):
    bp = {"customer_id": {"type": "string", "default": "{{customer_id}}"}}
    for k, v in props.items():
        p = {"type": "string", "description": v[0], "default": "{{%s}}" % k}
        if len(v) > 1 and v[1]:
            p["enum"] = v[1]
        bp[k] = p
    t = {"type": "function", "config": {"timeoutMs": 12000, "maxRetries": retries},
         "function": {"name": name, "handler": "__function__:api_call", "description": desc,
                      "parameters": {"type": "object", "properties": {
                          "url": {"type": "string", "default": BASE + path},
                          "method": {"type": "string", "default": "POST"},
                          "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                          "body": {"type": "object", "properties": bp, "required": required}}}},
         "post_process_code": hook(body)}
    if mapping:
        t["response_mapping"] = mapping
    return t

def eq(var, vals):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": v} for v in vals]}

def tr(target, desc, cond=None, tool_call=False):
    t = {"target_node": target, "description": desc, "condition": cond or {"operator": "always"}}
    if tool_call:
        t["is_tool_call"] = True
    return t

ALWAYS = lambda tgt: tr(tgt, "always")

# ---------- tools ----------
T_VERIFY = tool("verify_identity", "verify_identity",
    {"field": ("Which security answer this is.", ["date_of_birth", "phone_last4"]),
     "answer": ("date_of_birth as YYYY-MM-DD (day, then month, then year when said only in numbers); phone_last4 as four digits.",)},
    ["field", "answer"],
    "CALL it every time the customer gives a security answer (date of birth first, then the last four digits of the phone number). Never call it before an answer was given.",
    """
    left = d.get('wrong_answers_left')
    if not ok:
        d['what_to_do_next'] = 'The answer could not be read or the service failed. It was NOT counted as a wrong answer. Ask for the same answer again clearly (date of birth as day, month as a word, year).'
    elif d.get('hint') == 'day_month_swapped':
        d['what_to_do_next'] = 'Day and month look swapped. Ask the customer to say the month as a word, then call verify_identity again. This retry is not a wrong answer.'
    elif str(d.get('all_verified')).lower() == 'true':
        d['what_to_do_next'] = 'Both answers passed. Do not say anything about the account; the next step starts automatically.'
    elif str(d.get('verified')).lower() == 'true':
        d['what_to_do_next'] = 'This answer is correct. Ask the next security question (phone number last four digits if date of birth was just passed).'
    elif str(left) == '0':
        d['what_to_do_next'] = 'Three wrong answers: the check has ended. Do NOT state any debt. Tell the customer to use the mobile app or a branch, thank them, say goodbye, then call close_call with outcome not_verified and reason failed.'
    else:
        d['what_to_do_next'] = 'Wrong answer. Wrong answers left: ' + str(left) + '. Say it did not match and ask the same question again.'
    """,
    mapping=[{"path": "data.all_verified", "variable": "all_verified"}])

T_ACCOUNT = tool("get_account", "get_account", {}, [], "Get the late products.",
    """
    d['what_to_do_next'] = 'Account loaded.' if ok else 'Account lookup failed.'
    """,
    retries=2)

T_PROMISE = tool("create_promise", "create_promise",
    {"product_id": ("The product_id from the account result, copied unchanged.",),
     "amount": ("Agreed promise amount as a number, e.g. 250.00. Between the floor and the full past-due amount.",),
     "date": ("Agreed promise date as YYYY-MM-DD.",)},
    ["product_id", "amount", "date"],
    "CALL it only after the customer clearly said yes to the read-back of product, amount and date. Never say the promise is recorded before this returns ok true.",
    """
    if ok:
        d['what_to_do_next'] = 'Promise recorded. The next step starts automatically; say the confirmation sentence there.'
    else:
        d['what_to_do_next'] = 'The promise was NOT recorded (nothing saved). If this is the first failure, tell the customer you are trying once more and call create_promise again with the same values. If this is the second failure, say you could not record it, thank them, say goodbye, then call close_call with outcome no_promise and reason service_error.'
    """,
    mapping=[{"path": "data.ok", "variable": "promise_ok"}])
T_PROMISE["function"]["parameters"]["properties"]["body"]["properties"]["product_id"]["default"] = "{{product_id}}"

T_CALLBACK = tool("schedule_callback", "schedule_callback",
    {"date": ("Callback date YYYY-MM-DD: today or the next business day only.",),
     "time": ("Callback time HH:MM, from 10:00 to 19:00 inclusive and later than now.",)},
    ["date", "time"],
    "CALL it once the person gave a valid callback day and time (today or the next business day, 10:00-19:00 inclusive, later than now).",
    """
    if ok:
        d['what_to_do_next'] = 'Callback booked. Thank them, say goodbye, then call close_call with outcome not_reached and reason callback.'
    else:
        d['what_to_do_next'] = 'Callback NOT booked (nothing saved). Try once more with the same values. If it fails again, say you could not book it, say goodbye, then call close_call with outcome not_reached and reason no_callback.'
    """)

T_TRANSFER = tool("transfer_to_agent", "transfer_to_agent",
    {"queue": ("Queue: restructuring (payment plan / lower instalments), general (customer insists on a human), support (hardship and customer accepted support).", ["restructuring", "general", "support"])},
    ["queue"],
    "CALL it for a payment-plan request (restructuring), an insisted human request (general), or hardship when the customer accepted support (support).",
    """
    if ok:
        d['what_to_do_next'] = 'Transfer done. Thank the customer, say goodbye, then call close_call with outcome transferred and reason restructuring, human or support matching the queue (restructuring->restructuring, general->human, support->support).'
    else:
        d['what_to_do_next'] = 'Transfer NOT done. Try once more with the same queue. If it fails again, say you could not transfer, say goodbye, then call close_call with outcome no_promise and reason service_error.'
    """)

T_CLOSE = tool("close_call", "close_call",
    {"outcome": ("Call outcome.", ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"]),
     "reason": ("Required except for promise and paid. transferred: restructuring|human|support. no_promise: refused|hardship|dispute|service_error. not_verified: failed|declined. not_reached: callback|no_callback|wrong_number|deceased|unclear.",
                ["restructuring", "human", "support", "refused", "hardship", "dispute", "service_error", "failed", "declined", "callback", "no_callback", "wrong_number", "deceased", "unclear"])},
    ["outcome"],
    "CALL it exactly once, as the very last tool call, after you said goodbye. Use the outcome and reason from the closing table. Leave reason empty for promise and paid.",
    """
    if ok:
        d['what_to_do_next'] = 'Call closed. Say nothing more.'
    else:
        d['what_to_do_next'] = 'Closing failed. Call close_call once more with the same outcome and reason.'
    """,
    mapping=[{"path": "data.ok", "variable": "close_ok"}])

def tools_of(*ts):
    import copy
    return [copy.deepcopy(t) for t in ts]

CLOSE_TR = tr("end_done", "The call was closed", eq("close_ok", ["true", "True"]))

COMMON = ("Speak English. One or two short sentences per turn. If the customer's last message contains a question, first answer it in one short sentence, then continue: "
          "robot/AI question -> say you are Freya Bank's digital assistant; scam question -> say they can verify the call by phoning Freya Bank's customer service number; "
          "anything you cannot answer from the tools -> say you do not have that information (never invent figures, dates or reasons). "
          "After every tool result either speak to the customer or call the next tool; follow the what_to_do_next line in the result. One tool call per message. "
          "Never offer a discount, waiver, instalment plan or any term not in these instructions. "
          "Never claim an action is done unless its tool result says ok true; if a call failed say plainly that nothing was saved. "
          "If the customer asks for a human: ask once whether you can help first; if they insist, call transfer_to_agent queue general, then say goodbye and call close_call transferred / human. "
          "Always thank the customer and say goodbye before close_call. close_call is called exactly once and is the last tool call.")

def conv(name, task, tools, transitions, on_enter=None, extraction=None, first_only=False):
    n = {"name": name, "node_type": "conversation", "task_message": task, "tools": tools, "transitions": transitions}
    if on_enter:
        n["on_enter"] = on_enter
    if first_only:
        n["on_enter_first_entry_only"] = True
    if extraction:
        n["extraction_schema"] = extraction
    return n

def code_node(name, code, nxt, transitions):
    return {"name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": nxt, "on_enter": {"type": "silent"},
            "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {
                "code": {"type": "string", "default": code}, "timeout_ms": {"type": "number", "default": 8000}}}}}],
            "transitions": transitions}

# ---------- code ----------
HELP = '''
import json, datetime, re
HOL = %s
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
def isbd(d):
    return d.weekday() < 5 and d.isoformat() not in HOL
def add_bd(d, n):
    c = 0
    while c < n:
        d = d + datetime.timedelta(days=1)
        if isbd(d):
            c += 1
    return d
def next_bd(d):
    return add_bd(d, 1)
def sp(d):
    return DAYS[d.weekday()] + ' ' + d.isoformat()
def last_bd_of_week(monday):
    d = monday + datetime.timedelta(days=4)
    while not isbd(d):
        d = d - datetime.timedelta(days=1)
    return d
''' % json.dumps(HOL)

SETUP = HELP + '''
vars['cal_state'] = 'bad'
vars['calendar'] = 'unknown'
try:
    raw = str(vars.get('now') or '')
    today = datetime.datetime.strptime(raw[:10], '%Y-%m-%d').date()
    hm = raw[11:16] if len(raw) >= 16 else '00:00'
    datetime.datetime.strptime(hm, '%H:%M')
    mon = today - datetime.timedelta(days=today.weekday())
    nmon = mon + datetime.timedelta(days=7)
    lines = []
    lines.append('Today is ' + sp(today) + ', current time ' + hm + '. Business days are Monday to Friday except these Freya Bank holidays: ' + ', '.join(HOL) + '.')
    lines.append('Today is a business day: ' + ('yes' if isbd(today) else 'no') + '. Next business day after today: ' + sp(next_bd(today)) + '.')
    lines.append('THIS week (use for "this <weekday>"): ' + '; '.join(sp(mon + datetime.timedelta(days=i)) for i in range(7)) + '.')
    lines.append('NEXT calendar week (use for "next <weekday>"): ' + '; '.join(sp(nmon + datetime.timedelta(days=i)) for i in range(7)) + '.')
    lines.append('Tomorrow is ' + sp(today + datetime.timedelta(days=1)) + '.')
    lbt = last_bd_of_week(mon)
    lbn = last_bd_of_week(nmon)
    lines.append('Last business day of this week: ' + sp(lbt) + '. Last business day of next week: ' + sp(lbn) + '.')
    vars['calendar'] = '\\n'.join(lines)
    vars['today_iso'] = today.isoformat()
    vars['now_time'] = hm
    nb = next_bd(today) if not isbd(today) or True else today
    cb = []
    cb.append('Callback window: ' + ('today ' + today.isoformat() + ' only at a time later than ' + hm + ' and up to 19:00, or ' if isbd(today) and hm < '19:00' else '') + 'the next business day ' + sp(nb) + ', at a time from 10:00 to 19:00 (both included). Anything else is outside the window.')
    vars['callback_rules'] = ' '.join(cb)
    vars['cal_state'] = 'ok'
except Exception:
    vars['cal_state'] = 'bad'
'''

FACTS = HELP + '''
import ast
BANDS = [(1, 7, 12, 'early', 1), (8, 45, 7, 'late', 2)]
vars['facts_state'] = 'bad'
def load_products():
    v = vars.get('products')
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            try:
                v = ast.literal_eval(v)
            except Exception:
                v = None
    if isinstance(v, list) and v:
        return [p for p in v if isinstance(p, dict)]
    found = dict()
    for k in list(vars.keys()):
        m = re.search(r'products\\.(\\d+)\\.(\\w+)$', str(k))
        if m:
            found.setdefault(int(m.group(1)), dict())[m.group(2)] = vars.get(k)
    return [found[i] for i in sorted(found.keys())]
def money(x):
    return '%.2f' % float(x)
try:
    today = datetime.datetime.strptime(str(vars.get('now'))[:10], '%Y-%m-%d').date()
    prods = load_products()
    p = prods[0]
    late = int(float(p.get('days_late')))
    b = [x for x in BANDS if x[0] <= late <= x[1]][0]
    deadline = add_bd(today, b[2])
    typ = str(p.get('type'))
    if typ == 'credit_card':
        phrase = 'credit card ending ' + str(p.get('card_last4'))
        floor = p.get('minimum_payment')
    elif typ == 'personal_loan':
        phrase = 'personal loan'
        floor = p.get('instalment_amount')
    else:
        phrase = 'car loan'
        floor = p.get('instalment_amount')
    mon = today - datetime.timedelta(days=today.weekday())
    cand = last_bd_of_week(mon)
    if cand <= today:
        cand = last_bd_of_week(mon + datetime.timedelta(days=7))
    if cand > deadline:
        cand = deadline
    vars['product_id'] = str(p.get('product_id'))
    vars['product_phrase'] = phrase
    vars['past_due_txt'] = money(p.get('past_due'))
    vars['floor_txt'] = money(floor)
    vars['days_late'] = str(late)
    vars['band_name'] = b[3]
    vars['attempts_allowed'] = str(b[4])
    vars['deadline_spoken'] = sp(deadline)
    vars['deadline_iso'] = deadline.isoformat()
    vars['attempt1_date'] = sp(cand)
    vars['facts_state'] = 'ok'
except Exception:
    vars['facts_state'] = 'bad'
'''
for c in (SETUP, FACTS):
    assert "{{" not in c and "}}" not in c, "braces"

# ---------- prompts ----------
GREET_EXTRACT = [{"name": "speaker", "type": "string", "enum_values": ["customer", "someone_else", "unclear"],
                  "description": "customer = the person clearly confirmed they are the customer ('yes', 'that's me', 'speaking' or said their own name). someone_else = another person answered (relative, colleague, wrong number, says the customer is not here or died). unclear = anything else ('hello', 'go ahead', 'who is this', a question).",
                  "min_confidence": 0.6}]

GREET_TASK = (COMMON + " You have just asked 'Am I speaking with {{title}} {{last_name}}?'. Do NOT mention collections, debt, payment or any product. "
    "Only 'yes', 'that's me', 'speaking' or the customer's own name confirms. 'Hello', 'go ahead', 'who is this' do not confirm: answer any question first, then ask 'Am I speaking with {{title}} {{last_name}}?' once more. "
    "If it is still unclear after that second ask, say goodbye and call close_call with outcome not_reached and reason unclear. "
    "Before identity is verified, if the customer says twice they do not want to talk, say goodbye and call close_call not_verified / declined. Tools allowed: transfer_to_agent (only for an insisted human request), close_call.")

IDENT_TASK = (COMMON + " Never mention the debt, the product or the account in this step. Ask two security questions, one at a time: first the date of birth, then the last four digits of the phone number on file. "
    "After each answer CALL verify_identity (field date_of_birth with YYYY-MM-DD, whatever way the customer said it; a date given only in numbers is day, then month, then year; field phone_last4 with four digits). "
    "Three wrong answers in total end the check, whichever question. A day_month_swapped hint means: ask the customer to say the month as a word; that retry is not a wrong answer. "
    "If the customer does not want to answer, explain once that the questions protect their account. If they still decline, say goodbye and call close_call not_verified / declined. Asking what the call is about instead of answering counts as declining; a second refusal or a second such question closes the call (not_verified / declined). "
    "If the customer says twice they do not want to talk, close as not_verified / declined. After the three wrong answers follow what_to_do_next (close not_verified / failed). Do not call close_call before the check is over or declined. Do not tell anything about the account.")

THIRD_TASK = (COMMON + " The person on the line is NOT confirmed as the customer. Do not say why you are calling and say nothing about the bank's business beyond the opening sentence. No security questions, nothing about any account, even if they offer to pay. "
    "Ask when the customer can be reached. {{callback_rules}} Calendar: {{calendar}} "
    "If they offer a valid day and time, CALL schedule_callback (date YYYY-MM-DD, time HH:MM), then close per what_to_do_next (not_reached / callback). "
    "If they offer a day or time outside the window, say so and ask once for another time; if that is also outside, do not schedule: thank them, say goodbye, call close_call not_reached / no_callback. "
    "If they say the number does not belong to the customer: thank them, say goodbye, close not_reached / wrong_number. "
    "If they say the customer has died: say exactly 'I am sorry for your loss.', ask nothing else, say goodbye, close not_reached / deceased. "
    "If the person turns out to be the customer ('yes that's me'), ask 'Am I speaking with {{title}} {{last_name}}?' if not clearly confirmed; otherwise continue handling as above.")

NEG_ENTER = ("If the customer's last message contained a question, answer it in one short sentence first. Then say you are calling from the collections team about a late payment, name the product '{{product_phrase}}', state the past-due amount {{past_due_txt}} and that it is {{days_late}} days late. "
             "Then ask exactly: \"Can you make this payment today?\"")

NEG_TASK = (COMMON + " IDENTITY IS VERIFIED. FACTS: product {{product_phrase}} (product_id {{product_id}}), past due {{past_due_txt}}, {{days_late}} days late, band {{band_name}}, floor amount {{floor_txt}}, deadline {{deadline_spoken}} (ISO {{deadline_iso}}), persuasion attempts allowed {{attempts_allowed}}, attempt-1 date {{attempt1_date}}.\n"
    "CALENDAR:\n{{calendar}}\n"
    "AMOUNTS: you propose every amount; never ask 'how much can you pay'. Ask for the full past-due amount first. If the customer says the full amount is too much, offer the floor {{floor_txt}} once and say the rest stays overdue; if they refuse the floor it is a flat refusal. If they propose an amount from {{floor_txt}} up to {{past_due_txt}} (both included) accept it. Below the floor: say it cannot be recorded and offer the floor once; if they do not accept, flat refusal.\n"
    "DATES: a promise date must be today or later, a business day and not after the deadline. For EVERY day or period the customer names (also 'today') CALL check_payment_date (date = YYYY-MM-DD from the calendar above, or 'vague' if no exact day; product_id {{product_id}}). 'Next <weekday>' is the weekday of the following calendar week; 'this <weekday>' is in the current week. Never say yourself whether a day is allowed; the decision is read out by the system. "
    "Continue from the decision in {{date_decision}} (proposed date {{date_proposed}}): ok -> if the amount is also agreed, move on to the read-back; not_business_day / after_deadline / propose_deadline -> wait for the customer to accept the proposed day; if the customer refuses the deadline it is a flat refusal; past or ask_exact -> ask for a day.\n"
    "GETTING THE PROMISE: a date or amount proposed by the customer is never a refusal. A flat refusal or a non-answer (a plain no to paying today with no date and no amount) uses one persuasion attempt. Attempt 1: for the full amount (or the floor if they already said the full amount is too much) propose the date {{attempt1_date}} (last business day of this week, or of next week if today is that day). Attempt 2, only if attempts allowed is 2: propose the floor amount {{floor_txt}} on the deadline {{deadline_spoken}}. When attempts are used up stop, do not repeat a refused offer, say goodbye and call close_call no_promise / refused. Count your attempts yourself.\n"
    "AGREEMENT: when an amount and a valid date are agreed, CALL transition_to_confirm.\n"
    "SPECIAL: illness, death in the family or job loss -> one short sentence of sympathy, NO persuasion attempt, offer to connect them with the customer support team; if they accept CALL transfer_to_agent queue support then close transferred / support; if they decline close no_promise / hardship (if they still name a date or amount themselves, handle it with the rules above). "
    "'I already paid' -> say payments can take one business day to appear, take no promise, say goodbye, close paid. 'Not my debt' / 'never had this product' / product closed or paid off in the past -> do not argue, no promise, close no_promise / dispute. Request for a new payment plan or lower instalments -> do not describe a plan, CALL transfer_to_agent queue restructuring, close transferred / restructuring. "
    "If the customer says twice they do not want to talk, close no_promise / refused. Do not offer anything outside these rules. Tools: check_payment_date, transfer_to_agent, close_call.")

CONF_TASK = (COMMON + " Product {{product_phrase}} (product_id {{product_id}}), past due {{past_due_txt}}, floor {{floor_txt}}, deadline {{deadline_spoken}}. CALENDAR:\n{{calendar}}\n"
    "Read the agreed product, amount and date back and ask exactly \"Do you confirm?\". CALL create_promise only after a clear yes (product_id {{product_id}}, the agreed amount as a number, the agreed date as YYYY-MM-DD). "
    "If the customer changes the date, CALL check_payment_date with the new date (it is checked by the system). If the customer changes the amount, check it yourself (from {{floor_txt}} up to {{past_due_txt}} inclusive; below the floor offer the floor once) and read it back again. "
    "One promise per product; a recorded promise cannot be changed in this call (they can change it in the mobile app). If the customer now refuses, says it is not their debt, asks for a payment plan, or says they already paid, handle it: refusal -> close no_promise / refused; dispute -> no_promise / dispute; plan -> transfer_to_agent restructuring then close transferred / restructuring; paid -> say payments can take one business day to appear, close paid. "
    "Never say the promise is recorded; that is said in the next step after create_promise returned ok true. Tools: create_promise, check_payment_date, transfer_to_agent, close_call.")

DONE_TASK = ("The promise was recorded successfully. Say exactly: \"You will receive a text message confirming this promise.\" If the customer asked something, answer in one short sentence first (if they ask to change the promise: it cannot be changed in this call, they can change it in the mobile app). Then thank them, say goodbye, and CALL close_call with outcome promise (no reason). One tool call per message. Follow what_to_do_next.")

FAIL_TASK = ("The account could not be loaded. Apologise briefly, say you cannot continue the call right now (do not mention any debt), thank them, say goodbye, then CALL close_call with outcome no_promise and reason service_error.")

# ---------- assemble ----------
nodes = {}
nodes["setup"] = code_node("setup", SETUP, "greet", [
    tr("greet", "calendar ready", eq("cal_state", ["ok"])), tr("now_error", "now missing or unreadable")])
nodes["now_error"] = {"name": "now_error", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
    "terminal": {"type": "function", "function": {"name": "now_missing_error", "handler": "__function__:end_call", "parameters": {"type": "object", "properties": {
        "message_mode": {"type": "string", "default": "custom"},
        "spoken_message": {"type": "string", "default": "I am sorry, there is a technical problem and I cannot continue this call. Goodbye."}}}}}}
nodes["end_done"] = {"name": "end_done", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
    "terminal": {"type": "function", "function": {"name": "call_closed", "handler": "__function__:end_call", "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}}}

nodes["greet"] = conv("greet", GREET_TASK, tools_of(T_TRANSFER, T_CLOSE), [
    CLOSE_TR,
    tr("identity", "The customer confirmed", eq("speaker", ["customer"])),
    tr("third_party", "Someone else answered", eq("speaker", ["someone_else"])),
    ALWAYS("greet")],
    on_enter={"type": "tts", "text": "Hello, I am a digital assistant calling from Freya Bank, and this call is recorded. Am I speaking with {{title}} {{last_name}}?"},
    extraction=GREET_EXTRACT, first_only=True)
nodes["third_party"] = conv("third_party", THIRD_TASK, tools_of(T_CALLBACK, T_CLOSE), [CLOSE_TR, ALWAYS("third_party")],
    on_enter={"type": "llm", "prompt": "Answer any question in one short sentence without saying why you call. Do not say why you are calling. Ask when the customer can be reached, or handle a wrong-number / deceased statement as instructed."})
nodes["identity"] = conv("identity", IDENT_TASK, tools_of(T_VERIFY, T_TRANSFER, T_CLOSE), [
    CLOSE_TR,
    tr("fetch_account", "Both security answers passed", eq("all_verified", ["true", "True"])),
    ALWAYS("identity")],
    on_enter={"type": "llm", "prompt": "Answer any question the customer asked in one short sentence (do not mention the debt). Then say you need to ask two security questions and ask the first: their date of birth."},
    first_only=True)
nodes["fetch_account"] = {"name": "fetch_account", "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "facts",
    "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
    "pre_actions": [T_ACCOUNT], "response_mapping": [{"path": "data.products", "variable": "products"}],
    "transitions": [tr("facts", "products loaded", {"logic": "or", "conditions": [{"variable": "products", "operator": "is_set"}]}), tr("account_fail", "no account data")]}
nodes["facts"] = code_node("facts", FACTS, "negotiate", [tr("negotiate", "facts ready", eq("facts_state", ["ok"])), tr("account_fail", "facts failed")])
nodes["account_fail"] = conv("account_fail", FAIL_TASK, tools_of(T_CLOSE), [CLOSE_TR, ALWAYS("account_fail")], on_enter={"type": "llm"})

neg_tools = tools_of(T_TRANSFER, T_CLOSE)
neg_tools.insert(0, DT["tool"])
nodes["negotiate"] = conv("negotiate", NEG_TASK, neg_tools, [
    DT["transition"], CLOSE_TR,
    tr("confirm", "The customer agreed an amount and a valid date", tool_call=True,
       cond={"operator": "matches_intent", "description": "An amount and a valid payment date were agreed"}),
    ALWAYS("negotiate")],
    on_enter={"type": "llm", "prompt": NEG_ENTER}, first_only=True)
conf_tools = tools_of(T_PROMISE, T_TRANSFER, T_CLOSE)
conf_tools.insert(1, DT["tool"])
nodes["confirm"] = conv("confirm", CONF_TASK, conf_tools, [
    DT["transition"],
    tr("promise_done", "The promise was recorded", eq("promise_ok", ["true", "True"])),
    CLOSE_TR, ALWAYS("confirm")],
    on_enter={"type": "llm", "prompt": "Read the agreed product, amount and date back to the customer and ask exactly \"Do you confirm?\". Do not say anything is recorded."}, first_only=True)
nodes["promise_done"] = conv("promise_done", DONE_TASK, tools_of(T_CLOSE), [CLOSE_TR, ALWAYS("promise_done")], on_enter={"type": "llm"})
nodes.update(DT["nodes"])

wf = {"initial_node": "setup",
      "system_prompt": "You are Freya Bank's digital phone assistant. Speak English. Follow each step's instructions strictly. The customer is addressed as {{title}} {{last_name}}.",
      "nodes": nodes}
out = os.path.join(WD, "workflow.json")
json.dump(wf, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("written")

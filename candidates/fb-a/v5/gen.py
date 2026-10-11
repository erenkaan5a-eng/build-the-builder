import json, sys, os
D = os.path.dirname(os.path.abspath(__file__))
BASE = "https://freya-bank-mock.freyavoice.workers.dev/v1/"
HOL = ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"]

def always(t, d="always"):
    return {"target_node": t, "description": d, "condition": {"operator": "always"}}

def eq(var, vals):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": v} for v in vals]}

def gt0(var):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "greater_than", "operand": 0}]}

def hook(ok_msg, fail_msg):
    return ("try:\n"
            "    if isinstance(result, dict):\n"
            "        result.pop('header', None)\n"
            "        d = result.get('data')\n"
            "        if not isinstance(d, dict):\n"
            "            d = dict(ok=False)\n"
            "            result['data'] = d\n"
            "        good = str(d.get('ok')).lower() == 'true'\n"
            "        d['what_to_do_next'] = " + repr(ok_msg) + " if good else " + repr(fail_msg) + "\n"
            "except Exception:\n"
            "    pass\n")

VERIFY_HOOK = (
"try:\n"
"    if isinstance(result, dict):\n"
"        result.pop('header', None)\n"
"        d = result.get('data')\n"
"        if not isinstance(d, dict):\n"
"            d = dict(ok=False)\n"
"            result['data'] = d\n"
"        good = str(d.get('ok')).lower() == 'true'\n"
"        ver = str(d.get('verified')).lower() == 'true'\n"
"        allv = str(d.get('all_verified')).lower() == 'true'\n"
"        left = d.get('wrong_answers_left')\n"
"        msg = ''\n"
"        if str(d.get('hint')) == 'day_month_swapped':\n"
"            msg = 'Day and month look swapped. This does not count as a wrong answer. Ask the customer to say the date of birth again with the month as a word, then call verify_identity again.'\n"
"        elif not good:\n"
"            msg = 'The service did not check the answer (nothing counted as wrong). If it was a date of birth, ask the customer to say it again with the month as a word. Otherwise try the same call once more. Say nothing about the account.'\n"
"        elif allv:\n"
"            msg = 'Both security answers passed. Say one short thanks. Do not state the debt yet and ask nothing more.'\n"
"        elif ver:\n"
"            msg = 'That answer is correct. Ask the other security question now (the last four digits of the phone number on file if the date of birth is done, otherwise the date of birth).'\n"
"        else:\n"
"            try:\n"
"                n = int(left)\n"
"            except Exception:\n"
"                n = -1\n"
"            if n == 0:\n"
"                msg = 'Wrong answer and no attempts are left. Do not state the debt. Tell the customer to use the mobile app or a branch, thank them, say goodbye, then call close_call with outcome not_verified and reason failed.'\n"
"            else:\n"
"                msg = 'Wrong answer. Attempts left: ' + str(left) + '. Say it was not correct and ask the same question again.'\n"
"        d['what_to_do_next'] = msg\n"
"except Exception:\n"
"    pass\n")

def api_tool(name, path, props, desc, hk, required=None, retries=0, pre=None):
    body = {"type": "object", "properties": props, "required": required or []}
    t = {"type": "function", "config": {"timeoutMs": 12000, "maxRetries": retries},
         "function": {"name": name, "handler": "__function__:api_call", "description": desc,
                      "parameters": {"type": "object", "properties": {
                          "url": {"type": "string", "default": BASE + path},
                          "method": {"type": "string", "default": "POST"},
                          "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                          "body": body}}},
         "post_process_code": hk}
    if pre:
        t["pre_process_code"] = pre
    return t

CID = {"type": "string", "default": "{{customer_id}}"}

verify_tool = api_tool("verify_identity", "verify_identity", {
    "customer_id": CID,
    "field": {"type": "string", "enum": ["date_of_birth", "phone_last4"], "default": "{{field}}", "description": "Which answer this is: date_of_birth or phone_last4."},
    "answer": {"type": "string", "default": "{{answer}}", "description": "date_of_birth as YYYY-MM-DD (day, month, year order when said only as numbers); phone_last4 as four digits."}},
    "Check ONE security answer. CALL it every time the customer gives the date of birth or the last four phone digits. Follow what_to_do_next in the result.",
    VERIFY_HOOK, ["field", "answer"])

promise_tool = api_tool("create_promise", "create_promise", {
    "customer_id": CID,
    "product_id": {"type": "string", "default": "{{product_id}}", "description": "product_id exactly as in the product facts of your instructions."},
    "amount": {"type": "number", "default": "{{amount}}", "description": "Confirmed amount, digits only."},
    "date": {"type": "string", "default": "{{date}}", "description": "Confirmed payment date YYYY-MM-DD, taken from the date check decision."}},
    "Record the payment promise. CALL it ONLY after the customer clearly said yes to the read-back of product, amount and date. Never say it is recorded until this returns ok true.",
    hook("Promise recorded. Say exactly: \"You will receive a text message confirming this promise.\" Then thank the customer, say goodbye and call close_call with outcome promise (no reason). If the customer asks to change or cancel it, say they can change it in the mobile app.",
         "The promise was NOT recorded (nothing was saved). If this is the first failure, tell the customer you are trying again and call create_promise once more with the same values. If it failed twice, say you could not record it, thank the customer, say goodbye and call close_call with outcome no_promise and reason service_error."),
    ["product_id", "amount", "date"])

callback_tool = api_tool("schedule_callback", "schedule_callback", {
    "customer_id": CID,
    "date": {"type": "string", "default": "{{date}}", "description": "Callback date YYYY-MM-DD."},
    "time": {"type": "string", "default": "{{time}}", "description": "Callback time HH:MM, 24 hour."}},
    "Book the callback. CALL it only when the person gave a date and time inside the allowed callback window.",
    hook("Callback booked. Thank the person, say goodbye and call close_call with outcome not_reached and reason callback.",
         "The callback was NOT booked (nothing saved). Try once more with the same values; if it fails again, apologise, say goodbye and call close_call with outcome not_reached and reason no_callback."),
    ["date", "time"])

transfer_tool = api_tool("transfer_to_agent", "transfer_to_agent", {
    "customer_id": CID,
    "queue": {"type": "string", "enum": ["restructuring", "general", "support"], "default": "{{queue}}", "description": "restructuring (payment plan or lower instalments), general (wants a human), support (hardship, customer accepted support team)."}},
    "Hand the call to a person. CALL it only in the cases named in your instructions, after the customer agreed or insisted.",
    hook("Transfer done. Tell the customer you are connecting them, thank them, say goodbye and call close_call with outcome transferred and the reason equal to the queue used (restructuring, human for general, support).",
         "The transfer did NOT happen. Try once more; if it fails again tell the customer you could not transfer, say goodbye and call close_call with outcome no_promise and reason service_error."),
    ["queue"])

close_tool = api_tool("close_call", "close_call", {
    "customer_id": CID,
    "outcome": {"type": "string", "enum": ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"], "default": "{{outcome}}", "description": "promise, paid, transferred, no_promise, not_verified or not_reached."},
    "reason": {"type": "string", "enum": ["restructuring", "human", "support", "refused", "hardship", "dispute", "service_error", "failed", "declined", "callback", "no_callback", "wrong_number", "deceased", "unclear"], "default": "{{reason}}", "description": "Leave out for promise and paid. transferred: restructuring, human, support. no_promise: refused, hardship, dispute, service_error. not_verified: failed, declined. not_reached: callback, no_callback, wrong_number, deceased, unclear."}},
    "End-of-call record. CALL it exactly once, as the very last tool call, only after you have thanked the customer and said goodbye in the same message.",
    hook("The call is recorded as closed. Say nothing more and call no other tool.",
         "The close was NOT recorded. Call close_call once more with the same outcome and reason."),
    ["outcome"],
    pre="try:\n    b = config.get('body')\n    if isinstance(b, dict) and b.get('outcome') in ('promise', 'paid'):\n        b.pop('reason', None)\nexcept Exception:\n    pass\n")

SYS = ("You are Freya Bank's digital assistant on a phone call. Speak English. At most two short sentences per turn. "
       "FIRST answer any question in the customer's last message in one short sentence, then continue with your step: "
       "if asked whether you are a robot or an AI, say you are Freya Bank's digital assistant; "
       "if asked whether this is a scam, say they can verify the call by phoning Freya Bank's customer service number; "
       "for any other question you cannot answer from your tools or instructions, say you do not have that information and never invent figures, dates or reasons. "
       "Call at most one tool per message. After every tool result you must speak to the customer or call the next tool, and you must follow the tool result's what_to_do_next. "
       "Say an action is done only if its tool returned ok true; if a tool failed or returned an error, say plainly that it was not done. "
       "Never offer a discount, waiver, instalment plan or any term not in your instructions. "
       "Address the customer as {{title}} {{last_name}}. Never end the call without exactly one close_call as your last tool call, preceded by thanks and goodbye in the same message.")

DATE_CODE = '''
import datetime
HOL = %s
def isbd(d):
    return d.weekday() < 5 and d.isoformat() not in HOL
def nbd(d):
    d = d + datetime.timedelta(days=1)
    while not isbd(d):
        d = d + datetime.timedelta(days=1)
    return d
def lbd(monday):
    d = monday + datetime.timedelta(days=4)
    while not isbd(d):
        d = d - datetime.timedelta(days=1)
    return d
DN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
def sp(d):
    return DN[d.weekday()] + ' ' + str(d.day) + ' ' + MN[d.month - 1] + ' (' + d.isoformat() + ')'
try:
    s = str(vars.get('now') or '').strip()
    today = datetime.date.fromisoformat(s[:10])
    tm = s[11:16] if len(s) >= 16 else ''
    monday = today - datetime.timedelta(days=today.weekday())
    lines = []
    for i in range(7):
        lines.append('this ' + DN[i] + ' = ' + sp(monday + datetime.timedelta(days=i)))
    for i in range(7):
        lines.append('next ' + DN[i] + ' = ' + sp(monday + datetime.timedelta(days=7 + i)))
    nb = nbd(today)
    vars['today_iso'] = today.isoformat()
    vars['cal_text'] = 'Today is ' + sp(today) + ', time now ' + (tm or 'unknown') + '.\\n' + '\\n'.join(lines)
    vars['cb_text'] = 'Today is ' + sp(today) + ', time now ' + (tm or 'unknown') + '. Allowed callback: today (only a time later than now) or the next business day ' + sp(nb) + ', from 10:00 to 19:00 both included. Bank holidays: 2026-10-26, 2026-11-11, 2026-11-26, 2026-12-25, 2027-01-01. Business days are Monday to Friday except those holidays.'
    vars['dates_state'] = 'ok'
except Exception:
    vars['today_iso'] = ''
    vars['cal_text'] = 'unknown'
    vars['cb_text'] = 'unknown'
    vars['dates_state'] = 'missing'
''' % json.dumps(HOL)

DEAL_CODE = '''
import datetime, json, re
HOL = %s
def isbd(d):
    return d.weekday() < 5 and d.isoformat() not in HOL
def addbd(d, n):
    c = 0
    while c < n:
        d = d + datetime.timedelta(days=1)
        if isbd(d):
            c += 1
    return d
def lbd(monday):
    d = monday + datetime.timedelta(days=4)
    while not isbd(d):
        d = d - datetime.timedelta(days=1)
    return d
DN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
def sp(d):
    return DN[d.weekday()] + ' ' + str(d.day) + ' ' + MN[d.month - 1] + ' (' + d.isoformat() + ')'
try:
    today = datetime.date.fromisoformat(str(vars.get('now') or '')[:10])
    found = dict()
    for k in list(vars.keys()):
        m = re.search(r'products\\.(\\d+)\\.(\\w+)$', str(k))
        if m:
            found.setdefault(int(m.group(1)), dict())[m.group(2)] = vars.get(k)
    prods = [found[i] for i in sorted(found.keys())]
    p = prods[0]
    late = int(float(p.get('days_late')))
    due = float(p.get('past_due'))
    typ = str(p.get('type'))
    if typ == 'credit_card':
        phrase = 'credit card ending ' + str(p.get('card_last4'))
        floor = float(p.get('minimum_payment'))
    elif typ == 'personal_loan':
        phrase = 'personal loan'
        floor = float(p.get('instalment_amount'))
    else:
        phrase = 'car loan'
        floor = float(p.get('instalment_amount'))
    if 1 <= late <= 7:
        band, nd, att = 'early', 12, 1
    elif 8 <= late <= 45:
        band, nd, att = 'late', 7, 2
    else:
        raise ValueError('days_late outside 1-45')
    dl = addbd(today, nd)
    monday = today - datetime.timedelta(days=today.weekday())
    a1 = lbd(monday)
    if a1 <= today:
        a1 = lbd(monday + datetime.timedelta(days=7))
    def fm(x):
        return ('%%.2f' %% x)
    txt = ('Product: ' + phrase + '. product_id (copy exactly): ' + str(p.get('product_id')) + '. Past-due amount: ' + fm(due) + '. Days late: ' + str(late) + '. Band: ' + band + '. '
           'Floor (lowest amount that can be recorded): ' + fm(floor) + '. Deadline (latest promise date): ' + sp(dl) + '. Persuasion attempts allowed: ' + str(att) + '. '
           'Attempt 1 date (last business day of this week, or of next week if today is that day): ' + sp(a1) + '. ')
    if att == 2:
        txt += 'Attempt 2 (late band only): the floor amount ' + fm(floor) + ' on the deadline ' + sp(dl) + '.'
    else:
        txt += 'There is no attempt 2 in the early band.'
    vars['deal_text'] = txt
    vars['acct_products'] = json.dumps([dict(product_id=str(p.get('product_id')), days_late=late)])
    vars['acct_state'] = 'ok'
except Exception:
    vars['deal_text'] = 'unavailable'
    vars['acct_products'] = '[]'
    vars['acct_state'] = 'error'
''' % json.dumps(HOL)

def code_node(name, code, nxt, trans=None):
    return {"name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": nxt,
            "on_enter": {"type": "silent"},
            "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {
                "code": {"type": "string", "default": code}, "timeout_ms": {"type": "number", "default": 8000}}}}}],
            "transitions": (trans or []) + [always(nxt)]}

CLOSED = {"target_node": "hangup", "description": "close_call succeeded", "condition": gt0("close_call_success_count")}

def conv(name, task, tools, trans, enter=None, extraction=None, turns=30, first_only=False):
    n = {"name": name, "node_type": "conversation", "task_message": task, "tools": tools,
         "max_node_turns": turns, "max_turn_transition": "wrap_up", "transitions": trans}
    if enter:
        n["on_enter"] = enter
    if first_only:
        n["on_enter_first_entry_only"] = True
    if extraction:
        n["extraction_schema"] = extraction
    return n

RULE_TALK = ("If the customer says twice that they do not want to talk, thank them, say goodbye and close ")
HUMAN = ("If the customer asks for a human, first ask once whether you can help; if they insist, call transfer_to_agent with queue general, then close_call transferred / human. ")

nodes = {}
nodes["setup"] = code_node("setup", DATE_CODE, "opening",
                           [{"target_node": "setup_error", "description": "now missing", "condition": eq("dates_state", ["missing"])}])
nodes["setup_error"] = conv("setup_error",
    "The current date is not available, so you cannot continue the call. Say you are sorry, there is a technical problem and the bank will call again; thank them, say goodbye, then call close_call with outcome not_reached and reason unclear. Do not mention any account.",
    [close_tool], [CLOSED], enter={"type": "llm"}, turns=4)

SPEAKER = [{"name": "speaker", "type": "string", "enum_values": ["self", "other"], "min_confidence": 0.65,
            "description": "self only if the person clearly confirmed being the customer ('yes', 'that's me', 'speaking', or says the customer's own name). other if somebody else answers, or says the customer is not here/unavailable, or is a relative. Empty for 'hello', 'go ahead', 'who is this' or unclear."}]
nodes["opening"] = conv("opening",
    "Stage: who is on the line. The opening sentence and the question 'Am I speaking with {{title}} {{last_name}}?' were already said. Do NOT say 'collections', 'debt', 'payment' or any product, for anyone, including relatives. "
    "Only 'yes', 'that's me', 'speaking' or the customer's own name counts as confirmation; 'hello', 'go ahead', 'who is this' do not. Answer a question first (robot/AI, scam), then ask 'Am I speaking with {{title}} {{last_name}}?' once more. If it is still unclear after that second ask, thank them, say goodbye and call close_call not_reached / unclear. "
    "If the person says the number does not belong to the customer, say goodbye and close_call not_reached / wrong_number. If the person says the customer has died, say exactly 'I am sorry for your loss.', ask nothing else, then close_call not_reached / deceased. "
    "If someone else answers, say nothing more about the call. " + HUMAN + RULE_TALK + "not_verified / declined. No other tools than listed.",
    [transfer_tool, close_tool],
    [CLOSED,
     {"target_node": "identity", "description": "The customer confirmed being the customer", "condition": eq("speaker", ["self"])},
     {"target_node": "third_party", "description": "Someone else answers", "condition": eq("speaker", ["other"])},
     always("opening", "stay")],
    enter={"type": "tts", "text": "Hello, I am a digital assistant calling from Freya Bank, and this call is recorded. Am I speaking with {{title}} {{last_name}}?"},
    extraction=SPEAKER, first_only=True)

nodes["third_party"] = conv("third_party",
    "Stage: someone other than the customer is on the line. Do not say why you are calling and say nothing about the account or any money matter, even if they offer to pay. Do not ask security questions. Ask when the customer can be reached. "
    "Calendar and callback window: {{cb_text}} "
    "If they give a day and time inside the window (later than now), call schedule_callback with the date and time (HH:MM). If the day or time is outside the window, ask once for another time; if that is also outside, do not schedule: say goodbye and close_call not_reached / no_callback. "
    "If they say the number does not belong to the customer: goodbye, close_call not_reached / wrong_number. If they say the customer has died: say exactly 'I am sorry for your loss.', ask nothing else, close_call not_reached / deceased. "
    "If the person turns out to be the customer, continue by asking nothing about the account yet. " + HUMAN,
    [callback_tool, transfer_tool, close_tool],
    [CLOSED, {"target_node": "identity", "description": "The person is the customer", "condition": eq("speaker", ["self"])}, always("third_party", "stay")],
    enter={"type": "llm", "prompt": "Answer any question briefly (without saying why you call), then ask when the customer can be reached."},
    extraction=SPEAKER)

nodes["identity"] = conv("identity",
    "Stage: identity. Do not mention debt, payment, collections or the product. You may not call get_account. Ask two security questions, ONE at a time: first the date of birth, then the last four digits of the phone number on file. After each answer CALL verify_identity (date of birth as YYYY-MM-DD; a date said only in numbers is day, then month, then year). "
    "A wrong answer may be asked again; three wrong answers in total end the check (the tool tells you). If the tool hints day_month_swapped, ask the customer to say the month as a word (this is not a wrong answer). "
    "After three wrong answers do not state the debt: tell the customer to use the mobile app or a branch, goodbye, close_call not_verified / failed. "
    "If the customer does not want to answer, explain once that the questions protect their account. If they still decline, goodbye, close_call not_verified / declined. Asking what the call is about instead of answering counts as declining; a second refusal or second such question closes the call (not_verified / declined). "
    "If the customer says twice they do not want to talk: goodbye, close_call not_verified / declined. " + HUMAN + " Never share account information here.",
    [verify_tool, transfer_tool, close_tool],
    [CLOSED,
     {"target_node": "fetch_account", "description": "Both answers verified",
      "condition": eq("verify_identity_response.data.all_verified", ["true", "True"])},
     always("identity", "stay")],
    enter={"type": "llm", "prompt": "Answer any question briefly (without mentioning the reason for the call), then say thanks and ask for the date of birth."},
    first_only=True)

acct_tool = api_tool("get_account", "get_account", {"customer_id": CID}, "Get the late products.",
                     hook("ok", "failed"), [], retries=2)
nodes["fetch_account"] = {"name": "fetch_account", "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "build_deal",
    "on_enter": {"type": "silent"}, "pre_actions": [acct_tool], "transitions": [always("build_deal")]}
nodes["build_deal"] = code_node("build_deal", DEAL_CODE, "negotiate",
    [{"target_node": "account_error", "description": "account missing", "condition": eq("acct_state", ["error"])}])
nodes["account_error"] = conv("account_error",
    "The account information could not be loaded. Do not state any amount. Say you are sorry, you could not access the account details now, thank the customer, say goodbye, then call close_call with outcome no_promise and reason service_error.",
    [close_tool], [CLOSED], enter={"type": "llm"}, turns=4)

NEG = (
"Stage: the debt and the promise. Identity is verified. Product facts (from the account tool; use only these): {{deal_text}}\n"
"Calendar (use it to turn the customer's words into YYYY-MM-DD; 'next <weekday>' is that weekday in the following calendar week, 'this <weekday>' is in the current week):\n{{cal_text}}\n"
"Opening of this stage: say you are calling from the collections team about a late payment, name the product in words, state the past-due amount and the days late. Then ask exactly: 'Can you make this payment today?'. Ask for the full past-due amount first; never ask 'how much can you pay'. You propose every amount.\n"
"DATES: for every day or period the customer names (and every date you are about to propose or read back) CALL check_payment_date first with the YYYY-MM-DD from the calendar, or 'vague' if no exact day; never judge whether a day is allowed yourself and never state a date rule yourself. After the decision is read out, continue from it: the date to use is {{date_proposed}} (decision {{date_decision}}: ok, not_business_day, after_deadline, past, ask_exact, propose_deadline, error). If the decision proposes a date, the customer must accept it. If the customer refuses the deadline date (after_deadline) treat it as a flat refusal.\n"
"AMOUNTS: if the customer says the full amount is too much, offer the floor once and say the rest stays overdue; if refused, flat refusal. An amount from the floor up to the full amount (inclusive) is accepted. Below the floor: say it cannot be recorded and offer the floor once; if not accepted, flat refusal.\n"
"A date or amount the customer proposes is never a refusal. A flat refusal or non-answer (including a no to paying today with no date and no amount) uses one persuasion attempt. Attempt 1: the full past-due amount (or the floor if the customer already said the full amount is too much) on the Attempt 1 date from the facts. Attempt 2 (late band only): the floor on the deadline. Never repeat an offer already refused. When attempts are used up: thank, goodbye, close_call no_promise / refused.\n"
"HARDSHIP: if the customer mentions illness, a death in the family or job loss: one short sentence of sympathy, no persuasion attempt, offer to connect them with the customer support team. If they accept: transfer_to_agent queue support, then close_call transferred / support. If they decline: close_call no_promise / hardship. If they still name a date or amount themselves, handle it under DATES and AMOUNTS and record it.\n"
"CONFIRM: once product, amount and a checked date are agreed, read the product, amount and date back and ask 'Do you confirm?'. CALL create_promise ONLY after a clear yes, with product_id from the facts. If the customer changes date or amount at this step, re-check it and read back again. One promise per product; a recorded promise cannot be changed or cancelled in this call (they can change it in the mobile app). Say it is recorded only after create_promise returned ok true; then say exactly 'You will receive a text message confirming this promise.', thank, goodbye, close_call promise.\n"
"OTHER: 'I already paid': say payments can take one business day to appear, take no promise, goodbye, close_call paid. 'Not my debt' or 'never had this product' or the product was closed/paid off in the past: do not argue, no promise, goodbye, close_call no_promise / dispute. Request for a new payment plan or lower instalments: do not describe a plan; transfer_to_agent queue restructuring, then close_call transferred / restructuring. "
"Request for a human: first ask once whether you can help; if they insist transfer_to_agent queue general, then close_call transferred / human. If the customer says twice they do not want to talk: goodbye, close_call no_promise / refused. If a transfer follows a recorded promise, close as transferred with that reason."
)

nodes["negotiate"] = conv("negotiate", NEG, [], [CLOSED, always("negotiate", "stay")],
    enter={"type": "llm"}, turns=40, first_only=True)

nodes["wrap_up"] = conv("wrap_up",
    "The call must end now. Thank the customer, say goodbye, then call close_call with the outcome that matches what happened: promise only if create_promise returned ok true; otherwise use the best fitting outcome and reason (not_verified / declined before identity passed, else no_promise / refused). Do not mention any account details unless identity was verified.",
    [close_tool], [CLOSED], enter={"type": "llm"}, turns=4)

nodes["hangup"] = {"name": "hangup", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
    "terminal": {"type": "function", "function": {"name": "call_finished", "handler": "__function__:end_call",
        "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}}}

# merge date tool
dt = json.load(open(os.path.join(D, "date_out.json"), encoding="utf-8"))
neg = nodes["negotiate"]
neg["tools"] = [dt["tool"], promise_tool, transfer_tool, close_tool]
neg["transitions"] = [dt["transition"]] + neg["transitions"]
nodes.update(dt["nodes"])

wf = {"initial_node": "setup", "system_prompt": SYS, "nodes": nodes,
      "test_variables": {"first_name": "Daniel", "last_name": "Reyes", "title": "Mr", "now": "2026-10-14T11:00"}}
json.dump(wf, open(os.path.join(D, "workflow.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("written")

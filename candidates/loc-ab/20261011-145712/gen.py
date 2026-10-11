import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://freya-bank-mock.freyavoice.workers.dev/v1/"
date_out = json.load(open(os.path.join(HERE, "date_out.json"), encoding="utf-8"))

HOL = ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"]

COMMON = r'''
import datetime, json, re
HOL = %s
DN = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
MN = ['January','February','March','April','May','June','July','August','September','October','November','December']
def sp(d):
    return DN[d.weekday()] + ' ' + str(d.day) + ' ' + MN[d.month-1] + ' (' + d.isoformat() + ')'
def isbd(d):
    return d.weekday() < 5 and d.isoformat() not in HOL
def addbd(d, n):
    c = 0
    while c < n:
        d = d + datetime.timedelta(days=1)
        if isbd(d):
            c += 1
    return d
def nextbd(d):
    return addbd(d, 1)
def lastbd_of_week(d):
    mon = d - datetime.timedelta(days=d.weekday())
    best = None
    for i in range(5):
        x = mon + datetime.timedelta(days=i)
        if isbd(x):
            best = x
    return best
''' % json.dumps(HOL)

CAL_CODE = COMMON + r'''
vars['now_state'] = 'missing'
vars['calendar_facts'] = 'Calendar unavailable.'
vars['callback_facts'] = 'Callback window unavailable.'
try:
    raw = str(vars.get('now') or '').strip()
    if len(raw) < 10:
        raise ValueError('no now')
    today = datetime.date.fromisoformat(raw[:10])
    hhmm = raw[11:16] if len(raw) >= 16 else '00:00'
    lines = []
    lines.append('Today is ' + sp(today) + ', current time ' + hhmm + '. Business days are Monday to Friday except these Freya Bank holidays: ' + ', '.join(HOL) + '.')
    mon = today - datetime.timedelta(days=today.weekday())
    tw = []
    nw = []
    for i in range(7):
        tw.append('this ' + DN[i] + ' = ' + (mon + datetime.timedelta(days=i)).isoformat())
        nw.append('next ' + DN[i] + ' = ' + (mon + datetime.timedelta(days=7+i)).isoformat())
    lines.append('"This <weekday>" means the one in the current calendar week: ' + '; '.join(tw) + '.')
    lines.append('"Next <weekday>" means that weekday in the following calendar week: ' + '; '.join(nw) + '.')
    lb = lastbd_of_week(today)
    if lb == today:
        a1 = lastbd_of_week(today + datetime.timedelta(days=7))
        lines.append('Today is the last business day of this week, so persuasion attempt 1 proposes the last business day of next week: ' + sp(a1) + '.')
    else:
        a1 = lb
        lines.append('Persuasion attempt 1 proposes the last business day of this week: ' + sp(a1) + '.')
    vars['attempt1_date'] = a1.isoformat()
    lines.append('Next business day after today: ' + sp(nextbd(today)) + '.')
    vars['calendar_facts'] = '\n'.join(lines)
    nb = nextbd(today)
    cb = []
    try:
        h = int(hhmm[:2]); m = int(hhmm[3:5])
        mins = h*60 + m
    except Exception:
        mins = 0
    if mins < 19*60:
        start = max(10*60, mins+1)
        cb.append('Callback today (' + today.isoformat() + '): any time from %02d:%02d to 19:00.' % (start//60, start%60))
    else:
        cb.append('Callback today is no longer possible (19:00 has passed).')
    cb.append('Callback on the next business day (' + nb.isoformat() + '): any time from 10:00 to 19:00, both included.')
    cb.append('Any other day or time is outside the window.')
    vars['callback_facts'] = ' '.join(cb)
    vars['now_state'] = 'ok'
except Exception:
    vars['now_state'] = 'missing'
'''

PREP_CODE = COMMON + r'''
vars['acct_state'] = 'empty'
vars['product_facts'] = 'No products found.'
vars['products'] = '[]'
try:
    raw = str(vars.get('now') or '').strip()
    today = datetime.date.fromisoformat(raw[:10])
    found = dict()
    for k in list(vars.keys()):
        m = re.search(r'products\.(\d+)\.(\w+)$', str(k))
        if m:
            found.setdefault(int(m.group(1)), dict())[m.group(2)] = vars.get(k)
    prods = [found[i] for i in sorted(found.keys())]
    if not prods:
        v = vars.get('get_account_response.data.products')
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                v = None
        if isinstance(v, list):
            prods = [p for p in v if isinstance(p, dict)]
    out = []
    lines = []
    n = 0
    for p in prods:
        pid = str(p.get('product_id') or '')
        late = int(float(p.get('days_late')))
        due = float(p.get('past_due'))
        typ = str(p.get('type') or '')
        if typ == 'credit_card':
            name = 'credit card ending ' + str(p.get('card_last4') or '')
            floor = float(p.get('minimum_payment'))
            floor_name = 'minimum payment'
        elif typ == 'personal_loan':
            name = 'personal loan'
            floor = float(p.get('instalment_amount'))
            floor_name = 'instalment amount'
        else:
            name = 'car loan'
            floor = float(p.get('instalment_amount'))
            floor_name = 'instalment amount'
        if late <= 7:
            band, nbd, att = 'early', 12, 1
        else:
            band, nbd, att = 'late', 7, 2
        dl = addbd(today, nbd)
        n += 1
        out.append(dict(product_id=pid, days_late=late))
        lines.append('Product %d (in this order): product_id=%s | say: "%s" | past due %.2f | %d days late | band %s | floor (%s) %.2f | deadline %s | persuasion attempts allowed: %d' % (n, pid, name, due, late, band, floor_name, floor, sp(dl), att))
    if out:
        vars['products'] = json.dumps(out)
        vars['product_facts'] = '\n'.join(lines)
        vars['acct_state'] = 'ok'
except Exception:
    vars['acct_state'] = 'empty'
'''


def code_node(name, code, target, extra_transitions=None):
    return {
        "name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": target,
        "on_enter": {"type": "silent"},
        "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "default": code}, "timeout_ms": {"type": "number", "default": 8000}}}}}],
        "transitions": (extra_transitions or []) + [{"target_node": target, "description": "always", "condition": {"operator": "always"}}],
    }


def cond(var, vals):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": v} for v in vals]}


def trans(target, desc, var, vals):
    return {"target_node": target, "description": desc, "condition": cond(var, vals)}


def hook(body):
    return ("try:\n    if isinstance(result, dict):\n        result.pop('header', None)\n        d = result.get('data')\n"
            "        if isinstance(d, dict):\n            ok = str(d.get('ok')).lower() == 'true'\n" + "\n".join("            " + l for l in body.split("\n")) + "\nexcept Exception:\n    pass\n")


def api_tool(name, path, desc, fields, hookbody, retries):
    props = {"customer_id": {"type": "string", "default": "{{customer_id}}"}}
    req = []
    for f, (typ, d, enum) in fields.items():
        p = {"type": typ, "description": d, "default": "{{%s}}" % f}
        if enum:
            p["enum"] = enum
        props[f] = p
        req.append(f)
    return {"type": "function", "config": {"timeoutMs": 12000, "maxRetries": retries},
            "function": {"name": name, "handler": "__function__:api_call", "description": desc, "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "default": BASE + path}, "method": {"type": "string", "default": "POST"},
                "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                "body": {"type": "object", "properties": props, "required": req}}}},
            "post_process_code": hook(hookbody)}


OUTCOMES = ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"]
close_call = api_tool(
    "close_call", "close_call",
    "CALL it exactly once, as the very last tool call of the call, in the same message as your spoken goodbye. outcome and reason come from the closing table in your instructions. Never call it twice after it succeeded.",
    {"outcome": ("string", "One of: promise, paid, transferred, no_promise, not_verified, not_reached.", OUTCOMES),
     "reason": ("string", "Omit for promise and paid. transferred: restructuring|human|support. no_promise: refused|hardship|dispute|service_error. not_verified: failed|declined. not_reached: callback|no_callback|wrong_number|deceased|unclear.", None)},
    "if ok:\n    d['what_to_do_next'] = 'The call is closed. Say nothing more and call no further tool.'\nelse:\n    d['what_to_do_next'] = 'The call was NOT closed. Call close_call once more with the same outcome and reason.'",
    1)
# reason is optional
close_call["function"]["parameters"]["properties"]["body"]["required"] = ["outcome"]

verify = api_tool(
    "verify_identity", "verify_identity",
    "CALL it every time the customer gives an answer to a security question (date of birth first, then last four digits of the phone number). Never call it before the customer answered.",
    {"field": ("string", "Which answer this is: date_of_birth or phone_last4.", ["date_of_birth", "phone_last4"]),
     "answer": ("string", "date_of_birth as YYYY-MM-DD (read a date said only in numbers as day, then month, then year); phone_last4 as exactly four digits.", None)},
    "hint = str(d.get('hint') or '')\nver = str(d.get('verified')).lower() == 'true'\nallv = str(d.get('all_verified')).lower() == 'true'\nleft = d.get('wrong_answers_left')\n"
    "if hint == 'day_month_swapped':\n    d['what_to_do_next'] = 'Day and month may be swapped. Ask the customer to say the month as a word and call verify_identity again. This retry is not a wrong answer.'\n"
    "elif allv:\n    d['what_to_do_next'] = 'Both answers passed. Say only that the check is complete; the next step follows.'\n"
    "elif ver:\n    d['what_to_do_next'] = 'This answer was correct. Ask the next security question (phone last four digits if the date of birth was just passed).'\n"
    "elif not ok:\n    d['what_to_do_next'] = 'The answer could not be read and did not count as wrong. Ask for it again, the date of birth as day, month and year.'\n"
    "elif left is not None and str(left) == '0':\n    d['what_to_do_next'] = 'Three wrong answers: the check has ended. Do not state any debt. Tell the customer to use the mobile app or a branch, say goodbye and call close_call with outcome not_verified and reason failed.'\n"
    "else:\n    d['what_to_do_next'] = 'Wrong answer; wrong answers left: ' + str(left) + '. Ask the same question again.'",
    0)

callback = api_tool(
    "schedule_callback", "schedule_callback",
    "CALL it once the person on the line offered a callback day and time that is inside the callback window in your instructions.",
    {"date": ("string", "Callback date YYYY-MM-DD, taken from the callback window in your instructions.", None),
     "time": ("string", "Callback time HH:MM, 24 hour, between 10:00 and 19:00.", None)},
    "if ok:\n    d['what_to_do_next'] = 'Callback booked. Say the day and time, say goodbye and call close_call with outcome not_reached and reason callback.'\nelse:\n    d['what_to_do_next'] = 'The callback was NOT booked (nothing saved) after the allowed tries. Say plainly it could not be booked, say goodbye and call close_call with outcome not_reached and reason no_callback. Do not call schedule_callback again.'",
    1)

transfer = api_tool(
    "transfer_to_agent", "transfer_to_agent",
    "CALL it to hand the call to a person, only in the cases your instructions list (restructuring, general, support). Add no notes on a transfer.",
    {"queue": ("string", "restructuring (payment plan or lower instalments), general (insisted on a human), support (hardship accepted).", ["restructuring", "general", "support"])},
    "if ok:\n    d['what_to_do_next'] = 'Transfer done. Say goodbye and call close_call with outcome transferred and the reason equal to the queue (restructuring, human for queue general, support).'\nelse:\n    d['what_to_do_next'] = 'The transfer was NOT completed after the allowed tries. Say plainly it could not be completed, say goodbye and call close_call with outcome transferred and the reason of the request (restructuring, human or support). Do not call transfer_to_agent again.'",
    1)

promise = api_tool(
    "create_promise", "create_promise",
    "CALL it once per product, only after the customer clearly said yes to the read-back of all promises. product_id from the account facts, amount and date exactly as read back.",
    {"product_id": ("string", "Product id copied unchanged from the product facts.", None),
     "amount": ("number", "Promised amount exactly as read back.", None),
     "date": ("string", "Promised date YYYY-MM-DD exactly as read back.", None)},
    "if ok:\n    d['what_to_do_next'] = 'This promise IS recorded. If other confirmed products still need create_promise, call it for the next one now. When all are done, say exactly: You will receive a text message confirming this promise.'\nelse:\n    d['what_to_do_next'] = 'This promise was NOT recorded (nothing saved); the allowed tries are used up. Do not call create_promise again for this product and do not say it is recorded. Continue with the other products; for this product call add_note with reason service_error. If no promise at all was recorded, say you could not record it.'",
    1)

note = api_tool(
    "add_note", "add_note",
    "CALL it once for each product that ends WITHOUT a recorded promise (never on a transfer). product_id from the product facts.",
    {"product_id": ("string", "Product id copied unchanged from the product facts.", None),
     "reason": ("string", "refused, hardship, dispute, paid or service_error.", ["refused", "hardship", "dispute", "paid", "service_error"])},
    "if ok:\n    d['what_to_do_next'] = 'Note saved. Continue with the next product or, when every product is settled, say goodbye and call close_call per the closing table.'\nelse:\n    d['what_to_do_next'] = 'The note was NOT saved after the allowed tries. Do not call add_note again for this product; continue.'",
    1)
for t in (note,):
    pass

dt = date_out["tool"]

END = "end_node"
def end_tr():
    return trans(END, "close_call succeeded", "close_call_response.data.ok", ["true", "True"])

SYSTEM = """You are Freya Bank's digital assistant on a phone call. Speak English, one or two short sentences per turn.
General rules:
- Call at most one tool per message. After every tool result you must speak to the customer or call the next tool; never end a turn silent. Obey the what_to_do_next field of every tool result.
- Always first answer a question in the customer's last message, in one short sentence, then continue: if asked whether you are a robot or an AI, say you are Freya Bank's digital assistant; if asked whether this is a scam, say they can verify the call by phoning Freya Bank's customer service number; if you cannot answer from your tools, say you do not have that information. Never invent figures, dates or reasons.
- Never say an action is done unless the tool result says it succeeded. Plainly say when something was not done.
- Never offer a discount, waiver, instalment plan or any term not in your instructions.
- Every call ends with exactly one close_call, as the last tool call, in the same message as a short thank-you and goodbye. Take outcome and reason only from the closing table in your instructions.
- Before identity is verified never say 'collections', 'debt', 'payment' or the product, to anyone."""

CLOSING_TABLE = """CLOSING (close_call outcome / reason):
- promise: at least one promise was recorded (wins over everything except a transfer).
- paid: no promise recorded and every product was noted paid (or the only product: customer said they already paid).
- transferred / restructuring, human or support: after a transfer (also if promises were recorded earlier; they stay).
- no_promise with reason refused, hardship, dispute or service_error: no promise recorded; use the reason of the first product, in product order, whose note is not paid.
- not_verified failed or declined; not_reached callback, no_callback, wrong_number, deceased or unclear (earlier stages)."""

nodes = {}
nodes["init_dates"] = code_node("init_dates", CAL_CODE, "open", [
    trans("now_missing", "the call date is missing", "now_state", ["missing"])])
nodes["now_missing"] = {"name": "now_missing", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
                        "terminal": {"type": "function", "function": {"name": "now_missing_end", "handler": "__function__:end_call", "parameters": {"type": "object", "properties": {
                            "message_mode": {"type": "string", "default": "custom"},
                            "spoken_message": {"type": "string", "default": "I am sorry, there is a technical problem and I cannot continue this call. Goodbye."}}}}}}

nodes["open"] = {
    "name": "open", "node_type": "conversation",
    "on_enter": {"type": "tts", "text": "Hello, I am a digital assistant calling from Freya Bank, and this call is recorded. Am I speaking with {{title}} {{last_name}}?"},
    "on_enter_first_entry_only": True,
    "task_message": """You have just asked 'Am I speaking with {{title}} {{last_name}}?'. Say nothing about why you call and never mention collections, debt, payment or any product, even to a relative.
{{callback_facts}}
Rules:
- Only 'yes', 'that's me', 'speaking' or the customer's own name confirms. 'Hello', 'go ahead' or 'who is this' do not: answer a question first, then ask once more. If still unclear after the second ask, say goodbye and call close_call not_reached / unclear.
- If someone else answers: do not say why you call, do not take any answer to security questions, tell nothing about the account even if they offer to pay. Ask when the customer can be reached. A callback must be inside the window above. When they give a day and time inside it, call schedule_callback. If the day or time is outside it, ask once for another time; if that is also outside, do not schedule, say goodbye and call close_call not_reached / no_callback.
- If they say the number does not belong to the customer: goodbye, close_call not_reached / wrong_number.
- If they say the customer has died: say exactly 'I am sorry for your loss.', ask nothing else, goodbye, close_call not_reached / deceased.
- If they ask for a human: ask once whether you can help first; if they insist, call transfer_to_agent queue general, then close_call transferred / human. Never add notes.
- If the person says twice they do not want to talk: goodbye, close_call not_verified / declined.
Do not call verify_identity here.""",
    "tools": [callback, close_call, transfer],
    "extraction_schema": [{"name": "line_state", "type": "string", "enum_values": ["customer_confirmed"],
                           "description": "Set to customer_confirmed ONLY if the speaker clearly confirmed to be the customer ('yes', 'that's me', 'speaking', or says the customer's own name). Leave empty for 'hello', 'go ahead', 'who is this', or anyone else.",
                           "min_confidence": 0.7}],
    "transitions": [end_tr(), trans("identity", "the customer confirmed who they are", "line_state", ["customer_confirmed"]),
                    {"target_node": "open", "description": "stay", "condition": {"operator": "always"}}],
}

nodes["identity"] = {
    "name": "identity", "node_type": "conversation",
    "on_enter": {"type": "llm", "prompt": "If the customer's last message asked a question, answer it in one short sentence first. Then say: 'Thank you. For your security I need to ask two questions. First, what is your date of birth?' Do not mention why you call."},
    "on_enter_first_entry_only": True,
    "task_message": """Verify identity with two security questions, one at a time: first the date of birth, then the last four digits of the phone number on file. After each answer call verify_identity. Send a date of birth as YYYY-MM-DD whatever way it was said; a date said only in numbers is day, then month, then year. Never say whether you expect an answer to be right.
- A wrong answer may be asked again; three wrong answers in total end the check, whichever question. Follow what_to_do_next.
- If verify_identity returns hint day_month_swapped, ask them to say the month as a word (not a wrong answer).
- After three wrong answers: do not state any debt, tell them to use the mobile app or a branch, goodbye, close_call not_verified / failed.
- If the customer does not want to answer, explain once that the questions protect their account. If they still decline, goodbye, close_call not_verified / declined. Asking what the call is about instead of answering counts as declining: the first time explain once; a second refusal or a second such question closes the call as not_verified / declined.
- If the customer says twice that they do not want to talk: close_call not_verified / declined.
- If they ask for a human: ask once whether you can help first; if they insist call transfer_to_agent queue general then close_call transferred / human.
- Never say what the call is about, never mention collections, debt, payment or a product. Say nothing about the account.""",
    "tools": [verify, close_call, transfer],
    "transitions": [end_tr(), {"target_node": "fetch_account", "description": "both security answers verified",
                               "condition": cond("verify_identity_response.data.all_verified", ["true", "True"])},
                    {"target_node": "identity", "description": "stay", "condition": {"operator": "always"}}],
}

nodes["fetch_account"] = {
    "name": "fetch_account", "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "prep_products",
    "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
    "pre_actions": [{"type": "function", "config": {"timeoutMs": 12000, "maxRetries": 2}, "function": {
        "name": "get_account", "handler": "__function__:api_call", "description": "Get the late products.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "default": BASE + "get_account"}, "method": {"type": "string", "default": "POST"},
            "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
            "body": {"type": "object", "properties": {"customer_id": {"type": "string", "default": "{{customer_id}}"}}, "required": ["customer_id"]}}}}}],
    "transitions": [{"target_node": "prep_products", "description": "always", "condition": {"operator": "always"}}],
}
nodes["prep_products"] = code_node("prep_products", PREP_CODE, "negotiate", [
    trans("account_error", "no products could be read", "acct_state", ["empty"])])

nodes["account_error"] = {
    "name": "account_error", "node_type": "conversation",
    "on_enter": {"type": "llm", "prompt": "Say that you could not retrieve the account details just now (nothing was recorded), apologise, say goodbye and call close_call with outcome no_promise and reason service_error."},
    "task_message": "You could not load the account. Say so plainly, apologise, say goodbye and call close_call with outcome no_promise and reason service_error. Make no promise and state no debt.",
    "tools": [close_call], "transitions": [end_tr(), {"target_node": "account_error", "description": "stay", "condition": {"operator": "always"}}],
}

NEG = """Identity is verified. The customer is {{title}} {{last_name}}. Follow what_to_do_next of every tool result. Answer any question in the customer's last message first (rules in your system prompt), in one short sentence.
{{calendar_facts}}
PRODUCT FACTS (copy product_id unchanged; state products and amounts as given):
{{product_facts}}

START: say you are calling from the collections team about a late payment. State EVERY late product above, one sentence each: its name in words, the past-due amount and how many days late. Then ask once: 'Can you make this payment today?' (with several products: 'Can you pay all of them today?'). Only once; with several products and a 'no', go through the products one by one in the order above without asking about today again. Each product starts at persuasion attempt 1. Attempts are counted per product. Keep a short private tally per product: promised / noted / open.

AMOUNTS: Ask for the full past-due amount first. Never ask 'how much can you pay?'; you propose every amount. If the customer says the full amount is too much, offer the floor, once, and say the rest stays overdue. If they propose an amount from the floor up to the full amount (both included), accept it. Below the floor: say it cannot be recorded and offer the floor once. If they refuse the floor it is a flat refusal.
DATES: A promise date must be today or later, a business day, and not after that product's deadline. For every day or period the customer names, call check_payment_date (date as YYYY-MM-DD from the calendar above, or 'vague' for a vague period; product_id of that product). Never say yourself whether a day is allowed; the decision is read out and stored in {{date_decision}}, with the date to use in {{date_proposed}} for product {{date_product}}. If the customer accepts that date, use {{date_proposed}} for that product. If the customer names one date for everything, call check_payment_date once per product (one per message); a product whose date is after its deadline is recorded on its own deadline and you say so in the read-back; the others keep the date the customer named. If the customer refuses the deadline it is a flat refusal. A date or amount the customer proposes is never a refusal.
PERSUASION: A flat refusal or non-answer uses one attempt (a 'no' to paying today with no date and no amount is a flat refusal). Attempt 1: full past-due amount (or the floor if the customer already said the full amount is too much) on the attempt-1 date from the calendar. Attempt 2 (late band only): the floor on that product's deadline. When the attempts for a product are used up, stop; never repeat a refused offer; the product ends without promise with note reason refused.
HARDSHIP: if the customer mentions illness, a death in the family or job loss: one short sentence of sympathy, no persuasion attempt, offer to connect them with the customer support team. If they accept: call transfer_to_agent queue support, then close_call transferred / support. If they decline: products without promise get add_note hardship; the close is no_promise / hardship per the table. If they still name a date or amount, record that promise as usual.
OTHER:
- 'I already paid': say payments can take one business day to appear, take no promise for that product, add_note reason paid for it, continue with other products.
- 'not mine' / 'never had this product' / product closed or paid off in the past: do not argue, take no promise for that product, add_note reason dispute, continue with the others.
- New payment plan or lower instalments: do not describe a plan. Call transfer_to_agent queue restructuring then close_call transferred / restructuring. Add NO notes at all on a transfer. Promises already recorded stay; agreed but unrecorded ones are not recorded.
- Request for a human: ask once whether you can help first; if they insist call transfer_to_agent queue general then close_call transferred / human (no notes).
- If the customer says twice they do not want to talk: add_note refused for each product without promise, then close_call no_promise / refused (or per table).
CONFIRM AND RECORD: When every product is settled (promise terms agreed or ended without promise), read ALL promises back together (product name, amount, date; say if a date was moved to the deadline) and ask 'Do you confirm?'. Call create_promise (once per product, one per message) only after a clear yes. If the customer changes a date or amount at this step, check the new value (check_payment_date for a date) and read everything back again. Say a promise is recorded only after create_promise succeeded. One promise per product; a recorded promise cannot be changed or cancelled in this call: they can change it in the mobile app. After promises are recorded say exactly: 'You will receive a text message confirming this promise.' If one create_promise fails, keep the recorded ones and call add_note service_error for the failed product.
NOTES: for each product without a promise call add_note with that product_id and reason refused, hardship, dispute, paid or service_error, before closing (not on transfers).
""" + CLOSING_TABLE + """
Then thank the customer, say goodbye and call close_call in the same message."""

nodes["negotiate"] = {
    "name": "negotiate", "node_type": "conversation",
    "on_enter": {"type": "llm", "prompt": "Start the STATE step now: say you are calling from the collections team about a late payment, state every late product one sentence each (name, past-due amount, days late) using the product facts, then ask the today question. If the customer's last message asked a question, answer it in one short sentence first."},
    "on_enter_first_entry_only": True,
    "task_message": NEG,
    "tools": [dt, promise, note, transfer, close_call],
    "transitions": [end_tr(), date_out["transition"], {"target_node": "negotiate", "description": "stay", "condition": {"operator": "always"}}],
}
for k, v in date_out["nodes"].items():
    nodes[k] = v

nodes[END] = {"name": END, "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
              "terminal": {"type": "function", "function": {"name": "call_closed", "handler": "__function__:end_call", "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}}}

wf = {"initial_node": "init_dates", "system_prompt": SYSTEM, "nodes": nodes,
      "test_variables": {"first_name": "Daniel", "last_name": "Reyes", "title": "Mr", "now": "2026-10-14T11:00"}}
json.dump(wf, open(os.path.join(HERE, "workflow.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("written")

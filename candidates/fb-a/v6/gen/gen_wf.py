import json, sys
W = sys.argv[1]
BASE = "https://freya-bank-mock.freyavoice.workers.dev/v1/"
dt = json.load(open(W + "/gen/date_tool_out.json", encoding="utf-8"))
HOL = json.load(open(W + "/date_config.json"))["holidays"]


def eq(var, *vals):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": v} for v in vals]}


def tr(target, cond, desc):
    return {"target_node": target, "description": desc, "condition": cond}


def always(target):
    return {"target_node": target, "description": "always", "condition": {"operator": "always"}}


def ok_and(tool, extra_var=None, extra_val=None):
    conds = []
    for o in ("true", "True"):
        c = [{"variable": tool + "_response.data.ok", "operator": "equals", "operand": o}]
        if extra_var:
            c.append({"variable": extra_var, "operator": "equals", "operand": extra_val})
        conds.append({"logic": "and", "conditions": c})
    return {"logic": "or", "conditions": conds}


def api_tool(name, props, desc, retries, hook, required):
    body = {}
    for k, (typ, d, enum) in props.items():
        p = {"type": typ, "default": "{{%s}}" % k}
        if d:
            p["description"] = d
        if enum:
            p["enum"] = enum
        body[k] = p
    body["customer_id"] = {"type": "string", "default": "{{customer_id}}"}
    return {"type": "function", "config": {"timeoutMs": 12000, "maxRetries": retries},
            "function": {"name": name, "handler": "__function__:api_call", "description": desc,
                         "parameters": {"type": "object", "properties": {
                             "url": {"type": "string", "default": BASE + name},
                             "method": {"type": "string", "default": "POST"},
                             "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                             "body": {"type": "object", "properties": body, "required": required}}}},
            "post_process_code": hook}


def hook(lines):
    return ("try:\n    result.pop('header', None)\n    d = result.get('data')\n    if isinstance(d, dict):\n        ok = str(d.get('ok')).lower() == 'true'\n"
            + "".join("        " + l + "\n" for l in lines) + "except Exception:\n    pass\n")


H_VERIFY = hook([
    "if ok and str(d.get('all_verified')).lower() == 'true':",
    "    d['what_to_do_next'] = 'Both answers passed. Identity is verified. Say nothing about the debt yet; the next step is handled for you.'",
    "elif d.get('hint') == 'day_month_swapped':",
    "    d['what_to_do_next'] = 'Day and month look swapped. Ask the customer to say the month as a word, then call verify_identity again with date_of_birth as YYYY-MM-DD. This retry is not a wrong answer.'",
    "elif not ok:",
    "    d['what_to_do_next'] = 'The answer could not be read and was NOT counted as wrong. Ask the same question again and call verify_identity again with the corrected format.'",
    "elif str(d.get('verified')).lower() == 'true':",
    "    d['what_to_do_next'] = 'This answer is correct. Ask the next security question (date of birth first, then the last four digits of the phone number on file).'",
    "else:",
    "    d['what_to_do_next'] = 'Wrong answer. Wrong answers left: ' + str(d.get('wrong_answers_left')) + '. If more than 0, say it did not match and ask the same question again. If 0, the check is over: do not state any debt and do not ask more.'"])
H_CB = hook(["d['what_to_do_next'] = 'Callback is booked. Say nothing more about it.' if ok else 'The callback was NOT booked. Say so plainly and try the tool once more with the same date and time.'"])
H_TR = hook(["d['what_to_do_next'] = 'The transfer is done. Say nothing more.' if ok else 'The transfer was NOT done. Say so plainly and try once more; if it fails again say you could not transfer.'"])
H_PROM = hook(["d['what_to_do_next'] = 'The promise is recorded. Do not say anything else; the call is closed for you.' if ok else 'The promise was NOT recorded. All allowed tries are used up. Do not call create_promise again. Say you could not record it.'"])


def transfer_tool():
    return api_tool("transfer_to_agent", {"queue": ("string", "support (illness, death in family, job loss, customer accepted help), restructuring (new payment plan or lower instalments), general (customer insists on a human)", ["restructuring", "general", "support"])},
                    "CALL it ONLY in the cases the prompt names (restructuring request, insisted human request, hardship help accepted). Pick the queue as described. One call only.", 1, H_TR, ["queue"])


TRANSFER_TRANS = [tr("fin_transferred_support", ok_and("transfer_to_agent", "transfer_to_agent_args.queue", "support"), "transfer to support done"),
                  tr("fin_transferred_restructuring", ok_and("transfer_to_agent", "transfer_to_agent_args.queue", "restructuring"), "transfer to restructuring done"),
                  tr("fin_transferred_human", ok_and("transfer_to_agent", "transfer_to_agent_args.queue", "general"), "transfer to general done")]


def ext(name, enum, desc):
    return {"name": name, "type": "string", "enum_values": enum, "description": desc, "min_confidence": 0.65}


def code_node(name, code, nxt, trans=None):
    assert "{{" not in code and "}}" not in code, name
    return {"name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": nxt, "on_enter": {"type": "silent"},
            "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {
                "code": {"type": "string", "default": code}, "timeout_ms": {"type": "number", "default": 8000}}}}}],
            "transitions": (trans or []) + [always(nxt)]}


PREP = r'''
import datetime
DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December']
HOL = %s
try:
    raw = str(vars.get('now') or '').strip()
    now = datetime.datetime.strptime(raw[:16].replace(' ', 'T'), '%%Y-%%m-%%dT%%H:%%M') if len(raw) >= 16 else datetime.datetime.strptime(raw[:10], '%%Y-%%m-%%d')
    today = now.date()
    def isbd(d):
        return d.weekday() < 5 and d.isoformat() not in HOL
    def nbd(d):
        d = d + datetime.timedelta(days=1)
        while not isbd(d):
            d = d + datetime.timedelta(days=1)
        return d
    def sp(d):
        return d.isoformat() + ' (' + DAYS[d.weekday()] + ' ' + str(d.day) + ' ' + MONTHS[d.month-1] + ')'
    mon = today - datetime.timedelta(days=today.weekday())
    def lastbd(m):
        for i in range(6, -1, -1):
            d = m + datetime.timedelta(days=i)
            if isbd(d):
                return d
        return m
    lb = lastbd(mon)
    prop1 = lb if today != lb else lastbd(mon + datetime.timedelta(days=7))
    lines = ['Today is ' + sp(today) + '. Current time: ' + now.strftime('%%H:%%M') + '.']
    lines.append('Is today a business day: ' + ('yes' if isbd(today) else 'no') + '.')
    lines.append('Next business day after today: ' + sp(nbd(today)) + '.')
    lines.append('"This <weekday>" (current calendar week, Monday to Sunday):')
    for i in range(7):
        lines.append('  this ' + DAYS[i] + ' = ' + sp(mon + datetime.timedelta(days=i)))
    lines.append('"Next <weekday>" (the following calendar week):')
    for i in range(7):
        lines.append('  next ' + DAYS[i] + ' = ' + sp(mon + datetime.timedelta(days=7+i)))
    lines.append('Persuasion attempt 1 date (last business day of this week, or of next week if today is that day): ' + sp(prop1) + '.')
    lines.append('Callback window: today or ' + nbd(today).isoformat() + ', time 10:00 to 19:00 both included, and later than ' + now.strftime('%%H:%%M') + ' if today.')
    vars['calendar'] = '\n'.join(lines)
    vars['prep_state'] = 'ok'
except Exception:
    vars['calendar'] = 'Calendar unavailable.'
    vars['prep_state'] = 'missing'
''' % json.dumps(HOL)

ACCT = r'''
import json, re, datetime
HOL = %s
try:
    found = dict()
    for k in list(vars.keys()):
        m = re.search(r'products\.(\d+)\.(\w+)$', str(k))
        if m:
            found.setdefault(int(m.group(1)), dict())[m.group(2)] = vars.get(k)
    p = None
    if found:
        p = found[sorted(found.keys())[0]]
    else:
        v = vars.get('products')
        if isinstance(v, str):
            v = json.loads(v)
        if isinstance(v, list) and v:
            p = v[0]
    if not p or not p.get('product_id'):
        raise ValueError('no product')
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
    if late < 1 or late > 45:
        raise ValueError('days late out of range')
    today = datetime.datetime.strptime(str(vars.get('now'))[:10], '%%Y-%%m-%%d').date()
    n = 12 if late <= 7 else 7
    d = today
    c = 0
    while c < n:
        d = d + datetime.timedelta(days=1)
        if d.weekday() < 5 and d.isoformat() not in HOL:
            c += 1
    band = 'early' if late <= 7 else 'late'
    att = 1 if band == 'early' else 2
    vars['product_id'] = str(p.get('product_id'))
    vars['acct_block'] = ('Product: ' + name + ' (product_id ' + str(p.get('product_id')) + '). Past-due amount: %%.2f. Days late: ' + str(late) + '. Band: ' + band + '. Floor (lowest amount that can be recorded): %%.2f. Deadline (latest promise date): ' + d.isoformat() + '. Persuasion attempts allowed: ' + str(att) + '.') %% (due, floor)
    vars['acct_state'] = 'known'
except Exception as e:
    vars['acct_block'] = 'Account unavailable.'
    vars['acct_state'] = 'unknown'
''' % json.dumps(HOL)

SYSTEM = """You are the digital assistant of Freya Bank, speaking on a phone call in English. Keep every turn to one or two short sentences. Ask one question at a time.
Hard rules for every turn:
- First, if the customer's last message contains a question, answer it in one short sentence, then continue. If they ask whether you are a robot or an AI, say you are Freya Bank's digital assistant. If they ask whether this is a scam, say they can verify the call by phoning Freya Bank's customer service number. If you cannot answer a question from the tools, say you do not have that information; never invent figures, dates or reasons.
- After every tool result, follow its what_to_do_next sentence and then speak to the customer or call the next tool. One tool call per message. Never end a turn with nothing.
- Never offer a discount, a waiver, an instalment plan or any term not given in your instructions.
- Never say something is recorded, booked or transferred unless the tool result said ok. Say plainly if it was not done.
- Never use the words collections, debt, payment or the product name before identity is verified.
- The call is closed for you by the system after you say goodbye; never try to close it yourself."""

nodes = {}
nodes["prep"] = code_node("prep", PREP, "greet", [tr("end_nonow", eq("prep_state", "missing"), "call variable now missing")])
nodes["end_nonow"] = {"name": "end_nonow", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
                      "terminal": {"type": "function", "function": {"name": "error_no_now", "handler": "__function__:end_call", "parameters": {"type": "object", "properties": {
                          "message_mode": {"type": "string", "default": "custom"}, "spoken_message": {"type": "string", "default": "I am sorry, I cannot continue this call right now. Goodbye."}}}}}}

OPEN = "Hello, this is a digital assistant calling from Freya Bank, and this call is recorded. Am I speaking with {{title}} {{last_name}}?"
PARTY_ENUM = ["confirmed", "other_person", "wrong_number", "deceased", "unsure", "declines"]
PARTY_DESC = ("confirmed ONLY if the customer said yes / that's me / speaking / their own name. other_person: someone else answers (relative, colleague) or says the customer is not available. "
              "wrong_number: says the number does not belong to the customer. deceased: says the customer has died. declines: says twice they do not want to talk. "
              "unsure: hello, go ahead, who is this, or anything else unclear. Empty if no answer yet.")


def greet_task(second):
    return ("You asked: 'Am I speaking with {{title}} {{last_name}}?' " + ("This is the second ask: answer any question first, then ask the same question again. " if second else "Wait for the answer. ")
            + "Only 'yes', 'that's me', 'speaking' or the customer's own name counts as confirmation; 'hello', 'go ahead', 'who is this' do not. Do not say why you are calling or mention any account, debt, payment or product. "
            "If the customer asks for a human, ask once whether you can help first; if they insist, call transfer_to_agent with queue general. No other tool calls.")


nodes["greet"] = {"name": "greet", "node_type": "conversation", "on_enter": {"type": "tts", "text": OPEN}, "on_enter_first_entry_only": True,
                  "task_message": greet_task(False), "tools": [transfer_tool()],
                  "extraction_schema": [ext("party", PARTY_ENUM, PARTY_DESC)],
                  "transitions": TRANSFER_TRANS + [tr("identity", eq("party", "confirmed"), "confirmed"), tr("third_party", eq("party", "other_person"), "someone else"),
                                                   tr("fin_wrong_number", eq("party", "wrong_number"), "wrong number"), tr("fin_deceased", eq("party", "deceased"), "deceased"),
                                                   tr("fin_declined", eq("party", "declines"), "no talk"), tr("greet2", eq("party", "unsure"), "unclear, ask once more"), always("greet")]}
nodes["greet2"] = {"name": "greet2", "node_type": "conversation", "on_enter": {"type": "llm", "prompt": "Answer any question the customer just asked in one short sentence, then ask exactly: Am I speaking with {{title}} {{last_name}}? Mention nothing about why you call."},
                   "task_message": greet_task(True), "tools": [transfer_tool()],
                   "extraction_schema": [ext("party2", PARTY_ENUM, PARTY_DESC)],
                   "transitions": TRANSFER_TRANS + [tr("identity", eq("party2", "confirmed"), "confirmed"), tr("third_party", eq("party2", "other_person"), "someone else"),
                                                    tr("fin_wrong_number", eq("party2", "wrong_number"), "wrong number"), tr("fin_deceased", eq("party2", "deceased"), "deceased"),
                                                    tr("fin_declined", eq("party2", "declines"), "no talk"), tr("fin_unclear", eq("party2", "unsure"), "still unclear"), always("greet2")]}

nodes["third_party"] = {"name": "third_party", "node_type": "conversation",
                        "on_enter": {"type": "llm", "prompt": "Answer any question briefly without saying why you call or anything about an account, then ask when the customer can be reached."},
                        "task_message": "Someone other than the customer is on the line. Say nothing about why you are calling, and tell them nothing about any account, even if they offer to pay; they may not answer security questions. Ask when the customer can be reached.\n"
                        "Calendar:\n{{calendar}}\n"
                        "A callback must be today or the next business day, between 10:00 and 19:00 both included, and later than the current time. When the person offers a valid date and time, CALL schedule_callback (date YYYY-MM-DD, time HH:MM 24h). "
                        "If they offer a day or time outside the window, ask once for another time. If the second offer is also outside the window, or they refuse, do not schedule. "
                        "If they say the number does not belong to the customer, or that the customer has died, ask nothing else. Set third_state accordingly.",
                        "tools": [api_tool("schedule_callback", {"date": ("string", "Callback date YYYY-MM-DD, today or the next business day", None), "time": ("string", "Callback time HH:MM 24h, from 10:00 to 19:00, later than now", None)},
                                           "CALL it once the person gave a valid callback date and time inside the window. Never call it for an invalid time.", 1, H_CB, ["date", "time"])],
                        "extraction_schema": [ext("third_state", ["none", "wrong_number", "deceased", "no_callback"], "wrong_number if the person says this number does not belong to the customer; deceased if they say the customer died; no_callback if the person's second proposed day/time is again outside the window, or they refuse to give a time; else none")],
                        "transitions": [tr("fin_callback", ok_and("schedule_callback"), "callback booked"), tr("fin_wrong_number", eq("third_state", "wrong_number"), "wrong number"),
                                        tr("fin_deceased", eq("third_state", "deceased"), "deceased"), tr("fin_no_callback", eq("third_state", "no_callback"), "no valid callback"), always("third_party")]}

nodes["identity"] = {"name": "identity", "node_type": "conversation",
                     "on_enter": {"type": "llm", "prompt": "Answer any question the customer asked in one short sentence (do not mention the debt or account). Then ask for their date of birth."},
                     "task_message": "The customer confirmed who they are. Verify identity with two security questions, one at a time: first the date of birth, then the last four digits of the phone number on file. Do not mention any debt, payment, or product.\n"
                     "CALL verify_identity after each answer: field date_of_birth with the answer as YYYY-MM-DD whatever way they said it (a date given only as numbers is day, then month, then year), or field phone_last4 with four digits. Calendar for reference:\n{{calendar}}\n"
                     "Follow what_to_do_next in every tool result. A wrong answer may be asked again; three wrong answers in total end the check. A day_month_swapped hint: ask the customer to say the month as a word; that retry is not a wrong answer.\n"
                     "If the customer does not want to answer, explain once that the questions protect their account. Asking what the call is about instead of answering counts as declining. If they still decline, or decline a second time, set id_state to declined. Same if they say twice they do not want to talk.\n"
                     "If the customer asks for a human, ask once whether you can help first; if they insist, call transfer_to_agent with queue general. If they ask for a new payment plan, call transfer_to_agent with queue restructuring.",
                     "tools": [api_tool("verify_identity", {"field": ("string", "Which answer this is", ["date_of_birth", "phone_last4"]), "answer": ("string", "date_of_birth as YYYY-MM-DD; phone_last4 as four digits", None)},
                                        "CALL it every time the customer gives a security answer. One answer per call.", 0, H_VERIFY, ["field", "answer"]), transfer_tool()],
                     "extraction_schema": [ext("id_state", ["none", "declined"], "declined only if the customer refused to answer after you explained the questions protect their account (or asked about the call a second time, or twice said they do not want to talk); else none")],
                     "transitions": TRANSFER_TRANS + [tr("get_account_call", eq("verify_identity_response.data.all_verified", "true", "True"), "both passed"),
                                                      tr("fin_failed", eq("verify_identity_response.data.wrong_answers_left", "0"), "three wrong answers"),
                                                      tr("fin_declined", eq("id_state", "declined"), "declined"), always("identity")]}

nodes["get_account_call"] = {"name": "get_account_call", "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "acct", "on_enter": {"type": "silent"},
                             "pre_actions": [{"type": "function", "config": {"timeoutMs": 12000, "maxRetries": 2}, "function": {"name": "get_account", "handler": "__function__:api_call", "description": "Get the late products.",
                                                                                                                                  "parameters": {"type": "object", "properties": {"url": {"type": "string", "default": BASE + "get_account"}, "method": {"type": "string", "default": "POST"},
                                                                                                                                                                               "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                                                                                                                                                                               "body": {"type": "object", "properties": {"customer_id": {"type": "string", "default": "{{customer_id}}"}}, "required": []}}}}}],
                             "transitions": [always("acct")]}
nodes["acct"] = code_node("acct", ACCT, "fin_service_error", [tr("negotiate", eq("acct_state", "known"), "account loaded")])

NEG = ("Account facts (from the system, exact): {{acct_block}}\n"
       "Calendar:\n{{calendar}}\n"
       "Identity is verified. Work through these steps in order:\n"
       "1. In your first message say you are calling from the collections team about a late payment, name the product in words, state the past-due amount and how many days late it is, then ask exactly: \"Can you make this payment today?\"\n"
       "2. Amounts: you propose every amount; never ask 'how much can you pay'. Ask for the full past-due amount first. If the customer says the full amount is too much, offer the floor once and say the rest stays overdue. A customer amount from the floor up to the full amount is accepted. Below the floor say it cannot be recorded and offer the floor once; if they do not accept the floor, it is a flat refusal.\n"
       "3. Dates: for every day or period the customer names (also 'today', 'tomorrow', 'this Friday', 'next Tuesday', 'end of the month'), CALL check_payment_date with date as YYYY-MM-DD read from the calendar above, or 'vague' if no exact day was given, and product_id from the account facts. Never say yourself whether a day is allowed. After its decision is read out, continue from it. If the customer refuses the deadline date, it is a flat refusal.\n"
       "4. A date or amount proposed by the customer is never a refusal. A flat refusal or a non-answer (a no to paying today with no date and no amount) uses one persuasion attempt. Attempts allowed are in the account facts. Attempt 1: propose the full past-due amount (or the floor if the customer already said the full amount is too much) on the attempt 1 date from the calendar (check it with check_payment_date first). Attempt 2 (late band only): propose the floor amount on the deadline date. Never repeat an offer already refused. When the attempts are used up, stop and set deal_state to refused.\n"
       "5. When the customer clearly agrees to an amount and a date that the date check approved, set deal_state to agreed (say nothing more; the next step reads it back).\n"
       "Special cases (these come before the persuasion rules): illness, death in the family or job loss: say one short sentence of sympathy, make no persuasion attempt, offer to connect them with the customer support team; if they accept, CALL transfer_to_agent with queue support; if they decline set deal_state to hardship_declined. If they still name a date or amount themselves, handle it as in steps 2-3.\n"
       "'I already paid': say payments can take one business day to appear, take no promise, set deal_state to paid.\n"
       "'This debt is not mine', 'I never had this product', or the product was closed or paid off in the past: do not argue, take no promise, set deal_state to dispute.\n"
       "A request for a new payment plan or lower instalments: describe no plan; CALL transfer_to_agent with queue restructuring.\n"
       "A request for a human: ask once whether you can help first; if they insist CALL transfer_to_agent with queue general.\n"
       "If the customer says twice that they do not want to talk, set deal_state to refused.\n"
       "Only one promise per product. If asked about changing a recorded promise, say they can change it in the mobile app.")
nodes["negotiate"] = {"name": "negotiate", "node_type": "conversation", "on_enter": {"type": "llm"}, "on_enter_first_entry_only": True,
                      "task_message": NEG, "tools": [dt["tool"], transfer_tool()],
                      "extraction_schema": [ext("deal_state", ["none", "agreed", "paid", "dispute", "refused", "hardship_declined"],
                                                "agreed: customer clearly accepted a specific amount and date that was checked. paid: says they already paid this past-due amount. dispute: not their debt/product, or product closed or paid off in the past. refused: persuasion attempts used up with no agreement, or twice said they do not want to talk. hardship_declined: had illness/death/job loss and declined support transfer. none otherwise.")],
                      "transitions": [dt["transition"]] + TRANSFER_TRANS + [tr("confirm", eq("deal_state", "agreed"), "agreed amount and date"), tr("fin_paid", eq("deal_state", "paid"), "already paid"),
                                                                            tr("fin_dispute", eq("deal_state", "dispute"), "dispute"), tr("fin_refused", eq("deal_state", "refused"), "refused"),
                                                                            tr("fin_hardship", eq("deal_state", "hardship_declined"), "hardship declined"), always("negotiate")]}
nodes.update(dt["nodes"])
nodes["reset_deal"] = code_node("reset_deal", "vars['deal_state'] = 'none'\nvars['confirm_state'] = 'none'\n", "negotiate")

nodes["confirm"] = {"name": "confirm", "node_type": "conversation",
                    "on_enter": {"type": "llm", "prompt": "Read the product, the amount and the date back to the customer and ask exactly: \"Do you confirm?\""},
                    "task_message": "Account facts: {{acct_block}}\nThe customer agreed to an amount and a date. Read the product (in words), the amount and the date back and ask exactly: \"Do you confirm?\" Answer any customer question first in one short sentence.\n"
                    "CALL create_promise only after a clear yes to this read-back, with product_id from the account facts, the agreed amount and the agreed date as YYYY-MM-DD. If the customer says no or wants to change the date or the amount, do not call create_promise; set confirm_state to changed. "
                    "If the create_promise result says it was not recorded, all allowed tries are used up: do not call it again; say plainly that you could not record it.\n"
                    "If the customer asks for a human, ask once whether you can help first; if they insist CALL transfer_to_agent with queue general. For a new payment plan or lower instalments CALL transfer_to_agent with queue restructuring.",
                    "tools": [api_tool("create_promise", {"product_id": ("string", "product_id from the account facts, copied unchanged", None), "amount": ("number", "Agreed amount, a number", None), "date": ("string", "Agreed promise date YYYY-MM-DD", None)},
                                       "CALL it once, only after the customer clearly said yes to the read-back of product, amount and date. Never call it again after it reported failure.", 1, H_PROM, ["product_id", "amount", "date"]), transfer_tool()],
                    "extraction_schema": [ext("confirm_state", ["none", "changed"], "changed if the customer said no or wants a different date or amount at the read-back; else none")],
                    "transitions": TRANSFER_TRANS + [tr("fin_promise", ok_and("create_promise"), "promise recorded"),
                                                     tr("fin_service_error", {"logic": "or", "conditions": [{"variable": "create_promise_failure_count", "operator": "greater_than", "operand": 0}]}, "promise failed after retries"),
                                                     tr("reset_deal", eq("confirm_state", "changed"), "customer changes"), always("confirm")]}

FINALS = {
    "promise": ("promise", "", "Thank you for your time. You will receive a text message confirming this promise. Goodbye."),
    "paid": ("paid", "", "Payments can take one business day to appear. Thank you for your time, goodbye."),
    "transferred_restructuring": ("transferred", "restructuring", "I am transferring you now. Thank you, goodbye."),
    "transferred_human": ("transferred", "human", "I am transferring you now. Thank you, goodbye."),
    "transferred_support": ("transferred", "support", "I am transferring you to the customer support team now. Thank you, goodbye."),
    "refused": ("no_promise", "refused", "I understand. Thank you for your time, goodbye."),
    "hardship": ("no_promise", "hardship", "I understand. Thank you for your time, goodbye."),
    "dispute": ("no_promise", "dispute", "I understand. Thank you for your time, goodbye."),
    "service_error": ("no_promise", "service_error", "I am sorry, I could not complete that. Thank you for your time, goodbye."),
    "failed": ("not_verified", "failed", "I cannot continue without verifying your identity. Please use the mobile app or a branch. Thank you, goodbye."),
    "declined": ("not_verified", "declined", "I understand. Thank you for your time, goodbye."),
    "callback": ("not_reached", "callback", "Thank you, we will call back at the time you gave. Goodbye."),
    "no_callback": ("not_reached", "no_callback", "Thank you for your time. Goodbye."),
    "wrong_number": ("not_reached", "wrong_number", "I am sorry for the mistake. Goodbye."),
    "deceased": ("not_reached", "deceased", "I am sorry for your loss. Goodbye."),
    "unclear": ("not_reached", "unclear", "I could not confirm who I am speaking with. Thank you, goodbye."),
}
for k, (o, r, msg) in FINALS.items():
    code = "vars['outcome'] = %r\nvars['reason'] = %r\n" % (o, r)
    nodes["fin_" + k] = code_node("fin_" + k, code, "end_" + k)
    nodes["end_" + k] = {"name": "end_" + k, "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
                         "terminal": {"type": "function", "function": {"name": "closed_" + k, "handler": "__function__:end_call", "parameters": {"type": "object", "properties": {
                             "message_mode": {"type": "string", "default": "custom"}, "spoken_message": {"type": "string", "default": msg}}}}}}

close_tool = {"type": "function", "config": {"timeoutMs": 12000, "maxRetries": 0, "alwaysRunsAt": ["end_of_call"]},
              "function": {"name": "close_call", "handler": "__function__:api_call", "description": "Record how the call ended.",
                           "parameters": {"type": "object", "properties": {"url": {"type": "string", "default": BASE + "close_call"}, "method": {"type": "string", "default": "POST"},
                                                                           "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                                                                           "body": {"type": "object", "required": ["outcome"], "properties": {
                                                                               "customer_id": {"type": "string", "default": "{{customer_id}}"},
                                                                               "outcome": {"type": "string", "default": "{{outcome}}", "enum": ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"], "description": "How the call ended"},
                                                                               "reason": {"type": "string", "default": "{{reason}}", "description": "Reason per the outcome; empty for promise and paid"}}}}}},
              "pre_process_code": "try:\n    b = config.get('body')\n    if isinstance(b, dict) and (b.get('outcome') in ('promise', 'paid') or not b.get('reason')):\n        b.pop('reason', None)\nexcept Exception:\n    pass\n"}

wf = {"initial_node": "prep", "system_prompt": SYSTEM, "nodes": nodes, "tools": [close_tool],
      "test_variables": {"first_name": "Daniel", "last_name": "Reyes", "title": "Mr", "now": "2026-10-14T11:00"}}
json.dump(wf, open(W + "/workflow.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

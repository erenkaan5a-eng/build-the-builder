"""Generate a date-decision tool for a phone agent: code decides whether a payment date can be recorded and what
to propose; a fixed line (tts) relays the decision word for word.

    python builder/runtime/date_tool.py <date_config.json> <negotiation_node_key>
prints JSON {"tool": ..., "nodes": {...}, "transition": ..., "instructions": ...} to merge into a workflow.

Verified on Freya chat (eval/probes/probe_code_tool.py): a code_exec tool gets the model's arguments in the global
`params`; routing after a tool result is suppressed unless an assistant message precedes it, which the tool's
static preSpeech provides; the code's variables then route to a code node and a tts node.

date_config.json (all values come from the brief, none from this file):
{
  "now_var": "now",                           # call variable holding the current date/time (YYYY-MM-DD...)
  "weekend_days": [5, 6],                      # Python weekday numbers that are not business days
  "holidays": ["YYYY-MM-DD", ...],
  "products_vars": ["products"],               # variables that may hold the account's product list
  "product_id_field": "product_id", "days_late_field": "days_late",
  "bands": [{"min": 1, "max": 7, "deadline_business_days": 12}, ...],
  "vague_asks_before_deadline": 1,             # how many times to ask for an exact day before proposing the deadline
  "say": {                                     # templates; {day} {next} {deadline} are filled by code, as "Tuesday 27 October"
    "checking": "...", "ok": "...", "not_business_day": "...", "after_deadline": "...",
    "past": "...", "ask_exact": "...", "vague_propose_deadline": "...", "error": "..."
  }
}
"""
import json, sys

CODE_TEMPLATE = r'''
import json, datetime, re
CFG = json.loads(r"""__CFG__""")
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
def spoken(d):
    return DAYS[d.weekday()] + ' ' + str(d.day) + ' ' + MONTHS[d.month - 1]
def isbd(d):
    return d.weekday() not in CFG['weekend_days'] and d.isoformat() not in CFG['holidays']
def add_bd(d, n):
    c = 0
    while c < n:
        d = d + datetime.timedelta(days=1)
        if isbd(d):
            c += 1
    return d
def next_bd(d):
    d = d + datetime.timedelta(days=1)
    while not isbd(d):
        d = d + datetime.timedelta(days=1)
    return d
def load_products():
    for name in CFG['products_vars']:
        v = vars.get(name)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                try:
                    import ast
                    v = ast.literal_eval(v)
                except Exception:
                    v = None
        if isinstance(v, list) and v:
            return [p for p in v if isinstance(p, dict)]
    found = dict()
    for k in list(vars.keys()):
        m = re.search(r'products\.(\d+)\.(\w+)$', str(k))
        if m:
            found.setdefault(int(m.group(1)), dict())[m.group(2)] = vars.get(k)
    return [found[i] for i in sorted(found.keys())]
decision, say, proposed, pid = 'error', CFG['say']['error'], '', ''
try:
    args = params if isinstance(params, dict) else dict()
except Exception:
    args = dict()
try:
    today = datetime.datetime.strptime(str(vars.get(CFG.get('now_var', 'now')))[:10], '%Y-%m-%d').date()
    prods = load_products()
    pid = str(args.get('product_id') or '').strip()
    prod = None
    for p in prods:
        if str(p.get(CFG['product_id_field'])) == pid:
            prod = p
    if prod is None and len(prods) == 1:
        prod = prods[0]
        pid = str(prod.get(CFG['product_id_field']))
    if prod is None:
        raise ValueError('unknown product')
    late = int(float(prod.get(CFG['days_late_field'])))
    band = [b for b in CFG['bands'] if b['min'] <= late <= b['max']]
    if not band:
        raise ValueError('no band')
    deadline = add_bd(today, int(band[0]['deadline_business_days']))
    raw = str(args.get('date') or '').strip().lower()
    day = None
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
        day = datetime.date.fromisoformat(raw)
    key = 'date_vague_count_' + re.sub(r'\W', '_', pid)
    if day is None:
        n = int(vars.get(key) or 0) + 1
        vars[key] = str(n)
        if n <= int(CFG.get('vague_asks_before_deadline', 1)):
            decision, say = 'ask_exact', CFG['say']['ask_exact']
        else:
            decision, proposed = 'propose_deadline', deadline.isoformat()
            say = CFG['say']['vague_propose_deadline'].format(deadline=spoken(deadline))
    elif day < today:
        decision, say = 'past', CFG['say']['past'].format(day=spoken(day))
    elif day > deadline:
        decision, proposed = 'after_deadline', deadline.isoformat()
        say = CFG['say']['after_deadline'].format(day=spoken(day), deadline=spoken(deadline))
    elif not isbd(day):
        nb = next_bd(day)
        decision, proposed = 'not_business_day', nb.isoformat()
        say = CFG['say']['not_business_day'].format(day=spoken(day), next=spoken(nb), deadline=spoken(deadline))
    else:
        decision, proposed = 'ok', day.isoformat()
        say = CFG['say']['ok'].format(day=spoken(day), deadline=spoken(deadline))
except Exception as e:
    vars['date_error'] = str(e)[:120]
vars['date_decision'] = decision
vars['date_say'] = say
vars['date_proposed'] = proposed
vars['date_product'] = pid
vars['date_flag'] = 'new'
'''


# The decision sentence is code-made; the model must repeat it unchanged. It may first answer a question the customer
# asked in the same message (a fixed tts line dropped such questions: PUB-04, run fb-a-v3-f1).
RELAY_PROMPT = ("First, if the customer's last message asked you a question or said something your instructions require you to "
                "respond to, answer it in one short sentence. Then say this decision exactly, word for word, without changing any "
                "day, date or amount: \"{{date_say}}\" Do not call any tool. Say nothing else about which days are possible.")


def build_code(cfg):
    cfg_json = json.dumps(cfg, indent=1)
    code = CODE_TEMPLATE.replace("__CFG__", cfg_json)
    if "{{" in code or "}}" in code or '"""' in cfg_json:
        raise ValueError("generated code would contain '{{', '}}' or triple quotes; adjust the config text")
    return code


def generate(cfg, negotiation_node):
    code = build_code(cfg)
    tool = {"type": "function", "config": {"timeoutMs": 10000, "preSpeech": {"mode": "static", "message": cfg["say"]["checking"], "interruptible": False}},
            "function": {"name": "check_payment_date", "handler": "__function__:code_exec",
                         "description": "CALL it every time the customer names a payment day or a period, before you say anything about that day. "
                                        "date = the day as YYYY-MM-DD read from the calendar in your instructions, or 'vague' when the customer gave no exact day. "
                                        "product_id = the product the date is for. The decision is read out after the call; do not judge the day yourself.",
                         "parameters": {"type": "object", "properties": {
                             "code": {"type": "string", "default": code},
                             "timeout_ms": {"type": "number", "default": 5000},
                             "date": {"type": "string", "description": "YYYY-MM-DD, or 'vague'"},
                             "product_id": {"type": "string", "description": "product id from the account result"}},
                             "required": ["date", "product_id"]}}}
    nodes = {
        "date_consume": {"name": "date_consume", "node_type": "code", "passthrough": True, "passthrough_default_transition": "date_relay",
                         "on_enter": {"type": "silent"},
                         "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {
                             "code": {"type": "string", "default": "vars['date_flag'] = 'used'\n"}, "timeout_ms": {"type": "number", "default": 5000}}}}}],
                         "transitions": [{"target_node": "date_relay", "description": "always", "condition": {"operator": "always"}}]},
        "date_relay": {"name": "date_relay", "node_type": "conversation",
                       "on_enter": {"type": "llm", "prompt": RELAY_PROMPT},
                       "task_message": RELAY_PROMPT, "max_node_turns": 5, "max_turn_transition": negotiation_node,
                       "transitions": [{"target_node": negotiation_node, "description": "always", "condition": {"operator": "always"}}]}}
    transition = {"target_node": "date_consume", "description": "the date check produced a new decision",
                  "condition": {"logic": "or", "conditions": [{"variable": "date_flag", "operator": "equals", "operand": "new"}]}}
    instructions = (f"Add `tool` to node {negotiation_node}'s tools. Put `transition` FIRST in {negotiation_node}'s transitions. "
                    "Add `nodes` to the workflow. In the negotiation prompt: call check_payment_date for every day or period the customer names; "
                    "never say yourself whether a day is allowed; after the decision is read out, continue from it. "
                    "The last decision is in {{date_decision}} (ok, not_business_day, after_deadline, past, ask_exact, propose_deadline, error) "
                    "and the date to use is {{date_proposed}}.")
    return {"tool": tool, "nodes": nodes, "transition": transition, "instructions": instructions}


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    print(json.dumps(generate(cfg, sys.argv[2]), indent=1))

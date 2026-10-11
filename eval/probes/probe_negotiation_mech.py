"""G1b probe: (a) array argument to a code_exec tool, (b) passthrough conversation node with a tts line,
(c) engine-run create_promise with baked values and a pre-hook that casts the amount. Fake customer id; no simulation."""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "builder"))
import common, toolspec

ts = toolspec.load(str(common.KIT / "tools/openapi.json"))
EV_CODE = """import json
try:
    ev = params.get('events') if isinstance(params, dict) else None
    vars['probe_events_type'] = type(ev).__name__
    vars['probe_events'] = json.dumps(ev)[:300]
    vars['rec_product'] = 'p1'
    vars['rec_amount'] = '365.5'
    vars['rec_date'] = '2026-10-16'
    vars['ev_flag'] = 'new'
except Exception as e:
    vars['probe_events'] = 'ERR ' + str(e)[:100]
    vars['ev_flag'] = 'new'
"""
tool = {"type": "function", "config": {"timeoutMs": 10000, "preSpeech": {"mode": "static", "message": "One moment.", "interruptible": False}},
        "function": {"name": "negotiation_event", "handler": "__function__:code_exec",
                     "description": "CALL it for every customer message about paying. events = one item per product and kind of statement.",
                     "parameters": {"type": "object", "properties": {
                         "code": {"type": "string", "default": EV_CODE}, "timeout_ms": {"type": "number", "default": 5000},
                         "events": {"type": "array", "description": "One item per statement.", "items": {"type": "object", "properties": {
                             "product_id": {"type": "string", "description": "p1, p2 ... or all"},
                             "type": {"type": "string", "enum": ["proposes", "refuses", "accepts"]},
                             "date": {"type": "string", "description": "YYYY-MM-DD or empty"},
                             "amount": {"type": "string", "description": "number or empty"}}, "required": ["product_id", "type"]}}},
                         "required": ["events"]}}}
PRE = "try:\n    b = config.get('body')\n    if isinstance(b, dict):\n        b['amount'] = float(vars.get('rec_amount'))\n        vars['probe_pre_ran'] = 'yes'\nexcept Exception as e:\n    vars['probe_pre_ran'] = 'ERR ' + str(e)[:80]\n"
POST = "try:\n    vars['probe_post_ran'] = 'yes'\n    if isinstance(result, dict):\n        result.pop('header', None)\nexcept Exception:\n    pass\n"
rec = {"type": "function", "config": {"timeoutMs": 12000, "maxRetries": 0}, "pre_process_code": PRE, "post_process_code": POST,
       "function": {"name": "create_promise", "handler": "__function__:api_call", "description": "record",
                    "parameters": {"type": "object", "properties": {
                        "url": {"type": "string", "default": ts["ops"]["create_promise"]["url"]}, "method": {"type": "string", "default": "POST"},
                        "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                        "body": {"type": "object", "properties": {"customer_id": {"type": "string", "default": "{{customer_id}}"},
                                                                  "product_id": {"type": "string", "default": "{{rec_product}}"},
                                                                  "amount": {"type": "number", "default": "{{rec_amount}}"},
                                                                  "date": {"type": "string", "default": "{{rec_date}}"}}, "required": []}}}}}


def code(name, c, nxt):
    return {"name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": nxt, "on_enter": {"type": "silent"},
            "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {
                "code": {"type": "string", "default": c}, "timeout_ms": {"type": "number", "default": 5000}}}}}],
            "transitions": [{"target_node": nxt, "description": "always", "condition": {"operator": "always"}}]}


wf = {"initial_node": "talk", "system_prompt": "Test assistant. English. One short sentence.", "global_nodes": {}, "test_variables": {"now": "2026-10-14T11:00"},
      "nodes": {
          "talk": {"name": "talk", "node_type": "conversation", "on_enter_first_entry_only": True, "on_enter": {"type": "tts", "text": "Hello. When can you pay each product?"},
                   "task_message": "When the user says anything about paying, CALL negotiation_event with one item per product and statement. Product ids are p1 and p2.",
                   "tools": [tool], "max_node_turns": 20, "max_turn_transition": "talk",
                   "transitions": [{"target_node": "consume", "description": "new", "condition": {"logic": "or", "conditions": [{"variable": "ev_flag", "operator": "equals", "operand": "new"}]}},
                                   {"target_node": "talk", "description": "stay", "condition": {"operator": "always"}}]},
          "consume": code("consume", "vars['ev_flag'] = 'used'\n", "say_pass"),
          "say_pass": {"name": "say_pass", "node_type": "conversation", "passthrough": True, "passthrough_default_transition": "record_one",
                       "on_enter": {"type": "tts", "text": "Recording now."}, "task_message": "Do not call any tool.",
                       "transitions": [{"target_node": "record_one", "description": "always", "condition": {"operator": "always"}}]},
          "record_one": {"name": "record_one", "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "after", "on_enter": {"type": "silent"},
                         "pre_actions": [rec], "transitions": [{"target_node": "after", "description": "always", "condition": {"operator": "always"}}]},
          "after": {"name": "after", "node_type": "conversation", "on_enter": {"type": "tts", "text": "Done. Events were {{probe_events_type}}."}, "task_message": "Do not call any tool.",
                    "transitions": [{"target_node": "after", "description": "stay", "condition": {"operator": "always"}}]}}}


class T:
    def log(self, k, m):
        print(f"[{k}] {m}")


pub = common.publish("probe-neg-mech", wf, T())
cv = {"customer_id": "c_probe_neg", "now": "2026-10-14T11:00"}
r1 = common.freya.api("POST", "/api/v2/chat/message", {"workflowId": pub["workflow_id"], "message": "Hi", "customerVariables": cv})
r2 = common.freya.api("POST", "/api/v2/chat/message", {"workflowId": pub["workflow_id"], "callId": r1["callId"],
                                                        "message": "I will pay the card on Friday the 16th, but I refuse to pay the loan.", "customerVariables": cv})
print("TURN2 reply:", r2.get("response"))
call = common.freya.get_call(r1["callId"])
vt = {}
for m in call["messages"]:
    role, msg = m.get("role"), m.get("message") or ""
    if role in ("assistant", "user"):
        print(f"  {role}: {msg[:160]}")
    elif role == "system":
        try:
            ev = json.loads(msg)
        except Exception:
            continue
        e = ev.get("event")
        if e == "node_enter":
            print("  [node]", ev.get("node"))
        if e == "function_call_start" and ev.get("function") != "code_exec":
            a = ev.get("args") or {}
            print("  [call]", ev.get("function"), json.dumps(a.get("body", a.get("params", a)))[:300])
        if e in ("function_call_complete", "function_call_error") and ev.get("function") != "code_exec":
            print("  [", e, "]", json.dumps(ev.get("result") or ev.get("error"))[:200])
        if e == "route_evaluated" and ev.get("variable_table"):
            vt = ev["variable_table"]
for k in sorted(x for x in vt if "record_one" in x or "create_promise" in x or x.startswith("probe_")):
    v = vt.get(k)
    print("  var", k, "=", (v.get("value") if isinstance(v, dict) else v))
try:
    common.freya.api("POST", "/api/v2/chat/end", {"callId": r1["callId"]})
except Exception:
    pass

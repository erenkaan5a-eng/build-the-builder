"""G1 probe: can the model call a code_exec tool with an argument, the code decide, and a fixed line relay the decision?
No bank calls. Uses the chat API on a probe slot."""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "builder"))
import common

CODE = """
try:
    cand = None
    for k in ('date', 'check_date_args.date', 'params', 'check_date_args.params'):
        v = vars.get(k)
        if v:
            cand = str(v)
            break
    try:
        cand = cand or str(params)
    except Exception:
        pass
    vars['probe_keys'] = ','.join(sorted(k for k in vars.keys() if 'date' in k.lower()))[:400]
    vars['date_say'] = 'CODE DECISION for ' + str(cand)
    vars['date_flag'] = 'new'
except Exception as e:
    vars['date_say'] = 'CODE ERROR ' + str(e)[:80]
    vars['date_flag'] = 'new'
"""
tool = {"type": "function", "config": {"timeoutMs": 10000, "preSpeech": {"mode": "static", "message": "One moment, let me check that date.", "interruptible": False}},
        "function": {"name": "check_date", "handler": "__function__:code_exec",
                     "description": "CALL it every time the user names a payment day or period. date = that day as YYYY-MM-DD, or 'vague' if no exact day.",
                     "parameters": {"type": "object", "properties": {
                         "code": {"type": "string", "default": CODE},
                         "timeout_ms": {"type": "number", "default": 5000},
                         "date": {"type": "string", "description": "The day the user named as YYYY-MM-DD, or 'vague'."}},
                         "required": ["date"]}}}
wf = {"initial_node": "talk", "system_prompt": "You are a test assistant. Speak English. One short sentence per turn.",
      "nodes": {
        "talk": {"name": "talk", "node_type": "conversation", "on_enter": {"type": "tts", "text": "Hello. Which day can you pay?"},
                 "on_enter_first_entry_only": True,
                 "task_message": "Today is {{now}}. When the user names a day or a period, CALL check_date once. Do not judge the day yourself; the tool decides and its decision is read out after it. Otherwise answer briefly.",
                 "tools": [tool], "max_node_turns": 30, "max_turn_transition": "talk",
                 "transitions": [
                     {"target_node": "consume", "description": "a new decision exists", "condition": {"logic": "or", "conditions": [{"variable": "date_flag", "operator": "equals", "operand": "new"}]}},
                     {"target_node": "talk", "description": "stay", "condition": {"operator": "always"}}]},
        "consume": {"name": "consume", "node_type": "code", "passthrough": True, "passthrough_default_transition": "relay", "on_enter": {"type": "silent"},
                    "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {
                        "code": {"type": "string", "default": "vars['date_flag'] = 'used'\n"}, "timeout_ms": {"type": "number", "default": 5000}}}}}],
                    "transitions": [{"target_node": "relay", "description": "always", "condition": {"operator": "always"}}]},
        "relay": {"name": "relay", "node_type": "conversation", "on_enter": {"type": "tts", "text": "{{date_say}}"},
                  "task_message": "Do not call any tool in this turn. Answer briefly.", "max_node_turns": 30, "max_turn_transition": "talk",
                  "transitions": [{"target_node": "talk", "description": "always", "condition": {"operator": "always"}}]}},
      "global_nodes": {}, "test_variables": {"now": "2026-10-14T11:00"}}

class T:  # minimal trace stand-in
    def log(self, k, m): print(f"[{k}] {m}")
t = T()
pub = common.publish("probe-code-tool", wf, t)
cv = {"customer_id": "c_probe", "now": "2026-10-14T11:00"}
r1 = common.freya.api("POST", "/api/v2/chat/message", {"workflowId": pub["workflow_id"], "message": "Hello?", "customerVariables": cv})
print("TURN1:", r1.get("response"))
r2 = common.freya.api("POST", "/api/v2/chat/message", {"workflowId": pub["workflow_id"], "callId": r1["callId"], "message": "I can pay on Monday the 26th of October.", "customerVariables": cv})
print("TURN2:", r2.get("response"))
call = common.freya.get_call(r1["callId"])
for m in call.get("messages", []):
    role, msg = m.get("role"), m.get("message") or ""
    if role in ("assistant", "user"):
        print(f"  {role}: {msg[:200]}")
    elif role == "system":
        try: ev = json.loads(msg)
        except Exception: continue
        e = ev.get("event")
        if e in ("node_enter", "function_call_start", "function_call_complete", "function_call_error", "error"):
            print(f"  [{e}] {json.dumps({k: ev.get(k) for k in ('node','from_node','function','args','result','message') if ev.get(k) is not None})[:400]}")
        if e == "route_evaluated":
            vt = ev.get("variable_table") or {}
            keys = {k: (v.get('value') if isinstance(v, dict) else v) for k, v in vt.items() if any(x in k for x in ('date', 'flag', 'param', 'check'))}
            print(f"  [route matched={ev.get('matched')}] {ev.get('from_node')}->{ev.get('target')} reason={str(ev.get('reason'))[:200]} branches={json.dumps(ev.get('branches'))[:700]}")
try:
    common.freya.api("POST", "/api/v2/chat/end", {"callId": r1["callId"]})
except Exception:
    pass

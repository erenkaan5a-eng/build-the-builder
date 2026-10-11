"""builder/behavior.py must see the bank calls the workflow engine runs itself (api_request pre_actions).

Freya reports those calls under the handler name 'api_call' with the request URL in args (real call events in
tests/fixtures/chat-events-engine-run.json, captured 11 Oct). Before this check existed, behavior.py looked only at the
function name: an engine-run verify_identity was "no verify call" (false FAIL, loc-a recheck 15:33) and an engine-run
get_account/create_promise before verification was invisible (the guard check passed vacuously).
No model or Freya call here."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
sys.path.insert(0, str(ROOT / "tests"))
import behavior  # noqa: E402
from negotiation_harness import check, FAILS  # noqa: E402

MSGS = json.load(open(ROOT / "tests" / "fixtures" / "chat-events-engine-run.json", encoding="utf-8"))["messages"]
ev = behavior.parse_events(MSGS)
calls = [e[1] for e in ev if e[0] == "call" and e[1] not in ("code_exec", "negotiation_event", "end_call")]
check("E1 real call events: engine-run calls are named by their operation, in order",
      calls == ["verify_identity", "verify_identity", "get_account", "create_promise", "create_promise", "close_call"], calls)
check("E2 no bank call is left under the handler name 'api_call'", not [e for e in ev if e[0] in ("call", "result", "error") and e[1] == "api_call"],
      [e[:2] for e in ev if e[1:2] == ("api_call",)])
res = [(e[1], (e[2] or {}).get("data", {}).get("ok") if isinstance(e[2], dict) else None) for e in ev if e[0] == "result" and e[1] in ("get_account", "create_promise", "close_call")]
check("E3 each engine-run result is paired with its own operation", res == [("get_account", True), ("create_promise", True), ("create_promise", True), ("close_call", True)], res)
cp = [e[2] for e in ev if e[0] == "call" and e[1] == "create_promise"]
check("E4 the request body of an engine-run write is kept (product, amount, date)",
      [(b.get("product_id"), b.get("amount"), b.get("date")) for b in cp] == [("p1", 300.0, "2026-10-30"), ("p2", 900.0, "2026-10-23")], cp)


# the structural release check on synthetic events built the same way the platform reports engine-run calls
class _T:
    def log(self, kind, msg):
        pass


def sys_msg(d):
    return {"role": "system", "message": json.dumps(d)}


def start(op, body):
    return sys_msg({"event": "function_call_start", "function": "api_call",
                    "args": {"url": "https://bank.example/v1/" + op, "method": "POST", "body": body}})


POL = json.load(open(ROOT / "tests" / "fixtures" / "policy-a.json", encoding="utf-8"))
F = POL["identity"]["questions"][0]["field"]
FP, AP = POL["api_binding"]["verify"]["field_param"], POL["api_binding"]["verify"]["answer_param"]


def structural_on(messages):
    real = behavior.chat
    behavior.chat = lambda wid, tv, turns: ("c_test", ["Hello, I am a digital assistant.", "q", "q"], behavior.parse_events(messages))
    try:
        return dict((n, ok) for n, ok, _ in behavior.structural("wf_test", POL, _T()))
    finally:
        behavior.chat = real


base = [{"role": "assistant", "message": "Hello"}, sys_msg({"event": "node_enter", "node": "identity"}), sys_msg({"event": "node_enter", "node": "id_verify"})]
good = structural_on(base + [start("verify_identity", {FP: F, AP: "1988-03-14", "customer_id": "c"})])
check("E5 an engine-run verify_identity with the right field passes 'first security answer reaches verify_identity'",
      good["first security answer reaches verify_identity with the right field"], good)
bad = structural_on(base + [start("verify_identity", {FP: F, AP: "1988-03-14", "customer_id": "c"}), start("get_account", {"customer_id": "c"})])
check("E6 an engine-run get_account without a full verification is caught by 'no account or write call before verification'",
      bad["no account or write call before verification"] is False, bad)
wrong = structural_on(base + [start("verify_identity", {FP: "phone_last4", AP: "1988-03-14", "customer_id": "c"})])
check("E7 a verify call with the wrong field still fails the check", wrong["first security answer reaches verify_identity with the right field"] is False, wrong)
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

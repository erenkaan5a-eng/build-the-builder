"""Scripted chat probe of a PUBLISHED agent against a public practice customer (development only).

    FREYA_AUTH_VIA_PROXY=1 python3 eval/chat_probe.py <slot> <case_id> <name> "<msg 1>" "<msg 2>" ...

The customer's messages are fixed in advance (no simulated persona), so a reply the script did not expect makes the
rest of the script meaningless: read the saved transcript before drawing a conclusion. The two security answers of
the case can be written as {ID1} and {ID2}. Saves replies, node path, tool calls/results and the bank ledger of the
practice session to research/cloud-runs/chat-<name>.json. Chat and ledger are evidence of this one run only.
"""
import json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
sys.path.insert(0, str(ROOT / "tools"))
import common, behavior  # noqa: E402
from score import http  # noqa: E402  (patched by cloud proxy mode when FREYA_AUTH_VIA_PROXY=1)


def main():
    slot, case_id, name, msgs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
    st = json.load(open(ROOT / ".freya-agents.json"))[slot]
    case = [c for c in json.load(open(ROOT / "public-test-set.json")) if c["id"] == case_id][0]
    ids = [str(v) for v in case["identity"].values()]
    msgs = [m.replace("{ID1}", ids[0]).replace("{ID2}", ids[1] if len(ids) > 1 else "") for m in msgs]
    live = common.wf_hash(common.get_workflow(st["workflow_id"]))
    pv = common.published_version(st["workflow_id"])
    sess = http("/v1/practice/sessions", {"case": case_id})["variables"]
    t0 = time.time()
    call_id, replies, error = None, [], None
    for m in msgs:                      # stop at the first platform error: a turn is never re-sent blindly
        body = {"workflowId": st["workflow_id"], "message": m, "customerVariables": sess}
        if call_id:
            body["callId"] = call_id
        try:
            r = common.freya.api("POST", "/api/v2/chat/message", body)
        except RuntimeError as e:
            error = f"turn {len(replies) + 1} ({m!r}): {str(e)[:200]}"
            break
        call_id = r.get("callId") or call_id
        replies.append(r.get("response") or "")
    ev = []
    if call_id:
        try:
            for mm in common.freya.get_call(call_id).get("messages", []):
                if mm.get("role") in ("assistant", "user"):
                    ev.append(("assistant" if mm["role"] == "assistant" else "user", mm.get("message") or ""))
                elif mm.get("role") == "system":
                    try:
                        x = json.loads(mm.get("message") or "")
                    except Exception:
                        continue
                    if x.get("event") == "node_enter":
                        ev.append(("node", x.get("node")))
                    elif x.get("event") == "function_call_start":
                        a = x.get("args") or {}
                        ev.append(("call", x.get("function"), a.get("body", a)))
                    elif x.get("event") in ("function_call_complete", "function_call_error"):
                        ev.append(("result" if x["event"].endswith("complete") else "error", x.get("function"), x.get("result")))
        finally:
            try:
                common.freya.api("POST", "/api/v2/chat/end", {"callId": call_id})
            except Exception:
                pass
    led = http("/v1/practice/ledger/" + sess["customer_id"])
    out = {"slot": slot, "workflow_id": st["workflow_id"], "published_version": pv["version_number"], "live_hash": live, "case": case_id,
           "name": name, "call_id": call_id, "platform_error": error, "seconds": round(time.time() - t0), "turns": [[m, r] for m, r in zip(msgs, replies)],
           "events": ev, "ledger": {k: led.get(k) for k in ("outcome", "reason", "promises", "notes", "callbacks", "transfers")},
           "ledger_tools": [c["tool"] for c in led.get("calls", [])]}
    p = ROOT / "research" / "cloud-runs" / f"chat-{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for m, r in out["turns"]:
        print("CUSTOMER:", m, "\n   AGENT:", r)
    print("nodes:", " > ".join(e[1] for e in ev if e[0] == "node"))
    print("ledger:", json.dumps(out["ledger"]), "| tools:", " > ".join(out["ledger_tools"]))
    if error:
        print("PLATFORM ERROR at", error)
    print("saved", p, "| version", pv["version_number"], "hash", live)


if __name__ == "__main__":
    main()

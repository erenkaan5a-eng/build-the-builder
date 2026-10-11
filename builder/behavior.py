"""Behaviour checks of a PUBLISHED workflow through the chat API (sequential turns, no simulation).

- structural(): needs no bank data (works in the final): opening, identity stage entered after confirmation, the first
  security answer reaches the identity tool, no account/write tool before verification.
- practice(): development only: a public practice session (real bank data) driven from identity to the account facts.
"""
import json, re, sys, pathlib

import common

ROOT = common.KIT


def chat(workflow_id, variables, turns):
    call_id, replies = None, []
    for msg in turns:
        body = {"workflowId": workflow_id, "message": msg, "customerVariables": variables}
        if call_id:
            body["callId"] = call_id
        r = common.freya.api("POST", "/api/v2/chat/message", body)
        call_id = r.get("callId") or call_id
        replies.append(r.get("response") or "")
    events = []
    try:
        call = common.freya.get_call(call_id)
        for m in call.get("messages", []):
            if m.get("role") in ("assistant", "user"):
                events.append((m["role"], m.get("message") or ""))
            elif m.get("role") == "system":
                try:
                    ev = json.loads(m.get("message") or "")
                except Exception:
                    continue
                if ev.get("event") == "node_enter":
                    events.append(("node", ev.get("node")))
                elif ev.get("event") == "function_call_start":
                    a = ev.get("args") or {}
                    events.append(("call", ev.get("function"), a.get("body", a)))
                elif ev.get("event") in ("function_call_complete", "function_call_error"):
                    events.append(("result" if ev["event"].endswith("complete") else "error", ev.get("function"), ev.get("result")))
    finally:
        try:
            common.freya.api("POST", "/api/v2/chat/end", {"callId": call_id})
        except Exception:
            pass
    return call_id, replies, events


def sample_answer(field):
    f = field.lower()
    if "date" in f or "birth" in f and "year" not in f:
        return "the fourteenth of March, nineteen eighty-eight"
    if "year" in f:
        return "nineteen eighty-eight"
    if "phone" in f or "last4" in f or "digits" in f:
        return "four four seven one"
    if "post" in f or "zip" in f:
        return "S W one A, one A A"
    return "one two three four"


def calls_of(events, fn):
    return [e for e in events if e[0] == "call" and e[1] == fn]


def structural(workflow_id, pol, trace):
    """Checks that need no bank data. Returns list of (name, ok, detail)."""
    tv = dict(pol.get("test_variables") or {})
    tv[pol["call_variables"]["customer_id"]] = "c_behaviour_check"
    q = pol["identity"]["questions"][0]
    cid, replies, ev = chat(workflow_id, tv, ["Hello?", "Yes, that's me.", sample_answer(q["field"])])
    res = []
    res.append(("opening line spoken", bool(replies and replies[0].strip()), replies[0][:120] if replies else ""))
    nodes = [e[1] for e in ev if e[0] == "node"]
    res.append(("identity stage entered after confirmation", "identity" in nodes, " > ".join(nodes)[:200]))
    vcalls = calls_of(ev, "verify_identity")
    fp, ap = pol["api_binding"]["verify"]["field_param"], pol["api_binding"]["verify"]["answer_param"]
    okv = bool(vcalls) and str(vcalls[0][2].get(fp)) == q["field"] and str(vcalls[0][2].get(ap) or "").strip() != ""
    res.append(("first security answer reaches verify_identity with the right field", okv, json.dumps(vcalls[0][2])[:200] if vcalls else "no verify call"))
    early = [e[1] for e in ev if e[0] == "call" and e[1] in ("get_account", "create_promise", "add_note")]
    res.append(("no account or write call before verification", not early, ",".join(early)))
    for name, ok, det in res:
        trace.log("TEST", f"behaviour[{'PASS' if ok else 'FAIL'}] {name} :: {det} (chat {cid})")
    return res


def practice(workflow_id, case_id, trace):
    """Dev only: public practice customer -> verify both answers -> account facts reach the negotiation stage."""
    sys.path.insert(0, str(ROOT / "tools"))
    from score import http
    case = [c for c in json.load(open(ROOT / "public-test-set.json")) if c["id"] == case_id][0]
    sess = http("/v1/practice/sessions", {"case": case_id})["variables"]
    ident = case["identity"]
    answers = [f"{ident[k]}" for k in ident]
    cid, replies, ev = chat(workflow_id, sess, ["Hello?", "Yes, that's me."] + answers + ["Okay."])
    nodes = [e[1] for e in ev if e[0] == "node"]
    v = calls_of(ev, "verify_identity")
    acct_idx = [i for i, e in enumerate(ev) if e[0] == "node" and e[1] == "fetch_account"]
    neg = "negotiate" in nodes
    dues = ["%.2f" % p["past_due"] for p in case["products"]]
    after = ev[acct_idx[0]:] if acct_idx else []
    first_stmt = next((e[1] for e in after if e[0] == "assistant" and any(d in e[1].replace(",", "") for d in dues)), "")
    all_stated = bool(first_stmt) and all(d in first_stmt.replace(",", "") for d in dues)
    res = [("both answers sent to verify_identity", len(v) >= len(answers), f"{len(v)} verify calls"),
           ("account fetched after verification", bool(acct_idx), " > ".join(nodes)[:240]),
           ("negotiation stage reached with account facts", neg, ""),
           ("every product's past-due amount stated in the debt statement, before any offer", all_stated, first_stmt[:220])]
    for name, ok, det in res:
        trace.log("TEST", f"practice[{case_id}][{'PASS' if ok else 'FAIL'}] {name} :: {det} (chat {cid})")
    return res, ev

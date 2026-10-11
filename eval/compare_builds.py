"""Compare two candidate folders built from the same builder version and the same inputs.

    python eval/compare_builds.py candidates/<slot1>/<time> candidates/<slot2>/<time>
Prints decision differences (policy values that change behaviour) and structural workflow differences.
Prompt wording differences are counted, not treated as decision differences.
"""
import json, sys


def load(d):
    return json.load(open(d + "/policy.json", encoding="utf-8")), json.load(open(d + "/workflow.json", encoding="utf-8"))


DECISION_KEYS = ["call_variables", "calendar", "callback", "bands", "products", "write_retries", "after_promise_sentence", "statuses",
                 "uses_notes", "vague_asks_before_deadline", "api_binding", "goodbye_line"]


def decisions(p):
    d = {k: p.get(k) for k in DECISION_KEYS}
    d["identity_fields"] = [q["field"] for q in p["identity"]["questions"]]
    d["identity_hints"] = sorted((p["identity"].get("hints") or {}).keys())
    d["ladder"] = p["negotiation"]["ladder"]
    d["shared_date_clamps"] = p["negotiation"].get("shared_date_clamps_to_deadline")
    d["closing"] = {k: v for k, v in p["closing"].items()}
    d["confirm_question"] = p["negotiation"]["say"].get("confirm_question")
    d["first_ask"] = [p["negotiation"]["say"].get("first_ask_one"), p["negotiation"]["say"].get("first_ask_all")]
    d["extra_rules_kinds"] = sorted(r.get("kind") for r in p.get("extra_rules") or [])
    return d


def structure(w):
    s = {}
    for k, n in w["nodes"].items():
        tools = [(t["function"]["name"], json.dumps({x: y for x, y in (t.get("config") or {}).items() if x != "preSpeech"}, sort_keys=True))
                 for t in (n.get("tools") or []) + (n.get("pre_actions") or [])]
        trans = [(t["target_node"], json.dumps(t.get("condition"), sort_keys=True)) for t in n.get("transitions") or []]
        s[k] = {"type": n.get("node_type"), "first_only": n.get("on_enter_first_entry_only"), "on_enter": (n.get("on_enter") or {}).get("type"),
                "passthrough": n.get("passthrough"), "tools": tools, "transitions": trans,
                "extraction": [e["name"] for e in n.get("extraction_schema") or []]}
    return s


a, b = sys.argv[1], sys.argv[2]
pa, wa = load(a)
pb, wb = load(b)
da, db = decisions(pa), decisions(pb)
diff = [k for k in da if da[k] != db[k]]
print("DECISION differences:", len(diff))
for k in diff:
    print(f"  {k}:\n    A: {json.dumps(da[k])[:400]}\n    B: {json.dumps(db[k])[:400]}")
sa, sb = structure(wa), structure(wb)
nodes = sorted(set(sa) | set(sb))
sdiff = [k for k in nodes if sa.get(k) != sb.get(k)]
print("STRUCTURE differences (nodes, tools/config, transitions, entry flags):", len(sdiff))
for k in sdiff:
    x, y = sa.get(k), sb.get(k)
    if x is None or y is None:
        print(f"  node {k} only in {'B' if x is None else 'A'}")
        continue
    for f in x:
        if x[f] != y[f]:
            print(f"  node {k}.{f}:\n    A: {json.dumps(x[f])[:300]}\n    B: {json.dumps(y[f])[:300]}")
text_a = json.dumps({k: (n.get("task_message"), n.get("on_enter")) for k, n in wa["nodes"].items()}) + wa.get("system_prompt", "")
text_b = json.dumps({k: (n.get("task_message"), n.get("on_enter")) for k, n in wb["nodes"].items()}) + wb.get("system_prompt", "")
print("prompt text identical:", text_a == text_b, "| rules per stage A/B:",
      {k: (len(pa["rules"].get(k) or []), len(pb["rules"].get(k) or [])) for k in set(pa["rules"]) | set(pb["rules"])})

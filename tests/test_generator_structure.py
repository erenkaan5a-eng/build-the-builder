"""Generate workflows from the stored policies of the last measured candidates (no model or Freya call) and check the
lint and the routing contracts the runtime relies on."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
sys.path.insert(0, str(ROOT / "tests"))
import toolspec, components, lint
from negotiation_harness import check, FAILS

ts = toolspec.load(str(ROOT / "tools" / "openapi.json"))
for label, cand in (("A", "candidates/cmp-a/20261011-024419"), ("A+B", "candidates/cmp-ab/20261011-024603")):
    pol = json.load(open(ROOT / cand / "policy.json", encoding="utf-8"))
    wf = components.build(pol, ts)
    errs = [p for p in lint.lint(wf, str(ROOT / "tools" / "openapi.json")) if not p.startswith("warn:")]
    check(f"{label}: lint has no errors", not errs, errs)
    N = wf["nodes"]
    tr = lambda k: [t["target_node"] for t in N[k]["transitions"]]
    check(f"{label}: a mentioned hardship is routed to code before the model speaks (negotiate, neg_relay)",
          tr("negotiate")[0] == "hardship_go" and tr("neg_relay")[0] == "hardship_go" and tr("hardship_go") == ["neg_relay"], (tr("negotiate"), tr("neg_relay")))
    check(f"{label}: recording without a confirmed package goes back to the negotiation", "negotiate" in tr("rec_next") and "record_one" in tr("rec_next"), tr("rec_next"))
    check(f"{label}: unresolved products send FINISH back to the negotiation", tr("finish_prep") == ["negotiate", "finish_say"], tr("finish_prep"))
    chain = ["finish_say", "notes_next", "close_one", "close_check", "hangup"]
    check(f"{label}: goodbye -> notes -> one close_call -> close result -> hang up",
          tr("finish_say") == ["notes_next"] and tr("notes_next")[-1] == "close_one" and tr("close_one") == ["close_check"] and tr("close_check") == ["hangup"], [tr(k) for k in chain[:-1]])
    writes = {k: [(t["function"]["name"], (t.get("config") or {}).get("maxRetries")) for t in N[k].get("pre_actions") or []] for k in ("record_one", "close_one") + (("note_one",) if "note_one" in N else ())}
    check(f"{label}: engine-run writes carry no platform retry (single retry layer in code; none invented for notes/close)",
          all(r == 0 for v in writes.values() for _, r in v), writes)
    neg_tools = [t["function"]["name"] for t in N["negotiate"]["tools"]]
    check(f"{label}: the dialogue model cannot write promises, notes or the close in the negotiation", "create_promise" not in neg_tools and "add_note" not in neg_tools and "close_call" not in neg_tools, neg_tools)
    deal = N["build_deal"]["pre_actions"][0]["function"]["parameters"]["properties"]["code"]["default"]
    check(f"{label}: the account step initialises hardship_done='no' (the routing condition needs a value)", "vars['hardship_done'] = 'no'" in deal)
    hr = N["negotiate"]["transitions"][0]["condition"]["conditions"]
    check(f"{label}: the hardship route is skipped when the same message names a date or an amount (A32: the proposal reaches the code)",
          all({"variable": "offer_named", "operator": "not_equals", "operand": "yes"} in g["conditions"] for g in hr) and {c["variable"] for g in hr for c in g["conditions"]} >= {"hardship_seen", "hardship_early"}
          and N["neg_relay"]["transitions"][0] == N["negotiate"]["transitions"][0], hr)
    xs = lambda k: [x["name"] for x in N[k].get("extraction_schema") or []]
    check(f"{label}: a hardship said at the identity stage is extracted and kept by the account step",
          "hardship_seen" in xs("identity") and "vars['hardship_early']" in deal and "vars['offer_named'] = 'no'" in deal and "offer_named" in xs("negotiate") and "offer_named" in xs("neg_relay"),
          (xs("identity"), xs("negotiate"), xs("neg_relay")))
    idt = N["identity"]["task_message"]
    check(f"{label}: identity stage: parts of one answer are combined; a failed check only on the bank's result (style 'pieces', 11 Oct)",
          "in parts" in idt and "combined answer" in idt and "unless what_to_do_next says the identity check has failed" in idt, idt[:200])
    check(f"{label}: notes only in a brief that uses them", ("note_one" in N) == bool(pol.get("uses_notes")), ("note_one" in N, pol.get("uses_notes")))
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

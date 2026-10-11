"""Generate workflows from the stored policies of the last measured candidates (no model or Freya call) and check the
lint and the routing contracts the runtime relies on."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
sys.path.insert(0, str(ROOT / "tests"))
import toolspec, components, lint
from negotiation_harness import check, FAILS

ts = toolspec.load(str(ROOT / "tools" / "openapi.json"))
for label, cand in (("A", "tests/fixtures/policy-a.json"), ("A+B", "tests/fixtures/policy-ab.json")):
    pol = json.load(open(ROOT / cand, encoding="utf-8"))
    wf = components.build(pol, ts)
    errs = [p for p in lint.lint(wf, str(ROOT / "tools" / "openapi.json")) if not p.startswith("warn:")]
    check(f"{label}: lint has no errors", not errs, errs)
    N = wf["nodes"]
    tr = lambda k: [t["target_node"] for t in N[k]["transitions"]]
    check(f"{label}: a message cut off mid-sentence is answered first (ask to go on), then a mentioned hardship is routed to code before the model speaks",
          tr("negotiate")[:2] == ["go_on", "hardship_go"] and tr("neg_relay")[:2] == ["go_on", "hardship_go"] and tr("hardship_go") == ["neg_relay"]
          and tr("go_on") == ["neg_relay"], (tr("negotiate"), tr("neg_relay")))
    check(f"{label}: the answer to the support offer is routed by code (accept -> engine transfer, decline -> engine) before the model speaks",
          tr("neg_relay")[3:5] == ["hs_accept", "hs_decline"] and tr("hs_accept") == ["xfer_one"] and tr("hs_decline") == ["finish_prep", "neg_consume"]
          and tr("xfer_one") == ["xfer_check"] and tr("xfer_check") == ["finish_prep"], (tr("neg_relay"), tr("hs_decline")))
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
    hr = N["negotiate"]["transitions"][1]["condition"]["conditions"]
    check(f"{label}: the hardship route is skipped when the same message names a date or an amount (A32: the proposal reaches the code)",
          all({"variable": "offer_named", "operator": "not_equals", "operand": "yes"} in g["conditions"] for g in hr) and {c["variable"] for g in hr for c in g["conditions"]} >= {"hardship_seen", "hardship_early"}
          and N["neg_relay"]["transitions"][1] == N["negotiate"]["transitions"][1], hr)
    xs = lambda k: [x["name"] for x in N[k].get("extraction_schema") or []]
    check(f"{label}: a hardship said at the identity stage is extracted and kept by the account step",
          "hardship_seen" in xs("identity") and "vars['hardship_early']" in deal and "vars['offer_named'] = 'no'" in deal and "offer_named" in xs("negotiate") and "offer_named" in xs("neg_relay"),
          (xs("identity"), xs("negotiate"), xs("neg_relay")))
    check(f"{label}: identity stage is run by code (parts, bank result, close: tests/test_identity.py); the model only sends events",
          [t["function"]["name"] for t in N["identity"]["tools"]] == ["identity_event"], N["identity"]["tools"])
    check(f"{label}: notes only in a brief that uses them", ("note_one" in N) == bool(pol.get("uses_notes")), ("note_one" in N, pol.get("uses_notes")))
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

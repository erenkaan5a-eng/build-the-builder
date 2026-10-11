"""A32 hardship: the answer to the support offer is routed by code (no dialogue-model speech in that turn), the model's
free answer cannot carry an offer, and a message cut off mid-sentence is answered with a request to go on.
Expected values worked out by hand from Brief A rules 30-33 and 37-38; bank results are local imitations."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "builder" / "runtime"))
from negotiation_harness import Call, P, check, FAILS, platform_exec  # noqa: E402
import identity as ID  # noqa: E402
import negotiation as NG  # noqa: E402

# now Wed 14 Oct 2026; PUB-05: personal loan 780, floor 260, 21 days late -> late band, deadline 23 Oct, 2 attempts
LOAN = P("p1", "personal loan", 780.0, 260.0, "2026-10-23", 2)

# H1 PUB-05: hardship (code), then 'no transfer, can I get a discount?' -> the code answers the discount question with
#    the policy sentence and closes no_promise/hardship; no offer, no payment question
c = Call([LOAN], uses_notes=False)
c.run("HARDSHIP")
check("H1a the support offer is open after the code's hardship sentence (support_pending), any earlier reply cleared; a decline would end the call",
      c.v.get("support_pending") == "yes" and c.v.get("support_reply") == "consumed" and c.v.get("support_closes") == "yes",
      (c.v.get("support_pending"), c.v.get("support_reply"), c.v.get("support_closes")))
c.v["support_reply"], c.v["terms_asked"] = "declines", "yes"          # what the relay node's extraction would set
c.v["neg_relay.total_turns"] = "1"
c.run("SUPPORT_DECLINE")
check("H1b decline + discount question: the policy's 'no other terms' sentence, nothing to negotiate", c.v["neg_flag"] == "finish"
      and c.v["neg_say"].startswith("No other terms.") and "pay" not in c.v["neg_say"].lower(), (c.v["neg_flag"], c.v["neg_say"]))
o = c.finish()
check("H1c close no_promise/hardship, the goodbye after the code's sentence, no note in a brief without notes",
      o[:2] == ("no_promise", "hardship") and c.v["fin_say"].startswith("No other terms.") and c.v["fin_say"].endswith("Goodbye."), (o, c.v["fin_say"]))

# H2 hardship + own offer in one message, then the decline routed by code: the held proposal is read back and recorded
c = Call([LOAN])
c.ev(("p1", "proposes", "2026-10-16", "300"), ("p1", "hardship", "", ""))
check("H2a [own offer + hardship]: sympathy + support offer only, the offer is held, support_pending set",
      c.v["neg_say"] == "Sorry to hear. Support team?" and c.st().get("held") and c.v.get("support_pending") == "yes", (c.v["neg_say"], c.st().get("held")))
check("H2b a held proposal: the decline does NOT close the call (support_closes=no -> the relay leaves it to the engine)",
      c.v.get("support_closes") == "no", c.v.get("support_closes"))
c.ev(("p1", "declines_support", "", ""))
check("H2c the decline (engine event) leads to the read-back of the customer's own 300 on Friday 16 October",
      c.st()["phase"] == "readback" and "300.00 on Friday 16 October" in c.v["neg_say"] and c.v["neg_flag"] == "new", (c.st()["phase"], c.v["neg_say"]))
c.ev(("p1", "confirms", "", ""))
sent = c.rec(["ok"])
o = c.finish()
check("H2d confirmed -> one write of the read-back package, promise, the text-message sentence", sent == [("p1", "300.00", "2026-10-16")]
      and o[0] == "promise" and "text message" in c.v["fin_say"], (sent, o, c.v["fin_say"]))

# H3 accept: engine-run transfer to the policy's support queue, close transferred/support, no notes (B10)
c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.run("HARDSHIP")
c.v["support_reply"] = "accepts"
c.run("SUPPORT_ACCEPT")
check("H3a accept: the transfer queue is the policy's support queue", c.v.get("xfer_queue") == "support" and c.v.get("support_pending") == "no", c.v.get("xfer_queue"))
c.v["xfer_one_success_count"], c.v["xfer_one_response.data.ok"] = "1", "true"
platform_exec(NG.embed(ID.XFER_CHECK, {"node": "xfer_one", "ok": "ok"}), {"vars": c.v})
o = c.finish()
check("H3b close transferred/support with no notes on any product", o == ("transferred", "support", []), o)
c = Call([LOAN])
c.run("HARDSHIP"); c.run("SUPPORT_ACCEPT")
c.v["xfer_one_response.data.ok"] = "true"            # a value from nowhere: the success counter did not move
platform_exec(NG.embed(ID.XFER_CHECK, {"node": "xfer_one", "ok": "ok"}), {"vars": c.v})
check("H3c a transfer counts only when the transfer call itself succeeded in this call", c.v.get("xfer_done") == "failed", c.v.get("xfer_done"))

# H4 the model's free answer cannot carry an amount, a date or a question
c = Call([LOAN])
c.ev(("p1", "refuses", "", ""), answer="I cannot offer a discount. Would you like to make a payment for your personal loan?")
check("H4a an answer with a question is dropped (only the code's offer is said)", "Would you like" not in c.v["neg_say"], c.v["neg_say"])
c = Call([LOAN])
c.ev(("p1", "refuses", "", ""), answer="You can pay 100 now.")
check("H4b an answer with an amount is dropped", "100 now" not in c.v["neg_say"], c.v["neg_say"])
c = Call([LOAN])
c.ev(("p1", "refuses", "", ""), answer="I am Freya Bank's digital assistant.")
check("H4c a plain one-sentence answer is kept, before the code's offer", c.v["neg_say"].startswith("I am Freya Bank's digital assistant."), c.v["neg_say"])

# H5 'I lost my job and I cannot pay' in one message: the 'no' answered the payment question, the support offer stays open
c = Call([LOAN])
c.v["support_reply"] = "declines"                    # a stale extraction from the same message
c.ev(("p1", "hardship", "", ""), ("p1", "refuses", "", ""))
check("H5 the support offer is open and the stale 'declines' cannot answer it", c.v.get("support_pending") == "yes" and c.v.get("support_reply") == "consumed"
      and c.p("p1")["status"] == "hardship_offer", (c.v.get("support_pending"), c.v.get("support_reply"), c.p("p1")["status"]))

# H6 a message cut off mid-sentence: ask to go on, count it, decide nothing
c = Call([LOAN])
c.v["cut_off"] = "yes"; c.v["go_on_count"] = "0"
c.run("GO_ON")
check("H6 go on: the policy sentence, the counter, the flag consumed, no state change", c.v["neg_say"] == "Please go on." and c.v["go_on_count"] == "1"
      and c.v["cut_off"] == "consumed" and not c.v.get("neg_state"), (c.v["neg_say"], c.v["go_on_count"]))
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

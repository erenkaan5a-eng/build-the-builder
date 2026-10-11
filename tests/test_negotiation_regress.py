"""Regression tests for the findings of the 11 Oct review (freya-kapsamli-inceleme.md / runtime-sonda-sonuclari.json).
Expected values are worked out by hand from Brief A/B; the bank is a local imitation (counters + response fields).
Section 1 = normal workflow event sequences; section 2 = defensive tests that enter a node directly."""
import sys
from negotiation_harness import Call, P, check, FAILS

# now Wed 14 Oct 2026: this week's last business day Fri 16 Oct; late deadline 23 Oct; early deadline 2 Nov (26 Oct holiday).
print("== 1. normal workflow sequences")

# A) partial information (A24-27, A35, B6-7)
c = Call([P("p1", "personal loan", 300.0, 100.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "vague", "150"))
c.ev(("p1", "proposes", "2026-10-16", ""))
check("A1 amount + vague period, then the exact day alone: 150 is kept (A27, A21)", (c.p("p1").get("agreed") or {}) == {"amount": 150.0, "date": "2026-10-16"}, c.p("p1"))

c = Call([P("p1", "personal loan", 300.0, 100.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "2026-10-16", ""))
v0 = c.st()["rb_version"]
c.ev(("p1", "changes", "", "150"))
check("A2 at the read-back only the amount changes: the date 16 Oct is kept, new read-back (A35)",
      (c.p("p1").get("agreed") or {}) == {"amount": 150.0, "date": "2026-10-16"} and c.st()["phase"] == "readback" and c.st()["rb_version"] > v0
      and "150.00 on Friday 16 October" in c.v["neg_say"], (c.p("p1"), c.st()["phase"], c.v["neg_say"]))

c = Call([P("p1", "personal loan", 300.0, 100.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "2026-10-16", "200"))
c.ev(("p1", "changes", "2026-10-20", ""))
check("A3 at the read-back only the date changes: the amount 200 is kept (A35)", (c.p("p1").get("agreed") or {}) == {"amount": 200.0, "date": "2026-10-20"}, c.p("p1"))

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 900.0, 300.0, "2026-10-23", 2)])
c.ev(("all", "proposes", "2026-10-21", ""))
c.ev(("p2", "changes", "", "400"))
check("A4 multi-product: changing p2's amount keeps p2's date and leaves p1 untouched (B7, A35)",
      c.p("p1")["agreed"] == {"amount": 300.0, "date": "2026-10-21"} and c.p("p2")["agreed"] == {"amount": 400.0, "date": "2026-10-21"} and c.st()["phase"] == "readback",
      (c.p("p1")["agreed"], c.p("p2").get("agreed"), c.st()["phase"]))
c.ev(("all", "confirms", "", ""))
sent = c.rec(["ok", "ok"])
check("A5 the writes equal the re-read package exactly (A34, B7)", sent == [("p1", "300.00", "2026-10-21"), ("p2", "400.00", "2026-10-21")], sent)

# B) whole-package confirmation (A34, B7)
c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.ev(("all", "proposes", "2026-10-16", ""))
st = c.ev(("p1", "confirms", "", ""))
check("B1 a confirmation for p1 alone does not open recording of the two-product package (B7)", st["phase"] == "readback" and c.v["neg_flag"] != "record", (st["phase"], c.v["neg_flag"]))
check("B2 the partial confirmation does not mark the other product refused", c.p("p2")["status"] == "agreed", c.p("p2")["status"])
c.run("CONFIRM")
check("B2b the read-back path (rb_answer) confirms the whole current package", c.v["neg_flag"] == "record", c.v["neg_flag"])

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.ev(("all", "proposes", "2026-10-16", ""))
st = c.ev(("all", "confirms", "", ""), ("p2", "changes", "2026-10-20", ""))
check("B3 'yes, but change the loan date' does not record; a new read-back names 20 Oct for the loan (A35, B7)",
      st["phase"] == "readback" and c.v["neg_flag"] != "record" and c.p("p2")["agreed"]["date"] == "2026-10-20" and c.p("p1")["agreed"]["date"] == "2026-10-16",
      (st["phase"], c.v["neg_flag"], c.p("p2").get("agreed")))
c.run("REC_NEXT")
check("B3b no write is planned before the new read-back is confirmed", c.v.get("rec_go") != "yes", c.v.get("rec_go"))

c = Call([P("p1", "credit card", 365.0, 109.5, "2026-10-23", 2)])
c.ev(("p1", "proposes", "2026-10-16", "")); c.ev(("p1", "confirms", "", ""))
sent = c.rec(["ok"]); again = c.rec([])
check("B4 a recorded promise is not sent again", sent == [("p1", "365.00", "2026-10-16")] and again == [] and c.v.get("rec_go") != "yes", (sent, again))

# C) notes and closing (B8-11, Closing, A46-47)
c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.ev(("all", "paid", "", ""))
o = c.finish(note_results=["ok", "http_error"])
res = c.st().get("note_results")
check("C1 each note's own result is kept: p1 recorded, p2 failed (the earlier ok is not carried over)",
      res == [["p1", "paid", "ok"], ["p2", "paid", "failed"]], res)
check("C2 a failed note does not turn the close into service_error (close stays paid)", o[:2] == ("paid", ""), o)

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.ev(("p1", "proposes", "2026-10-16", ""), ("p2", "refuses", "", ""), ("p2", "refuses", "", ""))
c.ev(("p2", "refuses", "", "")); c.ev(("p2", "refuses", "", ""))
c.ev(("all", "confirms", "", "")); c.rec(["ok"])
c.v["transfer_to_agent_args.queue"] = "restructuring"; c.v["transfer_to_agent_response.data.ok"] = "true"
o = c.finish()
check("C3 transfer after a recorded promise: transferred/restructuring, no notes at all (A46 table note, B10)", o == ("transferred", "restructuring", []), o)

# D) B4 mixed first answer
c = Call([P("p1", "credit card", 510.0, 153.0, "2026-10-23", 2), P("p2", "personal loan", 1320.0, 440.0, "2026-10-23", 2)])
c.ev(("p1", "proposes", "2026-10-15", ""))
check("D1 B4: after a mixed first answer the next product starts at attempt 1, today is not asked again",
      c.p("p2")["offer"] is not None and c.p("p2")["offer"]["kind"] == "attempt" and c.p("p2")["offer"]["date"] == "2026-10-16" and c.p("p2")["used"] == 1,
      c.p("p2"))

# E) 'too much' contexts (A26, A29, A30)
CARD = P("p1", "credit card", 2125.1, 637.5, "2026-10-23", 2)
c = Call([CARD]); c.ev(("p1", "too_much", "", ""))
check("E1 'too much' alone: one floor offer with the overdue sentence (current reading: attempt 1, Fri 16 Oct)",
      c.p("p1")["offer"]["amount"] == 637.5 and c.p("p1")["offer"]["date"] == "2026-10-16" and c.p("p1")["used"] == 1 and c.v["neg_say"].count("637.50") >= 1, c.p("p1"))
c = Call([CARD]); c.ev(("p1", "refuses", "", ""), ("p1", "too_much", "", ""))
check("E2 'not today' + 'too much' in one message: one floor offer, one attempt used", c.p("p1")["used"] == 1 and c.p("p1")["offer"]["amount"] == 637.5, c.p("p1"))
c = Call([CARD]); c.ev(("p1", "too_much", "", ""), ("p1", "refuses", "", ""))
check("E3 the same two signals in the other order: still one floor offer, one attempt used", c.p("p1")["used"] == 1 and c.p("p1")["offer"]["amount"] == 637.5, c.p("p1"))
c = Call([CARD]); c.ev(("p1", "too_much", "", ""), ("p1", "proposes", "2026-10-16", "1000"))
check("E4 'too much, but 1000 on Friday': the proposal is handled, no floor offer, no attempt used (A27, A29)",
      (c.p("p1").get("agreed") or {}) == {"amount": 1000.0, "date": "2026-10-16"} and c.p("p1")["used"] == 0, c.p("p1"))

# F) hardship sentence has one owner (A32, PUB-05)
c = Call([P("p1", "personal loan", 780.0, 260.0, "2026-10-23", 2)], uses_notes=False)
c.v["hardship_seen"] = "yes"
c.run("HARDSHIP")
first = c.v.get("neg_say")
c.run("HARDSHIP")
check("F1 the hardship node says the brief's sympathy + support offer once and marks it done", first == "Sorry to hear. Support team?" and c.v.get("hardship_done") == "yes" and c.p("p1")["status"] == "hardship_offer", (first, c.v.get("hardship_done")))
st = c.ev(("p1", "declines_support", "", ""))
check("F2 declining support -> finish no_promise/hardship", st["phase"] == "finish" and c.finish()[:2] == ("no_promise", "hardship"), st["phase"])

print("== 2. defensive tests (a node entered directly)")
c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.ev(("all", "proposes", "2026-10-16", ""))
c.run("REC_NEXT")
check("X1 REC_NEXT entered at the read-back (no confirmation): no write is planned", c.v.get("rec_go") != "yes", c.v.get("rec_go"))
st = c.st(); st["products"][0]["agreed"]["amount"] = 250.0
import json as _j; c.v["neg_state"] = _j.dumps(st)
c.run("CONFIRM")
check("X2 a package that differs from the one read back cannot be confirmed", c.v["neg_flag"] != "record", c.v["neg_flag"])
c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.ev(("p1", "proposes", "2026-10-16", ""))
o = c.finish()
check("X3 FINISH entered with an agreed-unrecorded and an open product: not ready, no invented refused/service_error notes",
      c.v.get("fin_ready") == "no" and c.notes_sent == [], (c.v.get("fin_ready"), o, c.notes_sent))

print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

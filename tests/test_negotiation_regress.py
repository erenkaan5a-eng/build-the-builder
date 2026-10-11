"""Regression tests for the findings of the 11 Oct review (freya-kapsamli-inceleme.md / runtime-sonda-sonuclari.json).
Expected values are worked out by hand from Brief A/B; the bank is a local imitation (counters + response fields).
Section 1 = normal workflow event sequences; section 2 = defensive tests that enter a node directly."""
import sys
from negotiation_harness import Call, P, check, FAILS, platform_exec

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

# G) cloud session 11 Oct: hardship together with the customer's own offer (A32 last sentence), one sympathy owner
LOAN05 = P("p1", "personal loan", 780.0, 260.0, "2026-10-23", 2)
c = Call([LOAN05], uses_notes=False)
c.ev(("p1", "hardship", "", ""), ("p1", "proposes", "2026-10-16", "150"), answer="I am so sorry about your job.")
check("G1 'lost my job but I can pay 150 on Friday': one sympathy + support offer, the model's answer text is dropped, 150/Friday kept",
      c.v["neg_say"] == "Sorry to hear. Support team?" and [e.get("amount") for e in c.st().get("held") or []] == ["150"], (c.v["neg_say"], c.st().get("held")))
c.ev(("p1", "declines_support", "", ""), answer="I understand.")
check("G2 support declined: the kept 150 is handled under the amount rule (below the floor -> floor offered once, Friday kept), no second sympathy",
      c.p("p1")["offer"] == {"amount": 260.0, "date": "2026-10-16", "kind": "below_floor"} and c.v["neg_say"].startswith("I cannot record less than 260.00") and "Sorry" not in c.v["neg_say"],
      (c.p("p1")["offer"], c.v["neg_say"]))
st = c.ev(("p1", "refuses", "", ""))
check("G3 refusing the floor after a hardship: no persuasion attempt (A32), product closes as hardship",
      c.p("p1")["status"] == "hardship" and c.p("p1")["used"] == 0 and st["phase"] == "finish" and c.finish()[:2] == ("no_promise", "hardship"), (c.p("p1"), st["phase"]))

c = Call([LOAN05], uses_notes=False)
c.v["hardship_early"] = "yes"          # said at the identity stage, kept by the account step
c.ev(("p1", "refuses", "", ""))
check("G4 a hardship from the identity stage is not forgotten: 'no' to paying today -> support offer, no attempt used",
      c.v["neg_say"] == "Sorry to hear. Support team?" and c.p("p1")["used"] == 0 and c.p("p1")["status"] == "hardship_offer", (c.v["neg_say"], c.p("p1")))
st = c.ev(("p1", "refuses", "", ""))
check("G5 'no' to the support offer is not a payment refusal: hardship, no ladder offer", c.p("p1")["status"] == "hardship" and c.p("p1")["used"] == 0 and st["phase"] == "finish", c.p("p1"))

c = Call([LOAN05], uses_notes=False)
c.ev(("p1", "hardship", "", ""), ("p1", "refuses", "", ""))
check("G6 'lost my job, I can't pay' in one message: the 'no' answers the payment question, the support offer stays open (not closed unanswered)",
      c.p("p1")["status"] == "hardship_offer" and c.st()["phase"] == "negotiate" and c.v["neg_say"] == "Sorry to hear. Support team?", (c.p("p1")["status"], c.st()["phase"]))
c.ev(("all", "proposes", "2026-10-21", "300"))
check("G7 after a hardship the customer names a date+amount for 'all': still handled (scope includes the hardship product)",
      (c.p("p1").get("agreed") or {}) == {"amount": 300.0, "date": "2026-10-21"}, c.p("p1"))

c = Call([LOAN05], uses_notes=False)
c.ev(("p1", "hardship", "", ""), ("p1", "pays_today", "", ""))
c.ev(("p1", "proposes", "2026-10-20", "400"))
check("G8 a new proposal while the support offer is open replaces the kept one (no double handling)",
      (c.p("p1").get("agreed") or {}) == {"amount": 400.0, "date": "2026-10-20"} and not c.st().get("held"), (c.p("p1"), c.st().get("held")))

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.v["hardship_seen"] = "yes"
c.ev(("p1", "proposes", "2026-10-16", "300"))
c.ev(("all", "declines_support", "", ""))
check("G9 B: kept proposal for p1 after the support offer, p2 closes as hardship (no persuasion on p2)",
      c.p("p1")["status"] == "agreed" and c.p("p2")["status"] == "hardship" and c.p("p2")["used"] == 0 and c.st()["phase"] == "readback", (c.p("p1")["status"], c.p("p2")))

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2), P("p3", "car loan", 140.0, 46.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "2026-10-16", ""))
c.ev(("p2", "hardship", "", ""))
check("G10 B: a hardship the model scoped to one product covers every open product; p1's agreed date is kept",
      c.p("p1")["status"] == "agreed" and c.p("p2")["status"] == "hardship_offer" and c.p("p3")["status"] == "hardship_offer", [c.p(x)["status"] for x in ("p1", "p2", "p3")])
c.ev(("all", "declines_support", "", ""))
check("G11 ... support declined: p1 read back alone, p2/p3 hardship (no persuasion)", c.st()["phase"] == "readback" and c.p("p2")["status"] == "hardship" and c.p("p3")["status"] == "hardship" and c.p("p3")["used"] == 0,
      (c.st()["phase"], [c.p(x)["status"] for x in ("p1", "p2", "p3")]))

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 900.0, 300.0, "2026-10-23", 2)])
c.ev(("all", "proposes", "2026-10-30", ""))
check("G12 the deadline note of a clamped product is a separate sentence in the read-back (chat C3 showed '...23 October Friday 23 October...')",
      "900.00 on Friday 23 October. (latest date for personal loan)" in c.v["neg_say"], c.v["neg_say"])

# K) the call's language: day and month names come from the policy (calendar.day_names/month_names), English otherwise
TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
TR_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
c = Call([P("p1", "kredi kartı", 300.0, 90.0, "2026-11-02", 1)], days=TR_DAYS, months=TR_MONTHS)
c.ev(("p1", "proposes", "2026-10-16", ""))
check("K1 read-back in the policy's language: 'Cuma 16 Ekim', no English day or month name", "Cuma 16 Ekim" in c.v["neg_say"] and "Friday" not in c.v["neg_say"] and "October" not in c.v["neg_say"], c.v["neg_say"])
c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "2026-10-16", ""))
check("K2 without names in the policy: English as before", "Friday 16 October" in c.v["neg_say"], c.v["neg_say"])

# L) input formats that are not the kit's: the call's 'now' and amounts said in another convention (generic parsing)
for now in ("2026-10-14T11:00", "2026-10-14 11:00:00", "2026-10-14T11:00:00+03:00", "2026-10-14T08:00:00Z", "14.10.2026 11:00", "14/10/2026", "2026-10-14"):
    c = Call([P("p1", "kredi kartı", 300.0, 90.0, "2026-11-02", 1)], now=now)
    c.ev(("p1", "proposes", "2026-10-16", ""))
    ok = (c.p("p1").get("agreed") or {}).get("date") == "2026-10-16" and not c.v.get("neg_error")
    check(f"L1 now {now!r} is read (today = Wed 14 Oct): Friday agreed", ok, (c.v.get("neg_error"), c.p("p1")))
c = Call([P("p1", "kredi kartı", 300.0, 90.0, "2026-11-02", 1)], now="next Tuesday")
c.ev(("p1", "proposes", "2026-10-16", ""))
check("L2 an unreadable 'now' is an error (no machine clock)", bool(c.v.get("neg_error")) and "now" in c.v["neg_error"], c.v.get("neg_error"))
for said, want in (("1.234,56", 1234.56), ("1,234.56", 1234.56), ("1234,5", 1234.5), ("12.500", 12500.0), ("2.125,10 TL", 2125.10), ("₺ 950", 950.0), ("1500", 1500.0)):
    c = Call([P("p1", "kredi kartı", 20000.0, 100.0, "2026-11-02", 1)])
    c.ev(("p1", "proposes", "2026-10-16", said))
    check(f"L3 amount {said!r} -> {want}", (c.p("p1").get("agreed") or {}).get("amount") == want, (c.v.get("neg_error"), c.p("p1").get("agreed")))

# H) section 5 properties of the cloud review not covered above
c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.ev(("all", "proposes", "2026-10-16", "")); c.ev(("all", "confirms", "", ""))
sent = c.rec(["ok", "http_error", "http_error"])
check("H1 p1 ok then p2 fails twice: p1's earlier ok is not carried to p2; one retry only (single layer); p2 service_error",
      sent == [("p1", "300.00", "2026-10-16"), ("p2", "600.00", "2026-10-16"), ("p2", "600.00", "2026-10-16")] and c.p("p1")["status"] == "recorded" and c.p("p2")["status"] == "service_error",
      (sent, c.p("p2")["status"]))
o = c.finish()
check("H2 ... close promise; p2 gets a service_error note (B11); spoken result names the failed product",
      o == ("promise", "", [("p2", "service_error")]) and "Not recorded for personal loan" in c.v["fin_say"] and "You will receive a text message." in c.v["fin_say"], (o, c.v["fin_say"]))

c = Call([P("p1", "credit card", 365.0, 109.5, "2026-10-23", 2)], retries=0, uses_notes=False)
c.ev(("p1", "proposes", "2026-10-16", "")); c.ev(("p1", "confirms", "", ""))
sent = c.rec(["http_error", "ok"])
check("H3 a brief with no retry: exactly one attempt, then service_error, no SMS sentence",
      len(sent) == 1 and c.p("p1")["status"] == "service_error" and c.finish()[:2] == ("no_promise", "service_error") and "text message" not in c.v["fin_say"], (sent, c.v.get("fin_say")))

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.ev(("all", "proposes", "2026-10-16", "")); c.ev(("all", "confirms", "", ""))
c.v["transfer_to_agent_args.queue"] = "restructuring"; c.v["transfer_to_agent_response.data.ok"] = "true"
sent = c.rec(["ok", "ok"])
check("H4 transfer before the confirmed package is written: nothing is written (B10), the stale 'record' flag is cleared",
      sent == [] and c.v.get("rec_go") == "blocked" and c.v.get("neg_flag") == "used", (sent, c.v.get("rec_go"), c.v.get("neg_flag")))
o = c.finish()
check("H5 ... transferred/restructuring, no notes", o == ("transferred", "restructuring", []), o)

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1)], uses_notes=False)
c.ev(("p1", "proposes", "2026-10-16", ""))
o1 = c.finish(); o2 = c.finish(); o3 = c.finish()
check("H6 FINISH 'not ready' is bounded: twice back to the negotiation, then a close without invented notes",
      [o1[0], o2[0]] == [None, None] and c.v.get("fin_ready") == "yes" and o3[2] == [], (o1, o2, o3, c.v.get("fin_ready")))

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 600.0, 200.0, "2026-10-23", 2)])
c.ev(("all", "proposes", "2026-10-16", ""))
for i in range(3):
    st = c.ev(("p1", "confirms", "", ""))
check("H7 repeated single-product confirmations of a 2-product package: confirmation question repeated, package kept, nothing recorded, no refusal",
      st["phase"] == "readback" and c.v["neg_say"] == "Do you confirm?" and c.p("p2")["status"] == "agreed" and c.v["neg_flag"] != "record", (st["phase"], c.v["neg_say"]))
st = c.ev(("all", "confirms", "", ""))
check("H8 ... then a whole confirmation records both", c.v["neg_flag"] == "record" and c.rec(["ok", "ok"]) == [("p1", "300.00", "2026-10-16"), ("p2", "600.00", "2026-10-16")], c.v["neg_flag"])

c = Call([P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1)], uses_notes=False)
c.v["close_one_success_count"] = "1"; c.v["close_one_response.data.ok"] = "true"
platform_exec(NGc := __import__("negotiation").embed(__import__("negotiation").CLOSE_CHECK, {"ok": "ok"}), {"vars": c.v})
r1 = c.v["close_result"]
c.v["close_one_success_count"] = "0"; c.v["close_one_failure_count"] = "1"
platform_exec(NGc, {"vars": c.v})
check("H9 close_check makes the bank's close result visible (ok / failed)", (r1, c.v["close_result"]) == ("ok", "failed"), (r1, c.v["close_result"]))

# I) A45 'says twice that they do not want to talk' (count from the policy, not from code)
c = Call([P("p1", "personal loan", 780.0, 260.0, "2026-10-23", 2)], uses_notes=False, stop_close=2)
c.ev(("p1", "refuses", "", ""))
st = c.ev(("p1", "stop", "", ""), ("p1", "stop", "", ""))
check("I1 the first 'I do not want to talk' (said twice in one message counts once) is a non-answer: next attempt, no close",
      c.p("p1")["status"] == "offered" and c.p("p1")["used"] == 2 and st["phase"] == "negotiate" and st.get("stops") == 1, (c.p("p1"), st.get("stops")))
st = c.ev(("p1", "stop", "", ""))
check("I2 the second statement closes: no_promise/refused", st["phase"] == "finish" and c.finish()[:2] == ("no_promise", "refused"), st["phase"])
c = Call([P("p1", "personal loan", 780.0, 260.0, "2026-10-23", 2)], uses_notes=False)
st = c.ev(("p1", "stop", "", ""))
check("I3 a policy without the count keeps the earlier behaviour (one statement closes)", st["phase"] == "finish", st["phase"])

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

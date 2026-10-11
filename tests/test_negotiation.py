"""Local tests of builder/runtime/negotiation.py. Expected values are worked out by hand from the Brief A/B rules
(counts written in comments), not produced by the runtime under test. Fixture values are test data only."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder" / "runtime"))
import negotiation as NG

SAY = {"debt_intro": "I am calling about a late payment.", "product_line": "Your {name}: {amount} past due, {days} days late.",
       "first_ask_one": "Can you make this payment today?", "first_ask_all": "Can you pay all of them today?",
       "offer": "Could you pay {amount} on {date}?", "offer_named": "For your {name}, could you pay {amount} on {date}?",
       "floor_offer": "I can record {amount}; the rest stays overdue. Could you pay {amount} on {date}?",
       "below_floor": "I cannot record less than {amount}. Could you pay {amount} on {date}?",
       "not_business_day": "{day} is not a business day. Could you pay on {next}?", "after_deadline": "The latest date I can record is {deadline}.",
       "past": "That date has passed.", "ask_exact": "Which exact day?", "vague_deadline": "I can offer {deadline}.",
       "readback_intro": "To confirm:", "readback_item": "{name} {amount} on {date}", "readback_clamped": "(latest date for {name})",
       "confirm_question": "Do you confirm?", "recorded": "Recorded.", "not_recorded": "Not recorded for {name}.",
       "hardship": "Sorry to hear. Support team?", "paid": "Payments take a day.", "dispute": "Understood.", "checking": "One moment.", "error": "Please repeat."}
BASE = {"now_var": "now", "weekend_days": [5, 6], "holidays": ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"],
        "ladder": [{"amount": "full_or_floor_if_too_much", "date": "this_week_last_business_day_or_next_week_if_today"}, {"amount": "floor", "date": "deadline"}],
        "vague_asks": 1, "shared_date_clamps": True, "say": SAY, "rec_node": "record_one", "note_node": "note_one", "ok": "ok", "retries": 1, "queue_field": "queue",
        "queue_reason": {"restructuring": "restructuring", "general": "human", "support": "support"}, "transferred": "transferred", "promise": "promise",
        "paid": "paid", "no_promise": "no_promise", "statuses": {"refused": "refused", "hardship": "hardship", "dispute": "dispute", "paid": "paid", "service_error": "service_error"},
        "no_reason": ["promise", "paid"], "uses_notes": True, "after_promise_sentence": "You will receive a text message.", "goodbye": "Goodbye.",
        "technical": {"outcome": "no_promise", "reason": "service_error"}, "turn_vars": ["negotiate.total_turns", "neg_relay.total_turns"]}


def codes(**over):
    cfg = {**BASE, **over}
    return {k: NG.embed(getattr(NG, k), cfg) for k in ("ENGINE", "REC_NEXT", "FINISH", "NOTES_NEXT", "CONFIRM")}


def P(pid, name, full, floor, deadline, attempts):
    return {"id": pid, "name": name, "past_due": full, "floor": floor, "deadline": deadline, "attempts": attempts}


class Call:
    def __init__(self, prods, now="2026-10-14T11:00", **over):
        self.c = codes(**over)
        self.v = {"now": now, "products_json": json.dumps(prods)}
        self.turn = 0

    def ev(self, *events, same_turn=False, answer=""):
        # on the platform the first message of the stage lands in 'negotiate'; after a read-out reply the next one lands in 'neg_relay'
        if not same_turn:
            self.turn += 1
            if self.turn == 1:
                self.v["negotiate.total_turns"] = "1"
            else:
                self.v["neg_relay.total_turns"] = str(int(self.v.get("neg_relay.total_turns") or 0) + 1)
        exec(self.c["ENGINE"], {"vars": self.v, "params": {"answer": answer, "events": [dict(zip(("product_id", "type", "date", "amount"), e)) for e in events]}})
        return self.st()

    def st(self):
        return json.loads(self.v["neg_state"]) if self.v.get("neg_state") else None

    def p(self, pid):
        return [x for x in self.st()["products"] if x["id"] == pid][0]

    def rec(self, results):
        """results: list of 'ok' | 'http_error' | 'ok_false' applied to successive record attempts."""
        sent = []
        exec(self.c["REC_NEXT"], {"vars": self.v, "params": {}})
        for r in results:
            if self.v["rec_go"] != "yes":
                break
            sent.append((self.v["rec_product"], self.v["rec_amount"], self.v["rec_date"]))
            if r == "ok":
                self.v["record_one_success_count"] = str(int(self.v.get("record_one_success_count") or 0) + 1)
                self.v["record_one_response.data.ok"] = "true"
            elif r == "ok_false":
                self.v["record_one_success_count"] = str(int(self.v.get("record_one_success_count") or 0) + 1)
                self.v["record_one_response.data.ok"] = "false"
            else:
                self.v["record_one_failure_count"] = str(int(self.v.get("record_one_failure_count") or 0) + 1)
            exec(self.c["REC_NEXT"], {"vars": self.v, "params": {}})
        return sent

    def finish(self):
        exec(self.c["FINISH"], {"vars": self.v, "params": {}})
        notes = []
        while True:
            exec(self.c["NOTES_NEXT"], {"vars": self.v, "params": {}})
            if self.v["note_go"] != "yes":
                break
            notes.append((self.v["note_product"], self.v["note_reason"]))
        return self.v["fin_outcome"], self.v["fin_reason"], notes


FAILS = []


def check(name, cond, detail=""):
    print(("ok  " if cond else "FAIL"), name, "" if cond else "-> " + str(detail))
    if not cond:
        FAILS.append(name)


# now Wed 14 Oct 2026: this week's last business day Fri 16 Oct; late deadline (7th bd) 23 Oct; early deadline (12th bd, 26 Oct holiday) 2 Nov.
CARD12, LOAN12, CAR12 = P("p1", "credit card", 510.0, 153.0, "2026-10-23", 2), P("p2", "personal loan", 1320.0, 440.0, "2026-10-23", 2), P("p3", "car loan", 140.0, 46.0, "2026-11-02", 1)

# T1 PUB-12 shape: card tomorrow, loans refused; per-product attempt counters (loan 2, car 1)
c = Call([CARD12, LOAN12, CAR12])
c.ev(("p1", "proposes", "2026-10-15", ""), ("p2", "refuses", "", ""), ("p3", "refuses", "", ""))
check("T1 card agreed tomorrow", c.p("p1")["agreed"] == {"amount": 510.0, "date": "2026-10-15"}, c.p("p1"))
check("T1 loan attempt 1 = full on Fri 16 Oct", c.p("p2")["offer"] == {"amount": 1320.0, "date": "2026-10-16", "kind": "attempt"} and c.p("p2")["used"] == 1, c.p("p2"))
c.ev(("p2", "refuses", "", ""))
check("T1 loan attempt 2 = floor on deadline 23 Oct", c.p("p2")["offer"]["amount"] == 440.0 and c.p("p2")["offer"]["date"] == "2026-10-23" and c.p("p2")["used"] == 2, c.p("p2"))
c.ev(("p2", "refuses", "", ""))
check("T1 loan refused after 2 attempts; car attempt 1 offered", c.p("p2")["status"] == "refused" and c.p("p3")["offer"] == {"amount": 140.0, "date": "2026-10-16", "kind": "attempt"}, (c.p("p2")["status"], c.p("p3")))
st = c.ev(("p3", "refuses", "", ""))
check("T1 car refused after its single attempt -> read-back of the card only", c.p("p3")["status"] == "refused" and c.p("p3")["used"] == 1 and st["phase"] == "readback" and "credit card 510.00" in c.v["neg_say"] and "loan" not in c.v["neg_say"], (st["phase"], c.v["neg_say"]))
c.ev(("all", "confirms", "", ""))
sent = c.rec(["ok"])
check("T1 records exactly the confirmed card promise", sent == [("p1", "510.00", "2026-10-15")], sent)
o = c.finish()
check("T1 close promise + refused notes for loan and car", o == ("promise", "", [("p2", "refused"), ("p3", "refused")]), o)

# T2 PUB-13 shape: one date for both, loan clamped to its own deadline; card keeps 30 Oct
CARD13, LOAN13 = P("p1", "credit card", 300.0, 90.0, "2026-11-02", 1), P("p2", "personal loan", 900.0, 300.0, "2026-10-23", 2)
c = Call([CARD13, LOAN13])
st = c.ev(("all", "proposes", "2026-10-30", ""))
check("T2 card 30 Oct, loan clamped to 23 Oct, read-back names both", c.p("p1")["agreed"]["date"] == "2026-10-30" and c.p("p2")["agreed"]["date"] == "2026-10-23" and c.p("p2")["clamped"] and "30 October" in c.v["neg_say"] and "23 October" in c.v["neg_say"], c.v["neg_say"])
c.ev(("all", "confirms", "", ""))
sent = c.rec(["ok", "ok"])
check("T2 card recorded on 30 Oct, loan on 23 Oct (loan's date does not move the card)", sent == [("p1", "300.00", "2026-10-30"), ("p2", "900.00", "2026-10-23")], sent)
# T2b order swapped and now = Fri 16 Oct: early deadline = 12th bd after 16 Oct: 19,20,21,22,23,27,28,29,30,2,3,4 Nov -> 4 Nov; late = 7th: 19..23 (5), 27, 28 -> 28 Oct
c = Call([P("p1", "personal loan", 900.0, 300.0, "2026-10-28", 2), P("p2", "credit card", 300.0, 90.0, "2026-11-04", 1)], now="2026-10-16T11:00")
c.ev(("all", "proposes", "2026-10-30", ""))
check("T2b swapped order, other now: loan clamped to 28 Oct, card 30 Oct", c.p("p1")["agreed"]["date"] == "2026-10-28" and c.p("p2")["agreed"]["date"] == "2026-10-30", (c.p("p1")["agreed"], c.p("p2")["agreed"]))
# T2c the same named date for ONE product after its deadline is an offer (rule 23), not a clamp
c = Call([P("p1", "car loan", 1250.0, 400.0, "2026-10-23", 2)])
c.ev(("p1", "proposes", "2026-11-06", ""))
check("T2c single product after deadline -> deadline offered, not agreed", c.p("p1")["status"] == "offered" and c.p("p1")["offer"]["date"] == "2026-10-23" and "23 October" in c.v["neg_say"], c.p("p1"))
c.ev(("p1", "accepts", "", ""))
check("T2c accepting the deadline -> read-back", c.st()["phase"] == "readback" and c.p("p1")["agreed"] == {"amount": 1250.0, "date": "2026-10-23"}, c.st()["phase"])

# T3 PUB-06 shape: too much -> floor once (with 'rest stays overdue'); refusing the floor is a flat refusal -> attempt 1 = floor on Fri; attempt 2 = floor on deadline
CARD06 = P("p1", "credit card", 2125.1, 637.5, "2026-10-23", 2)
c = Call([CARD06])
c.ev(("p1", "too_much", "", ""))
check("T3 'too much' -> floor offered once as attempt 1, on Fri 16 Oct, with the overdue sentence", c.p("p1")["offer"] == {"amount": 637.5, "date": "2026-10-16", "kind": "floor_too_much"} and c.p("p1")["used"] == 1 and "rest stays overdue" in c.v["neg_say"], (c.p("p1"), c.v["neg_say"]))
c.ev(("p1", "refuses", "", ""))
check("T3 refusing it -> attempt 2 names the floor again on the deadline 23 Oct", c.p("p1")["offer"]["amount"] == 637.5 and c.p("p1")["offer"]["date"] == "2026-10-23" and c.p("p1")["used"] == 2, c.p("p1"))
st = c.ev(("p1", "refuses", "", ""))
check("T3 attempts used up -> finish", st["phase"] == "finish" and c.v["neg_flag"] == "finish", st["phase"])
o = c.finish()
check("T3 close no_promise/refused with a refused note (brief with notes)", o == ("no_promise", "refused", [("p1", "refused")]), o)
c2 = Call([CARD06], uses_notes=False)
c2.ev(("p1", "too_much", "", "")); c2.ev(("p1", "proposes", "2026-10-16", "637.5"))
check("T3b PUB-06 path: floor on Friday agreed -> read-back", c2.p("p1")["agreed"] == {"amount": 637.5, "date": "2026-10-16"} and c2.st()["phase"] == "readback", c2.p("p1"))

# T4 a proposal is not a refusal; T5 below floor once then refusal
c = Call([P("p1", "personal loan", 540.0, 180.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "2026-10-16", ""))
check("T4 proposing a date agrees the full amount, uses no attempt", c.p("p1")["agreed"] == {"amount": 540.0, "date": "2026-10-16"} and c.p("p1")["used"] == 0, c.p("p1"))
c = Call([P("p1", "personal loan", 540.0, 180.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "2026-10-16", "100"))
check("T5 below floor -> floor offered on the named valid date", c.p("p1")["offer"] == {"amount": 180.0, "date": "2026-10-16", "kind": "below_floor"}, c.p("p1"))
c.ev(("p1", "proposes", "2026-10-16", "100"))
check("T5 second below-floor -> flat refusal -> attempt 1", c.p("p1")["used"] == 1 and c.p("p1")["offer"]["kind"] == "attempt", c.p("p1"))

# T6 PUB-07 shape: vague once -> ask; holiday inside deadline -> next business day offered
c = Call([P("p1", "personal loan", 540.0, 180.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "vague", ""))
check("T6 vague -> ask exact day", c.v["neg_say"] == "Which exact day?" and c.p("p1")["vague"] == 1, c.v["neg_say"])
c.ev(("p1", "proposes", "2026-10-26", ""))
check("T6 holiday 26 Oct -> 27 Oct offered", c.p("p1")["offer"]["date"] == "2026-10-27" and c.p("p1")["offer"]["kind"] == "next_bd", c.p("p1"))
c.ev(("p1", "accepts", "", ""))
check("T6 accepted -> read-back 27 Oct", c.st()["phase"] == "readback" and "27 October" in c.v["neg_say"], c.v["neg_say"])
c = Call([P("p1", "personal loan", 540.0, 180.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "vague", "")); c.ev(("p1", "proposes", "vague", ""))
check("T6b vague twice -> deadline proposed", c.p("p1")["offer"]["date"] == "2026-11-02", c.p("p1"))

# T7 confirmation binding
c = Call([P("p1", "personal loan", 540.0, 180.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "2026-10-16", ""))
v1 = c.st()["rb_version"]
c.ev(("p1", "changes", "2026-10-20", ""))
check("T7 change at read-back -> new version, read-back of 20 Oct", c.st()["rb_version"] > v1 and "20 October" in c.v["neg_say"] and c.st()["phase"] == "readback", (c.st()["rb_version"], c.v["neg_say"]))
c.ev(("p1", "confirms", "", ""))
sent = c.rec(["ok"])
check("T7 confirmation binds the latest values", sent == [("p1", "540.00", "2026-10-20")], sent)
c = Call([P("p1", "personal loan", 540.0, 180.0, "2026-11-02", 1)])
c.ev(("p1", "refuses", "", ""))
st = c.ev(("p1", "confirms", "", ""))
check("T7b 'yes' before any read-back is not a confirmation (accepts the offer -> read-back)", st["phase"] == "readback", st["phase"])

# T8 the same event processed twice in one turn counts once
c = Call([CARD06])
c.ev(("p1", "refuses", "", ""))
c.ev(("p1", "refuses", "", ""), same_turn=True)
check("T8 duplicate event in the same turn does not consume a second attempt", c.p("p1")["used"] == 1, c.p("p1")["used"])

# T9 unknown product -> error, state unchanged; ambiguous product with several products -> error
c = Call([CARD13, LOAN13])
before = None
c.ev(("p9", "refuses", "", ""))
check("T9 unknown product -> error sentence, no state change", c.v["neg_say"] == "Please repeat." and "neg_state" not in c.v, c.v.get("neg_error"))
c.ev(("", "refuses", "", ""))
check("T9b product not named with two products -> error", c.v.get("neg_error", "").startswith("product not named"), c.v.get("neg_error"))

# T10 recording: first fails then succeeds; two failures -> no third attempt, service_error
c = Call([P("p1", "credit card", 365.0, 109.5, "2026-10-23", 2)], uses_notes=False)
c.ev(("p1", "proposes", "2026-10-16", "")); c.ev(("p1", "confirms", "", ""))
sent = c.rec(["http_error", "ok"])
check("T10 failure then success: two attempts, recorded", len(sent) == 2 and c.p("p1")["status"] == "recorded", (sent, c.p("p1")["status"]))
check("T10 close promise", c.finish()[:2] == ("promise", ""))
c = Call([P("p1", "credit card", 365.0, 109.5, "2026-10-23", 2)], uses_notes=False)
c.ev(("p1", "proposes", "2026-10-16", "")); c.ev(("p1", "confirms", "", ""))
sent = c.rec(["http_error", "ok_false", "ok"])
check("T10b two failures -> no third attempt", len(sent) == 2 and c.p("p1")["status"] == "service_error", (sent, c.p("p1")["status"]))
o = c.finish()
check("T10b close no_promise/service_error, the failure is said, no notes (brief without notes)", o == ("no_promise", "service_error", []) and "Not recorded" in c.v["fin_say"] and "Recorded." not in c.v["fin_say"], (o, c.v["fin_say"]))

# T11 partial success in a multi-product brief
c = Call([CARD13, LOAN13])
c.ev(("all", "proposes", "2026-10-21", "")); c.ev(("all", "confirms", "", ""))
sent = c.rec(["ok", "http_error", "http_error"])
o = c.finish()
check("T11 card recorded, loan failed twice -> promise + service_error note for the loan", o == ("promise", "", [("p2", "service_error")]), (sent, o))

# T12 transfer: transferred with the queue's reason, no notes at all
c = Call([CARD13, LOAN13])
c.ev(("p1", "refuses", "", ""))
c.v["transfer_to_agent_args.queue"] = "restructuring"; c.v["transfer_to_agent_response.data.ok"] = "true"
o = c.finish()
check("T12 transfer -> transferred/restructuring, no notes", o == ("transferred", "restructuring", []), o)

# T13 paid / dispute / hardship closing precedence
c = Call([CARD13, LOAN13])
c.ev(("all", "paid", "", ""))
check("T13 all paid -> close paid, notes paid", c.finish() == ("paid", "", [("p1", "paid"), ("p2", "paid")]))
c = Call([CARD13, LOAN13])
c.ev(("p1", "paid", "", ""), ("p2", "dispute", "", ""))
check("T13b paid + dispute -> no_promise with the first non-paid reason (dispute)", c.finish() == ("no_promise", "dispute", [("p1", "paid"), ("p2", "dispute")]))
c = Call([P("p1", "personal loan", 780.0, 260.0, "2026-10-23", 2)], uses_notes=False)
c.ev(("p1", "hardship", "", ""))
check("T13c hardship -> support offer said, no persuasion offer", c.v["neg_say"] == "Sorry to hear. Support team?" and c.p("p1")["used"] == 0, c.v["neg_say"])
st = c.ev(("p1", "declines_support", "", ""))
check("T13c declines support -> finish no_promise/hardship", st["phase"] == "finish" and c.finish()[:2] == ("no_promise", "hardship"), st["phase"])

# T14 missing / bad account snapshot -> error, nothing invented
c = Call([CARD06]); del c.v["products_json"]
c.ev(("p1", "refuses", "", ""))
check("T14 no product snapshot -> error sentence, no state", c.v["neg_say"] == "Please repeat." and "neg_state" not in c.v, c.v.get("neg_error"))

# T15 regression of the live PUB-12 run: the same product refused again in a later message must reach its next attempt
c = Call([CARD12, LOAN12, CAR12])
c.ev(("p1", "proposes", "2026-10-15", ""), ("p2", "refuses", "", ""), ("p3", "refuses", "", ""))
c.ev(("p2", "refuses", "", ""))
check("T15 second refusal in a later message is not taken for a duplicate", c.p("p2")["used"] == 2 and c.p("p2")["offer"]["date"] == "2026-10-23", c.p("p2"))
# T16 never an empty reply; the answer field is put before the code's sentence
c = Call([CARD06])
c.ev(("p1", "too_much", "", ""))
c.ev(("p1", "too_much", "", ""), same_turn=True)
check("T16 duplicate call gives the pending offer again, not an empty sentence", c.v["neg_say"].startswith("Could you pay 637.50") or "637.50" in c.v["neg_say"], c.v["neg_say"])
c.ev(("p1", "refuses", "", ""), answer="I am Freya Bank's digital assistant.")
check("T16 answer comes first, then the code's offer", c.v["neg_say"].startswith("I am Freya Bank's digital assistant.") and "637.50" in c.v["neg_say"], c.v["neg_say"])

# T17 deterministic read-back confirmation (extraction path): records only for the current read-back
c = Call([CARD13, LOAN13])
c.ev(("all", "proposes", "2026-10-30", ""))
exec(c.c["CONFIRM"], {"vars": c.v, "params": {}})
check("T17 confirmation of the current read-back -> record", c.v["neg_flag"] == "record" and c.st()["phase"] == "record", (c.v["neg_flag"], c.st()["phase"]))
c = Call([P("p1", "personal loan", 540.0, 180.0, "2026-11-02", 1)])
c.ev(("p1", "proposes", "2026-10-16", ""))
c.ev(("p1", "changes", "2026-10-26", ""))   # holiday: the next business day is only OFFERED, no new read-back yet
exec(c.c["CONFIRM"], {"vars": c.v, "params": {}})
check("T17b a 'yes' after a change but before the new read-back does not record", c.v["neg_flag"] != "record" and c.st()["phase"] != "record", (c.v["neg_flag"], c.st()["phase"]))

# T18 'already paid' ends the talk: its sentence is kept for the closing line; the required sentence is said once
c = Call([P("p1", "credit card", 180.0, 54.0, "2026-11-02", 1)], uses_notes=False)
st = c.ev(("p1", "paid", "", ""))
o = c.finish()
check("T18 paid -> closing line says the paid sentence then goodbye; close paid", st["phase"] == "finish" and c.v["fin_say"].startswith("Payments take a day.") and o[:2] == ("paid", ""), (c.v["fin_say"], o))
c = Call([P("p1", "credit card", 365.0, 109.5, "2026-10-23", 2)], uses_notes=False, say={**SAY, "recorded": "Recorded. You will receive a text message."})
c.ev(("p1", "proposes", "2026-10-16", "")); c.ev(("p1", "confirms", "", "")); c.rec(["ok"]); c.finish()
check("T18b the required sentence is not repeated", c.v["fin_say"].count("You will receive a text message") == 1, c.v["fin_say"])
# T19 declining support without an earlier hardship event still means hardship, no persuasion
c = Call([P("p1", "personal loan", 780.0, 260.0, "2026-10-23", 2)], uses_notes=False)
st = c.ev(("p1", "declines_support", "", ""))
check("T19 declines_support -> hardship -> finish no_promise/hardship", st["phase"] == "finish" and c.finish()[:2] == ("no_promise", "hardship"), st["phase"])
# T20 the PUB-06 path: 'too much' -> floor on Friday -> accepted -> read-back without a second floor offer
c = Call([CARD06])
c.ev(("p1", "too_much", "", "")); st = c.ev(("p1", "accepts", "", ""))
check("T20 accepted floor offer -> read-back 637.50 on Friday 16 October", st["phase"] == "readback" and "637.50 on Friday 16 October" in c.v["neg_say"] and ".." not in c.v["neg_say"], c.v["neg_say"])

# T21 hardship mentioned earlier in the call (extracted flag): a refusal is answered with the hardship response, no attempt used
c = Call([P("p1", "personal loan", 780.0, 260.0, "2026-10-23", 2)], uses_notes=False)
c.v["hardship_seen"] = "yes"
c.ev(("p1", "refuses", "", ""))
check("T21 earlier hardship -> support offer instead of persuasion", c.v["neg_say"] == "Sorry to hear. Support team?" and c.p("p1")["used"] == 0 and c.p("p1")["status"] == "hardship_offer", (c.v["neg_say"], c.p("p1")))
st = c.ev(("p1", "refuses", "", ""))
check("T21 'no' to the support offer -> hardship -> finish no_promise/hardship, offer not repeated", st["phase"] == "finish" and c.finish()[:2] == ("no_promise", "hardship"), st["phase"])
c = Call([P("p1", "personal loan", 780.0, 260.0, "2026-10-23", 2)], uses_notes=False)
c.v["hardship_seen"] = "yes"
c.ev(("p1", "proposes", "2026-10-16", "260"))
# 11 Oct cloud change: the sympathy + support offer comes first (A32 'one short sentence of sympathy'; earlier the
# proposal was taken at once and the sympathy was never said); the customer's own date/amount is kept, not lost
check("T21b hardship + own date/amount: sympathy and support offer first, the proposal is kept",
      c.v["neg_say"] == "Sorry to hear. Support team?" and c.p("p1")["status"] == "hardship_offer" and c.st().get("held"), (c.v["neg_say"], c.st().get("held")))
c.ev(("p1", "declines_support", "", ""))
check("T21b ... after the support offer is declined the kept proposal is read back and can be recorded (rule 32)",
      c.p("p1")["agreed"] == {"amount": 260.0, "date": "2026-10-16"} and c.st()["phase"] == "readback" and "Sorry" not in c.v["neg_say"], (c.p("p1"), c.v["neg_say"]))

print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

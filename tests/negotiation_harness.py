"""Shared harness for negotiation runtime tests: runs the generated code snippets with a local vars dict and a
local imitation of the engine-run bank nodes (record_one / note_one counters and response fields).
All bank answers here are local imitations, not live evidence."""
import json, pathlib, sys, textwrap
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
       "hardship": "Sorry to hear. Support team?", "paid": "Payments take a day.", "dispute": "Understood.", "checking": "One moment.", "error": "Please repeat.",
       "no_terms": "No other terms.", "go_on": "Please go on.", "robot_answer": "I am a digital assistant."}
BASE = {"now_var": "now", "weekend_days": [5, 6], "holidays": ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"],
        "ladder": [{"amount": "full_or_floor_if_too_much", "date": "this_week_last_business_day_or_next_week_if_today"}, {"amount": "floor", "date": "deadline"}],
        "vague_asks": 1, "shared_date_clamps": True, "say": SAY, "rec_node": "record_one", "note_node": "note_one", "ok": "ok", "retries": 1, "queue_field": "queue",
        "queue_reason": {"restructuring": "restructuring", "general": "human", "support": "support"}, "transferred": "transferred", "promise": "promise",
        "paid": "paid", "no_promise": "no_promise", "statuses": {"refused": "refused", "hardship": "hardship", "dispute": "dispute", "paid": "paid", "service_error": "service_error"},
        "no_reason": ["promise", "paid"], "uses_notes": True, "after_promise_sentence": "You will receive a text message.", "goodbye": "Goodbye.",
        "technical": {"outcome": "no_promise", "reason": "service_error"}, "turn_vars": ["negotiate.total_turns", "neg_relay.total_turns"],
        "support_queue": "support", "xfer_node": "xfer_one"}
def platform_exec(code, g):
    """Run generated code the way the platform runs it: inside a function, with vars/params as its arguments.
    Observed 11 Oct (chat C2): a 'global' statement that works under a plain exec() fails there with NameError."""
    ns = {}
    exec(compile("def __platform_run(vars, params):\n" + textwrap.indent(code, "    ", lambda line: True) + "\n", "<generated>", "exec"), ns)
    ns["__platform_run"](g.get("vars"), g.get("params", {}))


SNIPPETS = ("ENGINE", "REC_NEXT", "FINISH", "NOTES_NEXT", "CONFIRM", "HARDSHIP", "SUPPORT_DECLINE", "SUPPORT_ACCEPT", "GO_ON")


def P(pid, name, full, floor, deadline, attempts):
    return {"id": pid, "name": name, "past_due": full, "floor": floor, "deadline": deadline, "attempts": attempts}


class Call:
    def __init__(self, prods, now="2026-10-14T11:00", **over):
        cfg = {**BASE, **over}
        self.c = {k: NG.embed(getattr(NG, k), cfg) for k in SNIPPETS if hasattr(NG, k)}
        self.v = {"now": now, "products_json": json.dumps(prods)}
        self.turn = 0
        self.writes, self.notes_sent, self.log = [], [], []

    def run(self, name, params=None):
        if name not in self.c:
            self.log.append(name + ":missing")
            return
        self.log.append(name)
        platform_exec(self.c[name], {"vars": self.v, "params": params if params is not None else {}})

    def ev(self, *events, same_turn=False, answer=""):
        if not same_turn:
            self.turn += 1
            if self.turn == 1:
                self.v["negotiate.total_turns"] = "1"
            else:
                self.v["neg_relay.total_turns"] = str(int(self.v.get("neg_relay.total_turns") or 0) + 1)
        self.run("ENGINE", {"answer": answer, "events": [dict(zip(("product_id", "type", "date", "amount"), e)) for e in events]})
        return self.st()

    def st(self):
        return json.loads(self.v["neg_state"]) if self.v.get("neg_state") else None

    def p(self, pid):
        return [x for x in self.st()["products"] if x["id"] == pid][0]

    def _bank(self, node, r):
        if r == "ok":
            self.v[f"{node}_success_count"] = str(int(self.v.get(f"{node}_success_count") or 0) + 1)
            self.v[f"{node}_response.data.ok"] = "true"
        elif r == "ok_false":
            self.v[f"{node}_success_count"] = str(int(self.v.get(f"{node}_success_count") or 0) + 1)
            self.v[f"{node}_response.data.ok"] = "false"
        else:  # HTTP error: the response field keeps its earlier value, only the failure counter moves
            self.v[f"{node}_failure_count"] = str(int(self.v.get(f"{node}_failure_count") or 0) + 1)

    def rec(self, results):
        """Engine-run recording loop; results apply to successive create_promise attempts. Returns the writes sent."""
        sent = []
        self.run("REC_NEXT")
        for r in results:
            if self.v.get("rec_go") != "yes":
                break
            sent.append((self.v["rec_product"], self.v["rec_amount"], self.v["rec_date"]))
            self._bank("record_one", r)
            self.run("REC_NEXT")
        self.writes += sent
        return sent

    def finish(self, note_results=None):
        """FINISH then the notes loop; note_results apply to successive add_note calls (default: all ok)."""
        self.run("FINISH")
        sent = []
        results = list(note_results or [])
        if self.v.get("fin_ready", "yes") == "no":
            return self.v.get("fin_outcome"), self.v.get("fin_reason"), sent
        while True:
            self.run("NOTES_NEXT")
            if self.v.get("note_go") != "yes":
                break
            sent.append((self.v["note_product"], self.v["note_reason"]))
            self._bank("note_one", results.pop(0) if results else "ok")
        self.notes_sent += sent
        return self.v["fin_outcome"], self.v["fin_reason"], sent


FAILS = []


def check(name, cond, detail=""):
    print(("ok  " if cond else "FAIL"), name, "" if cond else "-> " + str(detail)[:300])
    if not cond:
        FAILS.append(name)

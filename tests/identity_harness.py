"""Harness for the identity runtime: runs the code snippets taken from a GENERATED workflow (the same strings that are
published) inside a function, the way the platform runs them, and imitates the engine around them: the routing on
id_flag, the engine-run verify call with its pre-hook, the bank, the post-hook and the flattened result keys.

The bank here is a local imitation written from the tool API's description (tools/openapi.json) and Brief A rules
11-14; it is independent of the runtime under test. Two engine modes are imitated because the platform behaviour is
not fully documented: 'hook' (the post-hook runs and the flattened keys are written from the hooked result) and
'nohook' (no post-hook; only the keys present in the new body are overwritten, older keys stay). Local imitation only,
not live evidence."""
import datetime, json, pathlib, re, sys, textwrap
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
import toolspec, components  # noqa: E402

TS = toolspec.load(str(ROOT / "tools" / "openapi.json"))


def run_fn(code, args):
    """Run generated code inside a function with the given names as its arguments (platform-like)."""
    ns = {}
    names = ", ".join(args)
    exec(compile(f"def __run({names}):\n" + textwrap.indent(code, "    ", lambda line: True) + "\n", "<generated>", "exec"), ns)
    ns["__run"](*args.values())


def code_of(node):
    return node["pre_actions"][0]["function"]["parameters"]["properties"]["code"]["default"]


class Bank:
    """verify_identity imitation: three wrong answers in total end the check; a day/month swap returns the hint and
    does not count; an unreadable value is ok=false and does not count. Returns the JSON body, or 'http_error'."""

    def __init__(self, dob, phone, wrong_left=3):
        self.truth = {"date_of_birth": dob, "phone_last4": phone}
        self.left = wrong_left
        self.ok_fields = set()
        self.calls = []
        self.faults = []          # queued: 'http_error' | 'ok_false' | dict body to return as is

    def verify(self, field, answer):
        self.calls.append((field, answer))
        if self.faults:
            f = self.faults.pop(0)
            if f == "http_error":
                return "http_error"
            if f == "ok_false":
                return {"ok": False, "error": "service refused"}
            return f
        if self.left <= 0:
            return {"ok": False, "error": "identity check ended", "wrong_answers_left": 0}
        if field == "date_of_birth":
            try:
                d = datetime.date.fromisoformat(answer)
                assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", answer)
            except Exception:
                return {"ok": False, "error": "unreadable date"}
            t = datetime.date.fromisoformat(self.truth[field])
            if d == t:
                return self._pass(field)
            if d.day != d.month and (d.year, d.day, d.month) == (t.year, t.month, t.day):
                return {"ok": True, "verified": False, "hint": "day_month_swapped", "wrong_answers_left": self.left}
        elif field == "phone_last4":
            if not re.fullmatch(r"\d{4}", answer):
                return {"ok": False, "error": "four digits expected"}
            if answer == self.truth[field]:
                return self._pass(field)
        else:
            return {"ok": False, "error": "unknown field"}
        self.left -= 1
        return {"ok": True, "verified": False, "wrong_answers_left": self.left}

    def _pass(self, field):
        self.ok_fields.add(field)
        return {"ok": True, "verified": True, "all_verified": self.ok_fields >= set(self.truth), "wrong_answers_left": self.left}


class IdCall:
    """One call through the identity stage of a workflow generated from a policy fixture."""

    def __init__(self, pol, bank, mode="hook"):
        self.wf = components.build(pol, TS)
        N = self.wf["nodes"]
        tool = N["identity"]["tools"][0]
        self.event_code = tool["function"]["parameters"]["properties"]["code"]["default"]
        self.send_code = code_of(N["id_send"])
        self.result_code = code_of(N["id_result"])
        self.consume_code = code_of(N["id_consume"])
        va = N["id_verify"]["pre_actions"][0]
        self.pre_hook, self.post_hook = va.get("pre_process_code", ""), va.get("post_process_code", "")
        self.body_tmpl = va["function"]["parameters"]["properties"]["body"]["properties"]
        self.bank, self.mode = bank, mode
        self.v = {"now": "2026-10-14T11:00", "customer_id": "c_test"}
        self.said, self.sent, self.trace = [], [], []
        self.end = None           # ('account',) | ('close', outcome, reason) | ('transfer', queue)
        self.no_reprocess_ok = True

    # ---- engine imitation
    def _bank_call(self):
        body = {k: (self.v.get(spec["default"].strip("{}")) if spec["default"].startswith("{{") else spec["default"]) for k, spec in self.body_tmpl.items()}
        config = {"body": body}
        if self.pre_hook:
            run_fn(self.pre_hook, {"vars": self.v, "config": config})
        body = config["body"]
        self.sent.append((body.get("field"), body.get("answer")))
        r = self.bank.verify(body.get("field"), body.get("answer"))
        node = "id_verify"
        if r == "http_error":
            self.v[f"{node}_failure_count"] = str(int(self.v.get(f"{node}_failure_count") or 0) + 1)
            return
        self.v[f"{node}_success_count"] = str(int(self.v.get(f"{node}_success_count") or 0) + 1)
        result = {"status": "success", "data": dict(r), "status_code": 200, "header": {"Content-Type": "application/json"}}
        if self.mode == "hook" and self.post_hook:
            run_fn(self.post_hook, {"result": result, "vars": self.v, "config": config})
        for k, val in (result.get("data") or {}).items():       # flattened keys: present keys overwrite, others stay
            self.v[f"{node}_response.data.{k}"] = str(val).lower() if isinstance(val, bool) else str(val)

    def _route(self):
        for _ in range(12):
            flag = self.v.get("id_flag")
            self.trace.append(flag)
            if flag == "verify":
                run_fn(self.send_code, {"vars": self.v})
                if self.v.get("id_go") != "yes":
                    self.said.append(self.v.get("id_say", ""))
                    run_fn(self.consume_code, {"vars": self.v})
                    return
                self._bank_call()
                run_fn(self.result_code, {"vars": self.v})
                continue
            if flag == "say":
                self.said.append(self.v.get("id_say", ""))
                run_fn(self.consume_code, {"vars": self.v})
                return
            if flag == "account":
                if self.v.get("security_verified") == "yes":
                    self.end = ("account",)
                return
            if flag == "close":
                self.said.append(self.v.get("fin_say", ""))
                self.end = ("close", self.v.get("fin_outcome"), self.v.get("fin_reason"))
                return
            if flag == "transfer":
                self.end = ("transfer", self.v.get("xfer_queue"))
                return
            return
        raise RuntimeError("routing loop: " + str(self.trace[-12:]))

    # ---- one customer message, as the dialogue model's events
    def msg(self, *events):
        evs = []
        for e in events:
            if isinstance(e, str):
                evs.append({"type": e})
            else:
                evs.append(dict(e))
        run_fn(self.event_code, {"vars": self.v, "params": {"events": evs}})
        self._route()
        return self.said[-1] if self.said else ""

    def reenter_result(self):
        """A repeated entry into id_result without a new request (e.g. a stale routing): must change nothing."""
        before = self.v.get("id_state")
        run_fn(self.result_code, {"vars": self.v})
        self.no_reprocess_ok = json.loads(before or "{}").get("verified") == json.loads(self.v.get("id_state") or "{}").get("verified") \
            and json.loads(self.v.get("id_state") or "{}").get("done") == json.loads(before or "{}").get("done")
        return self.no_reprocess_ok

    def st(self):
        return json.loads(self.v.get("id_state") or "{}")


def A(day=None, month=None, year=None, digits=None, field=None, kind="answer"):
    e = {"type": kind}
    for k, val in (("day", day), ("month", month), ("year", year), ("digits", digits), ("field", field)):
        if val is not None:
            e[k] = str(val)
    return e


def C(**kw):
    return A(kind="correction", **kw)

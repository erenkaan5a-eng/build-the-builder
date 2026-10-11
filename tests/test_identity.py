"""Identity stage: event sequences through the code generated from the policy fixtures (tests/fixtures), with a local
bank imitation (tests/identity_harness.py). Expected values are worked out by hand from Brief A rules 11-15 and 42
and the tool API; the test values (dates, digits) are test data only and appear nowhere in the builder.
Every sequence runs in both engine modes ('hook', 'nohook'): the post-hook's effect on the flattened keys is not
documented, so the runtime must be right in both."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from identity_harness import Bank, IdCall, A, C, run_fn, code_of, TS  # noqa: E402
from negotiation_harness import check, FAILS  # noqa: E402
import components, lint  # noqa: E402

POL = json.load(open(ROOT / "tests" / "fixtures" / "policy-a.json", encoding="utf-8"))
ASK_DOB, ASK_PHONE = POL["identity"]["questions"][0]["ask"], POL["identity"]["questions"][1]["ask"]
FAILED = ("close", "not_verified", "failed")
DECLINED = ("close", "not_verified", "declined")

for mode in ("hook", "nohook"):
    print(f"== engine mode: {mode}")
    M = f"[{mode}]"

    # I1 PUB-06 --style pieces (11 Oct failure): day+month, then the year; two digits, then two digits
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    r1 = c.msg(A(day=17, month=5))
    check(f"I1a {M} 'May seventeenth': no bank call, only the year is asked", b.calls == [] and "year" in r1 and "day" not in r1, (b.calls, r1))
    r2 = c.msg(A(year=1986))
    check(f"I1b {M} 'nineteen eighty-six': ONE verify call with the combined date, then the phone question",
          b.calls == [("date_of_birth", "1986-05-17")] and ASK_PHONE in r2, (b.calls, r2))
    r3 = c.msg(A(digits="15"))
    check(f"I1c {M} 'one five': no bank call, the remaining digits are asked", len(b.calls) == 1 and "remaining digits" in r3, (b.calls, r3))
    c.msg(A(digits="02"))
    check(f"I1d {M} 'zero two': one call with '1502' (text kept), account reached", b.calls[-1] == ("phone_last4", "1502") and len(b.calls) == 2 and c.end == ("account",)
          and c.v.get("security_verified") == "yes", (b.calls, c.end))
    check(f"I1e {M} no wrong answer used by the pieces", b.left == 3, b.left)

    # I2 the year first, then day and month
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    r = c.msg(A(year=1986))
    check(f"I2a {M} year alone: the day and month are asked, no bank call", b.calls == [] and "day" in r and "month" in r, r)
    c.msg(A(day=17, month=5))
    check(f"I2b {M} day+month complete it: one call", b.calls == [("date_of_birth", "1986-05-17")], b.calls)

    # I3 correction in the same message (one bank call for one customer message)
    b = Bank("1986-05-17", "4721"); c = IdCall(POL, b, mode)
    c.msg(A(day=17, month=5, year=1986))
    c.msg(A(digits="4821"), C(digits="4721"))
    check(f"I3 {M} '4821, sorry 4721': one call with 4721", [x for x in b.calls if x[0] == "phone_last4"] == [("phone_last4", "4721")] and c.end == ("account",), b.calls)

    # I3b correction of one date part in a later message keeps the other parts
    b = Bank("1986-05-17", "4721"); c = IdCall(POL, b, mode)
    c.msg(A(day=17, month=5))
    c.msg(C(year=1986))
    check(f"I3b {M} a corrected/added year keeps day and month", b.calls == [("date_of_birth", "1986-05-17")], b.calls)

    # I4 PUB-03: three wrong dates of birth -> failed on the bank's result, no account
    b = Bank("1992-07-21", "6630"); c = IdCall(POL, b, mode)
    c.msg(A(day=12, month=7, year=1991)); c.msg(A(day=21, month=8, year=1992)); last = c.msg(A(day=21, month=7, year=1990))
    check(f"I4 {M} PUB-03: failed after the third wrong answer, app/branch sentence, no account", c.end == FAILED and "mobile app" in last
          and c.v.get("security_verified") != "yes" and len(b.calls) == 3, (c.end, last, b.calls))
    after = c.msg(A(digits="6630"))
    check(f"I4b {M} after the close nothing more is sent", len(b.calls) == 3, b.calls)

    # I5 right DOB + wrong phone: only the phone is asked again; wrong answers spread over both questions
    b = Bank("1983-10-19", "4410"); c = IdCall(POL, b, mode)
    c.msg(A(day=19, month=10, year=1983))
    r = c.msg(A(digits="4401"))
    check(f"I5a {M} PUB-12: a wrong phone answer -> only the phone question again (the DOB is not asked again)",
          ASK_PHONE in r and ASK_DOB not in r and c.end is None, r)
    c.msg(A(digits="4410"))
    check(f"I5b {M} the second phone answer passes -> account", c.end == ("account",) and b.calls[0] == ("date_of_birth", "1983-10-19"), (c.end, b.calls))
    b = Bank("1983-10-19", "4410"); c = IdCall(POL, b, mode)
    c.msg(A(day=1, month=1, year=1980)); c.msg(A(day=19, month=10, year=1983)); c.msg(A(digits="1111")); last = c.msg(A(digits="2222"))
    check(f"I5c {M} 1 wrong DOB + 2 wrong phones = three in total -> failed", c.end == FAILED and len(b.calls) == 4, (c.end, b.calls))
    c.msg(A(day=19, month=10, year=1983))
    check(f"I5d {M} a verified question is never sent again", [x for x in b.calls if x == ("date_of_birth", "1983-10-19")] == [("date_of_birth", "1983-10-19")], b.calls)

    # I6 day/month swapped hint + the month as a word: not a wrong answer
    b = Bank("1990-03-05", "8846"); c = IdCall(POL, b, mode)
    r = c.msg(A(day=3, month=5, year=1990))
    check(f"I6a {M} swapped hint: the month is asked as a word, no wrong answer used", b.calls == [("date_of_birth", "1990-05-03")] and "month" in r and b.left == 3, (b.calls, r))
    c.msg(A(month="march"))
    check(f"I6b {M} 'March' alone completes the date from the two numbers heard -> verified", b.calls[-1] == ("date_of_birth", "1990-03-05") and b.left == 3
          and ASK_PHONE in c.said[-1], (b.calls, c.said[-1]))
    r = c.msg(A(digits="1234"))
    check(f"I6c {M} a later wrong phone answer is a wrong answer, not an old hint", "does not match" in r and b.left == 2, (r, b.left))

    # I7 ok=false (unreadable / refused by the service): not counted, asked again
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode); b.faults = ["ok_false"]
    r = c.msg(A(day=17, month=5, year=1986))
    check(f"I7 {M} ok=false: not a wrong answer, the same question again", b.left == 3 and ASK_DOB in r and c.end is None, (r, b.left))

    # I8 service errors: one automatic retry; then 'could not check' and the question again; never a wrong answer
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode); b.faults = ["http_error"]
    c.msg(A(day=17, month=5, year=1986))
    check(f"I8a {M} one HTTP error: one automatic retry, then verified", len(b.calls) == 2 and ASK_PHONE in c.said[-1], (b.calls, c.said))
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode); b.faults = ["http_error", "http_error"]
    r = c.msg(A(day=17, month=5, year=1986))
    check(f"I8b {M} two HTTP errors: 'could not check' + the question again, nothing counted", "could not check" in r and ASK_DOB in r and b.left == 3 and c.end is None, r)
    b.faults = ["http_error", "http_error"]
    r = c.msg(A(day=17, month=5, year=1986))
    check(f"I8c {M} service errors again: technical close (not failed, not declined)", c.end == ("close", "no_promise", "service_error"), c.end)

    # I9 a stale or repeated result is not processed twice
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    c.msg(A(day=17, month=5, year=1986))
    check(f"I9 {M} a repeated entry into the result step changes nothing", c.reenter_result() and c.st().get("verified") == ["date_of_birth"], c.st())

    # I10 an unreadable phone answer after a verified DOB: the old 'verified=true' must not pass the phone
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    c.msg(A(day=17, month=5, year=1986)); b.faults = [{"ok": False, "error": "four digits expected"}]
    r = c.msg(A(digits="1502"))
    check(f"I10 {M} ok=false after a verified question: no account, the phone question again", c.end is None and c.v.get("security_verified") != "yes" and ASK_PHONE in r, (c.end, r))

    # I11 declines (rule 15): explanation once, the second refusal closes 'declined'; never 'failed' without the bank
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    r = c.msg("refuses")
    check(f"I11a {M} first refusal: the protection explanation + the question", "protect" in r and ASK_DOB in r and c.end is None, r)
    c.msg("asks_purpose")
    check(f"I11b {M} 'what is this about?' instead of an answer is the second decline -> declined, no bank call", c.end == DECLINED and b.calls == [], (c.end, b.calls))
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    c.msg("asks_purpose", A(day=17, month=5, year=1986))
    check(f"I11c {M} a question together with an answer is not a decline", c.st().get("declines") == 0 and len(b.calls) == 1, c.st())
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    c.msg("asks_purpose"); c.msg(A(day=17, month=5, year=1986)); r = c.msg("asks_purpose")
    check(f"I11e {M} style asks_back: question, answer, question again -> not closed (the answer restarted the count), phone asked",
          c.end is None and ASK_PHONE in r and "protect" not in r, (c.end, r))
    c.msg("refuses")
    check(f"I11f {M} two in a row after that -> declined", c.end == DECLINED, c.end)
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    c.msg("stop"); c.msg(A(day=17, month=5, year=1986)); c.msg("stop")
    check(f"I11g {M} A45: 'I do not want to talk' twice in the identity stage -> declined, even with an answer in between", c.end == DECLINED, c.end)
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    for _ in range(6):
        c.msg("other")
    check(f"I11d {M} no event sequence without bank results reaches 'failed'", c.end is None and b.calls == [], (c.end, b.calls))

    # I12 a person asked for (rule 42): help offered once, then the engine-run transfer to the policy's queue
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    r = c.msg("human")
    check(f"I12a {M} first request for a person: the 'can I help' question only", r == POL["human_request"]["say"] and c.end is None, r)
    c.msg("human")
    check(f"I12b {M} insists: transfer to the general queue", c.end == ("transfer", "general"), c.end)

    # I13 questions during identity: the policy's answer, then the step continues; a partial answer is kept
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    r = c.msg("robot", A(day=17, month=5))
    check(f"I13 {M} robot question + day/month: the policy's answer, then only the year", r.startswith(POL["negotiation"]["say"]["robot_answer"]) and "year" in r and b.calls == [], r)

    # I14 digits: leading zero kept; too many digits is not sent; not a calendar date is not sent; a 2-digit year asks the year
    b = Bank("1979-11-02", "0358"); c = IdCall(POL, b, mode)
    c.msg(A(day=2, month=11, year=1979)); c.msg(A(digits="03")); c.msg(A(digits="58"))
    check(f"I14a {M} 'zero three' + 'five eight' -> '0358'", b.calls[-1] == ("phone_last4", "0358") and c.end == ("account",), b.calls)
    b = Bank("1979-11-02", "0358"); c = IdCall(POL, b, mode)
    c.msg(A(day=2, month=11, year=1979)); r = c.msg(A(digits="03581"))
    check(f"I14b {M} five digits: 'could not understand', no bank call", len(b.calls) == 1 and "could not understand" in r, (b.calls, r))
    b = Bank("1979-11-02", "0358"); c = IdCall(POL, b, mode)
    r = c.msg(A(day=31, month=2, year=1979))
    check(f"I14c {M} 31 February: not sent, asked again", b.calls == [] and ASK_DOB in r, r)
    r = c.msg(A(day=2, month=11, year=79))
    check(f"I14d {M} a two-digit year: the year is asked, nothing sent", b.calls == [] and "year" in r, r)

    # I14e a part the model could not turn into digits is asked again; the parts heard are kept
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    r = c.msg(A(day=17, month=5, year="nineteen eighty-six"))
    check(f"I14e {M} a year not in digits: only the year is asked, day and month kept", b.calls == [] and "year" in r and "day" not in r, r)
    c.msg(A(year=1986))
    check(f"I14f {M} then the year completes the date: one call", b.calls == [("date_of_birth", "1986-05-17")], b.calls)

    # I15 a bank answer that verifies the last question without full verification: technical close, never the account
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    c.msg(A(day=17, month=5, year=1986)); b.faults = [{"ok": True, "verified": True, "all_verified": False, "wrong_answers_left": 3}]
    c.msg(A(digits="1502"))
    check(f"I15 {M} contradictory bank result: no account, technical close", c.end == ("close", "no_promise", "service_error") and c.v.get("security_verified") != "yes", c.end)

    # I17 both answers in one message: the DOB first; the phone answer is kept and sent once the DOB passed
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    c.msg(A(day=17, month=5, year=1986), A(digits="1502", field="phone_last4"))
    check(f"I17 {M} DOB + phone in one message: two calls in order, account", b.calls == [("date_of_birth", "1986-05-17"), ("phone_last4", "1502")]
          and c.end == ("account",), (b.calls, c.end))
    b = Bank("1986-05-17", "1502"); c = IdCall(POL, b, mode)
    c.msg(A(day=1, month=1, year=1980), A(digits="1502", field="phone_last4"))
    check(f"I17b {M} a wrong DOB with the phone in the same message: the phone is not sent before the DOB passed", b.calls == [("date_of_birth", "1980-01-01")]
          and ASK_DOB in c.said[-1], (b.calls, c.said[-1]))

    # I16 a new call starts clean
    c2 = IdCall(POL, Bank("1986-05-17", "1502"), mode)
    check(f"I16 {M} a new call has no identity state", c2.st() == {} and c2.v.get("security_verified") is None, c2.st())

print("== generated workflow: identity structure")
ts = TS
for label, f in (("A", "policy-a.json"), ("A+B", "policy-ab.json")):
    pol = json.load(open(ROOT / "tests" / "fixtures" / f, encoding="utf-8"))
    wf = components.build(pol, ts)
    N = wf["nodes"]
    errs = [p for p in lint.lint(wf, str(ROOT / "tools" / "openapi.json")) if not p.startswith("warn:")]
    check(f"S0 {label}: lint has no errors", not errs, errs)
    tools = [t["function"]["name"] for t in N["identity"]["tools"]]
    check(f"S1 {label}: the identity stage gives the dialogue model no bank tool (no verify, close or transfer)", tools == ["identity_event"], tools)
    into_acct = [(k, t) for k, n in N.items() for t in n.get("transitions") or [] if t["target_node"] == "fetch_account"]
    gated = all(k == "id_result" and {"variable": "security_verified", "operator": "equals", "operand": "yes"} in t["condition"]["conditions"][0]["conditions"] for k, t in into_acct)
    check(f"S2 {label}: every way into the account call needs the bank's full verification (security_verified)", into_acct and gated, into_acct)
    where_verify = [k for k, n in N.items() for t in (n.get("tools") or []) + (n.get("pre_actions") or []) if (t.get("function") or {}).get("name") == "verify_identity"]
    check(f"S3 {label}: verify_identity is called only by the engine-run node", where_verify == ["id_verify"], where_verify)
    bad = []
    for k, n in N.items():
        for t in n.get("tools") or []:
            if t["function"]["name"] == "close_call":
                en = t["function"]["parameters"]["properties"]["body"]["properties"]["reason"].get("enum")
                if not en or "failed" in en or "declined" not in en:
                    bad.append((k, en))
    check(f"S4 {label}: every close tool of the dialogue model lists the table's reasons except the identity 'failed' (bank evidence needed)", not bad, bad)
    deal = code_of(N["build_deal"])
    v = {"now": "2026-10-14T11:00", "fetch_account_response.data.ok": "true", "fetch_account_response.data.products.0.product_id": "p1",
         "fetch_account_response.data.products.0.type": "personal_loan", "fetch_account_response.data.products.0.past_due": "100",
         "fetch_account_response.data.products.0.days_late": "5", "fetch_account_response.data.products.0.instalment_amount": "50"}
    run_fn(deal, {"vars": v})
    check(f"S5 {label}: the account step states no debt without the bank's verification in this call", v.get("acct_state") == "error" and not v.get("debt_say"), v.get("acct_state"))
    v["security_verified"] = "yes"
    run_fn(deal, {"vars": v})
    check(f"S5b {label}: with it, the debt statement is built", v.get("acct_state") == "ok" and "100.00" in v.get("debt_say", ""), v.get("debt_say"))
    idr = [t["target_node"] for t in N["id_relay"]["transitions"]]
    check(f"S6 {label}: the identity reply is read by a fixed line, then the next message goes back to the event step", N["id_relay"]["on_enter"] == {"type": "tts", "text": "{{id_say}}"}
          and idr == ["identity"] and not N["id_relay"].get("tools"), idr)
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

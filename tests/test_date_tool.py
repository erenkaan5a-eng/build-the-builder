"""Local tests of builder/runtime/date_tool.py. Expected dates come from public-test-set.json (organizer answers)
and from Brief A rules 19-23, not from the runtime under test."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder" / "runtime"))
import date_tool
CFG = json.load(open(ROOT / "eval/fixtures/date_config_a.json"))
CODE = date_tool.build_code(CFG)

def run(products, date, pid="p1", now="2026-10-14T11:00", state=None, flat=False):
    v = dict(state or {})
    v["now"] = now
    if flat:
        for i, p in enumerate(products):
            for k, x in p.items(): v[f"get_account_response.data.products.{i}.{k}"] = x
    else:
        v["products"] = json.dumps(products)
    exec(CODE, {"vars": v, "params": {"date": date, "product_id": pid}})
    return v

def P(pid, late): return {"product_id": pid, "type": "personal_loan", "past_due": 100, "days_late": late, "instalment_amount": 30}
cases = [
  ("PUB-07 holiday inside deadline -> next business day", [P("p1", 5)], "2026-10-26", "p1", "not_business_day", "2026-10-27"),
  ("PUB-04 after late deadline -> deadline",              [P("p1", 14)], "2026-11-06", "p1", "after_deadline", "2026-10-23"),
  ("PUB-06 this Friday ok",                               [P("p1", 12)], "2026-10-16", "p1", "ok", "2026-10-16"),
  ("PUB-13 card early band 30 Oct ok",                    [P("p1", 4), P("p2", 20)], "2026-10-30", "p1", "ok", "2026-10-30"),
  ("PUB-13 loan late band 30 Oct -> 23 Oct",              [P("p1", 4), P("p2", 20)], "2026-10-30", "p2", "after_deadline", "2026-10-23"),
  ("Saturday inside deadline -> Monday (rule 20)",        [P("p1", 5)], "2026-10-17", "p1", "not_business_day", "2026-10-19"),
  ("today is allowed (rule 19)",                          [P("p1", 5)], "2026-10-14", "p1", "ok", "2026-10-14"),
  ("yesterday is past",                                   [P("p1", 5)], "2026-10-13", "p1", "past", ""),
  ("early deadline is the 12th business day = 2 Nov",     [P("p1", 5)], "2026-11-02", "p1", "ok", "2026-11-02"),
  ("one day after early deadline",                        [P("p1", 5)], "2026-11-03", "p1", "after_deadline", "2026-11-02"),
  ("flattened product keys",                              [P("p1", 14)], "2026-10-26", "p1", "after_deadline", "2026-10-23"),
  ("two products, unknown id -> error, nothing proposed", [P("p1", 4), P("p2", 20)], "2026-10-16", "p9", "error", ""),
]
fails = 0
for name, prods, date, pid, dec, prop in cases:
    v = run(prods, date, pid, flat=name.startswith("flattened"))
    ok = v["date_decision"] == dec and v["date_proposed"] == prop and v["date_flag"] == "new"
    fails += not ok
    print(("ok  " if ok else "FAIL"), name, "->", v["date_decision"], v["date_proposed"], "|", v["date_say"])
# vague: ask once, then propose deadline (rule 21)
st = {}
v1 = run([P("p1", 5)], "vague", state=st); st = {k: x for k, x in v1.items() if k.startswith("date_vague")}
v2 = run([P("p1", 5)], "vague", state=st)
ok = v1["date_decision"] == "ask_exact" and v2["date_decision"] == "propose_deadline" and v2["date_proposed"] == "2026-11-02"
fails += not ok
print(("ok  " if ok else "FAIL"), "vague twice -> ask exact, then deadline", v1["date_decision"], v2["date_decision"], v2["date_proposed"])
# now = Fri 16 Oct, late band: business days after today 19,20,21,22,23,(26 holiday),27,28 -> 7th = 28 Oct
v = run([P("p1", 14)], "2026-10-29", now="2026-10-16T11:00")
ok = v["date_decision"] == "after_deadline" and v["date_proposed"] == "2026-10-28"; fails += not ok
print(("ok  " if ok else "FAIL"), "now=Fri 16 Oct, late deadline skips holiday -> 28 Oct", v["date_decision"], v["date_proposed"])
print("FAILURES:", fails); sys.exit(1 if fails else 0)

"""The fixed components call operations by role (verify_identity, get_account, ...); a contract may name them otherwise.
toolspec.bind_roles points each role at the operation the policy names for it in `operations`. Checked offline: the
kit's practice API with every path renamed (and moved under another prefix) + the policy of an earlier traced practice
build with an `operations` map added -> validation passes, the generated workflow calls only the renamed URLs and passes
the local lint against the renamed contract; unknown names, clashes and double bindings are reported, never guessed;
behavior.py names engine-run calls by role. No model or Freya call."""
import copy, json, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
sys.path.insert(0, str(ROOT / "tests"))
import toolspec, spec_extract, components, behavior  # noqa: E402
import lint as linter  # noqa: E402
from negotiation_harness import check, FAILS  # noqa: E402

API = ROOT / "tools" / "openapi.json"
POL = json.load(open(ROOT / "candidates" / "loc-a" / "20261011-133408" / "policy.json", encoding="utf-8"))
RENAME = {"verify_identity": "kimlik/dogrula", "get_account": "hesap/ozet", "create_promise": "odeme/soz",
          "add_note": "not/ekle", "schedule_callback": "geri-arama", "transfer_to_agent": "temsilci/aktar", "close_call": "gorusme/kapat"}

spec = json.load(open(API, encoding="utf-8"))
ren = copy.deepcopy(spec)
ren["paths"] = {}
for p, item in spec["paths"].items():
    role = p.rsplit("/", 1)[-1]
    ren["paths"]["/" + RENAME.get(role, role.strip("/"))] = item
ren["servers"] = [{"url": "https://mock.example.workers.dev/api"}]
tmp = pathlib.Path(tempfile.mkdtemp())
(tmp / "contract.json").write_text(json.dumps(ren), encoding="utf-8")
ts = toolspec.load(tmp / "contract.json")
check("R0 the renamed contract has none of the role names", not set(components.ROLES) & set(ts["ops"]), sorted(ts["ops"]))

# without a map: every role is missing -> validation problems, nothing built
ts0, bound0, p0 = toolspec.bind_roles(ts, None, components.ROLES)
probs0 = p0 + spec_extract.validate(POL, ts0)
check("R1 no operations map on a renamed contract: validation reports the missing operations", bound0 == {} and any("no operation verify_identity" in p for p in probs0), probs0[:3])

pol = dict(POL, operations={r: RENAME[r] for r in components.ROLES})
ts1, bound, probs = toolspec.bind_roles(ts, pol["operations"], components.ROLES)
probs += spec_extract.validate(pol, ts1)
check("R2 with the map: every role bound, policy validates against the renamed contract", bound == {r: RENAME[r] for r in components.ROLES} and probs == [], probs)
check("R3 the required operations are present after binding", not set(components.REQUIRED_OPS) - set(ts1["ops"]))
wf = components.build(pol, ts1)
s = json.dumps(wf)
urls = {u for u in __import__("re").findall(r'https://mock\.example\.workers\.dev/api/[A-Za-z0-9_/\-]+', s)}
check("R4 the workflow calls only the contract's URLs (all renamed ones that the build uses)",
      urls and urls <= {"https://mock.example.workers.dev/api/" + v for v in RENAME.values()} and "/api/kimlik/dogrula" in s and "/api/gorusme/kapat" in s, sorted(urls))
check("R5 no URL of an operation the contract does not have", "/verify_identity\"" not in s and "/get_account\"" not in s)
lp = linter.lint(wf, tmp / "contract.json")
check("R6 the generated workflow passes the local lint against the renamed contract", lp == [], lp[:5])

# the same contract written with $ref schemas (components/schemas) and 201 success answers reads the same
refd = copy.deepcopy(ren)
refd.setdefault("components", {}).setdefault("schemas", {})
for p, item in refd["paths"].items():
    op = item.get("post") or item.get("get")
    key = p.strip("/").replace("/", "_").replace("-", "_")
    body = op["requestBody"]["content"]["application/json"]
    refd["components"]["schemas"][key + "_req"] = body["schema"]
    body["schema"] = {"$ref": f"#/components/schemas/{key}_req"}
    ok = op["responses"].pop("200")
    refd["components"]["schemas"][key + "_resp"] = ok["content"]["application/json"]["schema"]
    ok["content"]["application/json"]["schema"] = {"$ref": f"#/components/schemas/{key}_resp"}
    op["responses"]["201"] = ok
(tmp / "contract-ref.json").write_text(json.dumps(refd), encoding="utf-8")
ts_r = toolspec.load(tmp / "contract-ref.json")
check("R12 $ref schemas and a 201 success answer: the contract reads exactly like the inline one", ts_r == ts, [k for k in ts["ops"] if ts_r["ops"].get(k) != ts["ops"][k]])
lp_r = linter.lint(wf, tmp / "contract-ref.json")
check("R13 the local lint reads the $ref contract too (same workflow passes)", lp_r == [], lp_r[:5])
cyc = {"paths": {"/a": {"post": {"requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/A"}}}}}}},
       "components": {"schemas": {"A": {"type": "object", "properties": {"self": {"$ref": "#/components/schemas/A"}, "x": {"type": "string"}}}}}}
d = toolspec.deref(cyc)
check("R14 a reference cycle stops instead of looping; a missing reference is left visible",
      "x" in d["paths"]["/a"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
      and toolspec.deref({"a": {"$ref": "#/nope"}}) == {"a": {"$ref": "#/nope"}})

# reported, never guessed
_, b, pr = toolspec.bind_roles(ts, {"verify_identity": "kimlik/yok"}, components.ROLES)
check("R7 an unknown operation name is a problem", any("'kimlik/yok' is not an operation" in p for p in pr) and "verify_identity" not in b, pr)
_, b, pr = toolspec.bind_roles(ts, {"get_account": "hesap/ozet", "create_promise": "hesap/ozet"}, components.ROLES)
check("R8 one operation bound to two roles is a problem", any("several roles" in p for p in pr), pr)
ts_k = toolspec.load(API)
_, b, pr = toolspec.bind_roles(ts_k, {"close_call": "transfer_to_agent"}, components.ROLES)
check("R9 binding a role to another operation while a same-named one exists is a problem", any("also has an operation named 'close_call'" in p for p in pr), pr)
_, b, pr = toolspec.bind_roles(ts_k, None, components.ROLES)
check("R10 the kit's own API without a map: every role binds to its same-named operation (earlier policies keep working)",
      pr == [] and b == {r: r for r in components.ROLES}, (b, pr))

# behavior.py: engine-run calls (handler 'api_call' + URL) are named by role through the policy's operation_urls
behavior.ROLE_BY_URL.clear()
behavior.ROLE_BY_URL.update({ts["ops"][n]["url"]: r for r, n in bound.items()})
ev = behavior.parse_events([{"role": "system", "message": json.dumps({"event": "function_call_start", "function": "api_call",
                             "args": {"url": "https://mock.example.workers.dev/api/kimlik/dogrula", "body": {"x": 1}}})},
                            {"role": "system", "message": json.dumps({"event": "function_call_complete", "function": "api_call", "result": {"ok": True}})}])
check("R11 behavior.py names an engine-run call to a renamed URL by its role", [e[:2] for e in ev] == [("call", "verify_identity"), ("result", "verify_identity")], ev)
behavior.ROLE_BY_URL.clear()
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

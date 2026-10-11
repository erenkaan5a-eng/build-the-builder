"""Before/after evidence: the structure checks of test_identity.py (S1-S4) and test_generator_structure.py (S5-S6) applied to the generator of a given
git revision with that revision's own stored policy (no model or Freya call).

    python tests/evidence_old_identity.py <git-rev> <policy.json>
"""
import importlib, json, pathlib, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
rev, pol_path = sys.argv[1], sys.argv[2]
tmp = pathlib.Path(tempfile.mkdtemp())
for f in ("builder/components.py", "builder/toolspec.py", "builder/lint.py", "builder/runtime/negotiation.py", "builder/runtime/date_tool.py"):
    (tmp / f).parent.mkdir(parents=True, exist_ok=True)
    (tmp / f).write_bytes(subprocess.run(["git", "show", f"{rev}:{f}"], cwd=ROOT, capture_output=True, check=True).stdout)
sys.path.insert(0, str(tmp / "builder"))
components, toolspec = importlib.import_module("components"), importlib.import_module("toolspec")
wf = components.build(json.load(open(pol_path, encoding="utf-8")), toolspec.load(str(ROOT / "tools" / "openapi.json")))
N = wf["nodes"]
res = []
tools = [t["function"]["name"] for t in N["identity"]["tools"]]
res.append(("S1 identity stage gives the dialogue model no bank tool", tools == ["identity_event"], tools))
into = [(k, json.dumps(t["condition"])) for k, n in N.items() for t in n.get("transitions") or [] if t["target_node"] == "fetch_account"]
res.append(("S2 every way into the account call needs security_verified (set by code from the bank's full verification)",
            bool(into) and all("security_verified" in c for _, c in into), into))
where = [k for k, n in N.items() for t in (n.get("tools") or []) + (n.get("pre_actions") or []) if (t.get("function") or {}).get("name") == "verify_identity"]
res.append(("S3 verify_identity only in an engine-run node", where == ["id_verify"], where))
bad = [k for k, n in N.items() for t in n.get("tools") or [] if t["function"]["name"] == "close_call"
       and (not t["function"]["parameters"]["properties"]["body"]["properties"]["reason"].get("enum")
            or "failed" in t["function"]["parameters"]["properties"]["body"]["properties"]["reason"]["enum"])]
res.append(("S4 no model close tool offers the identity 'failed' reason (bank evidence needed)", not bad, bad))
relay = [t["target_node"] for t in N["neg_relay"]["transitions"]]
res.append(("S5 the answer to the support offer is routed by code before the dialogue model speaks (A32)", "hs_accept" in relay and "hs_decline" in relay, relay))
res.append(("S6 a message cut off mid-sentence is answered with a request to go on", relay[:1] == ["go_on"], relay))
print(f"generator at {rev}, policy {pol_path}")
for name, ok, det in res:
    print(("ok  " if ok else "FAIL"), name, "" if ok else "-> " + str(det)[:300])

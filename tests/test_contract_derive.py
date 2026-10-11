"""build.derive_contract: a package whose services are only described in prose gets its contract written inside the
traced run (model call faked here; no network): structural check, one bounded repair, the result is written next to the
candidate and logged with its hash and conflicts; an unusable result stops with a visible error."""
import json, pathlib, sys, tempfile, asyncio
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder")); sys.path.insert(0, str(ROOT / "tests"))
import build, case_input, spec_extract  # noqa: E402
from negotiation_harness import check, FAILS  # noqa: E402

GOOD = {"openapi": "3.0.0", "servers": [{"url": "https://svc.example/api/v2"}], "x-conflicts": ["doc A says x, doc B says y"],
        "paths": {"/a.get": {"post": {"operationId": "a.get", "requestBody": {"content": {"application/json": {"schema": {
            "type": "object", "properties": {"data": {"type": "object", "properties": {"id": {"type": "string"}}}}}}}},
            "responses": {"200": {"content": {"application/json": {"schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}}}}}}}}}}
BAD = {"openapi": "3.0.0", "paths": {"/a.get": {"post": {"responses": {}}}}}

class T:
    def __init__(self): self.lines = []
    def log(self, k, m): self.lines.append((k, m))
    def model_call(self, *a, **k): pass
class B:
    def left(self): return 3000

def run(answers):
    seq = list(answers)
    async def fake(prompt, system, model, trace, purpose):
        return json.dumps(seq.pop(0))
    real = spec_extract._ask; spec_extract._ask = fake
    cand = pathlib.Path(tempfile.mkdtemp()); tr = T()
    try:
        out, err = build.derive_contract("CASE TEXT", cand, B(), tr), None
    except RuntimeError as e:
        out, err = None, str(e)
    finally:
        spec_extract._ask = real
    return out, err, tr.lines, seq

out, err, lines, left = run([GOOD])
check("D1 a usable derived contract is written next to the candidate and logged with hash, operations and conflicts",
      err is None and out.name == "contract.derived.json" and json.loads(out.read_text())["paths"] and
      any("POST /a.get" in m and "sha256" in m for _, m in lines) and any("conflict: doc A says x" in m for _, m in lines), lines)
out, err, lines, left = run([BAD, GOOD])
check("D2 structural problems get one bounded repair call", err is None and not left and any("one bounded repair" in m for _, m in lines), lines)
out, err, lines, left = run([BAD, BAD])
check("D3 still unusable after the repair: a visible error, nothing bound", out is None and "unusable" in (err or ""), err)
check("D4 check_contract: missing server, request schema and 2xx are reported", len(case_input.check_contract(BAD)) == 3, case_input.check_contract(BAD))
tmp = pathlib.Path(tempfile.mkdtemp()); (tmp / "c.json").write_text(json.dumps(GOOD))
note = case_input.bind_contract(tmp / "c.json", "https://mock.example.workers.dev", tmp / "bound.json")
check("D6 bound server = mock host + the contract's own path", json.loads((tmp / "bound.json").read_text())["servers"][0]["url"] == "https://mock.example.workers.dev/api/v2", note)
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

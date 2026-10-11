"""Local contract check for the renamed-API experiment (experiments/api-rename). No model or Freya call.

What it shows: (1) the deterministic validation rejects a policy whose api_binding still names the old fields, so a
build would go to its bounded repair call instead of generating a broken agent; (2) given a binding to the new names,
the generator uses only the binding (no field name of the kit API is hard-coded) and the result lints against the
renamed API. The binding in (2) is a TEST FIXTURE written here, not a model extraction: this file does not show that
the extraction step finds the new names. That part needs a model call (build.py --local-only) and is reported apart.
"""
import copy, json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
sys.path.insert(0, str(ROOT / "tests"))
import toolspec, spec_extract, components, lint
from negotiation_harness import check, FAILS

NEW_API = str(ROOT / "experiments" / "api-rename" / "openapi.json")
ts_new = toolspec.load(NEW_API)
pol = json.load(open(ROOT / "tests" / "fixtures" / "policy-a.json", encoding="utf-8"))

probs = spec_extract.validate(pol, ts_new)
check("R1 a binding to the old names is rejected against the renamed API (answer, wrong_answers_left, past_due)",
      any("'answer'" in p for p in probs) and any("'wrong_answers_left'" in p for p in probs) and any("'past_due'" in p for p in probs), probs)

fx = copy.deepcopy(pol)                       # fixture: what a correct extraction must produce for the renamed API
fx["api_binding"]["verify"]["answer_param"] = "value"
fx["api_binding"]["verify"]["remaining"] = "tries_left"
fx["api_binding"]["account"]["past_due"] = "overdue_amount"
check("R2 the fixture binding validates against the renamed API", spec_extract.validate(fx, ts_new) == [], spec_extract.validate(fx, ts_new))
wf = components.build(fx, ts_new)
errs = [p for p in lint.lint(wf, NEW_API) if not p.startswith("warn:")]
check("R3 the generated workflow lints against the renamed API", not errs, errs)
s = json.dumps(wf)
vt = wf["nodes"]["id_verify"]["pre_actions"][0]["function"]["parameters"]["properties"]["body"]["properties"]
check("R4 verify_identity sends 'value', not 'answer'", "value" in vt and "answer" not in vt, list(vt))
check("R5 the identity post-hook reads 'tries_left'; the deal code reads 'overdue_amount'",
      '"remaining": "tries_left"' in s.replace("\\n", "\n").replace('\\"', '"') and '"past_due": "overdue_amount"' in s.replace('\\"', '"'), "")
# an old name may only appear as the runtime's own concept key (e.g. "past_due": "overdue_amount"), never as a bound value
flat = s.replace('\\"', '"')
old = sorted(set(re.findall(r':\s*"(past_due|answer|wrong_answers_left)"', flat))) + (["wrong_answers_left"] if "wrong_answers_left" in flat else [])
check("R6 none of the old field names is bound as a value anywhere in the workflow", not old, old)
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

# Generalisation experiments

Status (cloud session, 11 Oct): see the "Status" lines under each experiment.

Both use the builder unchanged. Neither may lead to editing the builder with values from these inputs.

## 1. Raw memo that changes one rule — `memo-late-deadline/`

Input: `brief-a-memo.md` = Brief A + a dated memo that changes only the late-band deadline (rule 18: 7th → 5th business day).

Run (one Opus extraction call; publishes slot `exp-memo`; then 2 customers × 3 runs):
```
python3 builder/build.py experiments/memo-late-deadline/brief-a-memo.md tools/openapi.json --slot exp-memo --mode main --practice PUB-04
python3 tools/run_cases.py <agent_id printed by the build> --cases experiments/memo-late-deadline/cases.json --reps 3
```

Success (all must hold):
- Static (candidate `policy.json`): band 8–45 has `deadline_business_days` = 5, band 1–7 still 12; `amendments` records the change, its scope (late band) and the replaced provision (rule 18 late row); no `unresolved_conflicts` about it; trace shows the amendment line.
- Static (candidate `workflow.json`): the deal and negotiation code configs carry 5 for the late band; 7 does not appear for that band.
- Live: PUB-04 (14 days late, wants 6 Nov) → promise 1250 on **2026-10-21** (hand count from Wed 14 Oct: 15, 16, 19, 20, 21), 3/3; PUB-10 (control, unchanged expectation, Friday 16 Oct) 3/3.
- Failure modes to report separately: memo ignored (23 Oct recorded), memo over-applied (early band changed), extraction marks a conflict instead of applying the scoped change.
- Status: expected date re-derived independently of the runtime: now Wed 14 Oct 2026; business days after today 15 (1), 16 (2), 19 (3), 20 (4), 21 (5) -> 2026-10-21 (the 26 Oct holiday is outside the window). PUB-10 (8 days late = late band) keeps 16 Oct, inside both the old (23 Oct) and the new (21 Oct) deadline, so it is a valid control. Build and live runs: see research/cloud-progress.md.

## 2. Renamed API fields — `api-rename/`

Input: `openapi.json` = the kit API with `verify_identity` request `answer` → `value`, response `wrong_answers_left` → `tries_left`, and `get_account` item `past_due` → `overdue_amount`.

Run LOCAL ONLY (one Opus extraction call; no Freya call — the practice bank still expects the old names, so a live run would fail for a reason unrelated to the builder):
```
python3 builder/build.py briefs/brief-a.md experiments/api-rename/openapi.json --slot exp-api --mode main --local-only
```

Success (all must hold, local evidence only):
- `spec_extract.validate` passes: `api_binding.verify.answer_param` = `value`, `verify.remaining` = `tries_left`, `account.past_due` = `overdue_amount`.
- Generated workflow: the verify tool body field is `value`; the identity post-hook config uses `tries_left`; the deal code config uses `overdue_amount`; none of `answer`, `wrong_answers_left`, `past_due` is bound anywhere (search the JSON).
- `lint` against `experiments/api-rename/openapi.json` reports no error.
- Report it as "schema binding verified locally", never as an end-to-end pass.
- Status: the deterministic half runs without a model in `tests/test_api_binding.py` (R1: the old binding is rejected
  by `spec_extract.validate` against the renamed API, so a build goes to its bounded repair call; R2-R6: with a binding
  to the new names, written as a TEST FIXTURE, the generator binds only those names and lints clean; negative control:
  the old binding is detected). 6/6 pass. This does NOT show that the extraction step finds the new names; that needs the
  `--local-only` build above (one model call), reported separately in research/cloud-progress.md.

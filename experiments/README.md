# Generalisation experiments (prepared, NOT run yet)

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

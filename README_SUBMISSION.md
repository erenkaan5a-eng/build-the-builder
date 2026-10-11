# Build the Builder — submission and rerun guide

## What is submitted per hidden brief
1. The exported phone agent: `submission/hidden-N.workflow.json` (written by the builder only when its release checks pass; otherwise the export stays in the candidate folder, see below).
2. The run's trace: `traces/hidden-N.log` (the `tee` of the run) plus the builder's own trace `traces/<slot>-<time>.log`.
3. The builder code at the submitted commit (this repository).

## Setup with your own credentials
- Python 3.10 or newer (developed on 3.14.3, Windows).
- `pip install claude-agent-sdk` (developed with 0.2.165).
- Claude access for the builder's model calls: a logged-in Claude Code (`claude login`), or `CLAUDE_CODE_OAUTH_TOKEN`, or `ANTHROPIC_API_KEY` in the environment. The builder makes 1 call (policy extraction, model `claude-opus-5-5`, override with `EXTRACT_MODEL`) and up to 1 repair call; the fallback path (only if the main path fails) runs an agent with `claude-sonnet-5-5` (`FALLBACK_MODEL`).
- `cp env.example env.sh` and fill `FREYA_API_KEY` and `FREYA_BANK_TEAM_KEY` (ASCII only). `env.sh` is read by the builder itself and is git-ignored.
- Cloud session whose proxy injects the credentials (Network secrets: `Authorization: Bearer` for staging-app.freyavoice.ai, `x-team-key` for freya-bank-mock.freyavoice.workers.dev): set `FREYA_AUTH_VIA_PROXY=1` and leave the two keys unset. The builder and `tools/run_cases_cloud.py` then send those requests without the header and the proxy adds it (`tools/cloud_proxy.py`; the kit's `freya.py` and `tools/score.py` are not modified). Without the variable nothing changes. The trace logs only whether each key is set.

## Final form (case folder + mock URL)
```
scripts/run_final.sh <case_folder> <mock_url> [--contract FILE]
# = python3 builder/build.py <case_folder> <mock_url> --slot final-<folder> with set -o pipefail and a timestamped terminal log
python3 scripts/make_submission.py candidates/final-<folder>/<time> --team "<team>" --member "<name>" --repo <url> --mock-url <mock_url>
```
See research/final-hazirlik.md (what is ready, missing, and needs access) and workers/bank-mock/README.md.

## Single entry point
```
python3 builder/build.py {brief_path} {tool_api_path} --out submission/hidden-N.workflow.json 2>&1 | tee traces/hidden-N.log
```
- The slot (the Freya workflow that is created once and then updated in place) defaults to the brief file name.
- `--mode auto` (default): main path (policy extraction → fixed components → workflow), fallback agent only if the main path fails.
- One wall-clock budget of 30 minutes (`--budget-min`) covers extraction, repair, fallback, validation, publish, behaviour tests and export.
- Do not pass `--practice` in the final: it drives a public practice customer and exists for development only.
- Do not pass `--reuse-policy` in the final: it skips the extraction and republishes from the policy of an earlier traced run of the same inputs (development only, e.g. after a platform 5xx; the trace says so).

## What a run leaves behind
- `candidates/<slot>/<time>/`: `policy.raw.json`, `policy.json`, `workflow.json`, `support_boundary.json`, `export.json`, `manifest.json` (workflow/agent id, published version, tested and exported content hash, behaviour checks, known rule gaps, what is enforced by code vs left to the dialogue model, build seconds, model calls).
- `traces/<slot>-<time>.log`: start/end, every model call (model + purpose + token usage), created/updated Freya objects, tests, fallback decisions, known gaps.
- The final line says `release checks PASSED` or `FAILED`. PASSED means: lint + Freya dry-run, behaviour checks on the published version, tested content hash == exported content hash. It does not mean policy correctness.
- If the checks fail, `--out` is left unchanged; inspect the candidate folder and its manifest before deciding anything.

## Local checks (no network)
```
python3 tests/test_negotiation.py
python3 tests/test_negotiation_regress.py
python3 tests/test_date_tool.py
python3 tests/test_generator_structure.py
python3 tests/test_api_binding.py
python3 tests/test_identity.py      # identity stage run by code (both engine modes of the result keys)
python3 tests/test_support.py       # support offer answered by code, model answer guard, 'go on'
python3 builder/lint.py <workflow.json> <tool_api.json>
```

## When the release behaviour check could not run
A platform 5xx on the chat API during the build makes the release checks FAIL (the export is kept in the candidate
folder). Re-run only the behaviour checks on the same published version, without rebuilding or changing it:
```
python3 eval/recheck_release.py candidates/<slot>/<time>
```
It refuses to check when the live workflow's hash differs from the exported one and writes `recheck-<time>.json`
next to the manifest (the manifest itself is not edited).

## A brief that builds on another (development: Brief B)
Brief B says it builds on Brief A; the development A+B candidate was built from the plain concatenation
`{ cat briefs/brief-a.md; echo; cat briefs/brief-b.md; } > out/brief-ab.md` (no manual edit).

## Contest rules kept by the builder
- The phone agent model is the one in `freya.py`; the builder never changes it.
- The phone agent calls only the supplied tool API (lint rejects any other URL).
- Bank values, names and rules come from the brief and its tool API at run time; nothing from a final brief is written into the builder.

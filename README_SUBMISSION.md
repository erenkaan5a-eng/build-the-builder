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

## Single entry point
```
python3 builder/build.py {brief_path} {tool_api_path} --out submission/hidden-N.workflow.json 2>&1 | tee traces/hidden-N.log
```
- The slot (the Freya workflow that is created once and then updated in place) defaults to the brief file name.
- `--mode auto` (default): main path (policy extraction → fixed components → workflow), fallback agent only if the main path fails.
- One wall-clock budget of 30 minutes (`--budget-min`) covers extraction, repair, fallback, validation, publish, behaviour tests and export.
- Do not pass `--practice` in the final: it drives a public practice customer and exists for development only.

## What a run leaves behind
- `candidates/<slot>/<time>/`: `policy.raw.json`, `policy.json`, `workflow.json`, `export.json`, `manifest.json` (workflow/agent id, published version, tested and exported content hash, behaviour checks, known rule gaps, build seconds, model calls).
- `traces/<slot>-<time>.log`: start/end, every model call (model + purpose + token usage), created/updated Freya objects, tests, fallback decisions, known gaps.
- The final line says `release checks PASSED` or `FAILED`. PASSED means: lint + Freya dry-run, behaviour checks on the published version, tested content hash == exported content hash. It does not mean policy correctness.
- If the checks fail, `--out` is left unchanged; inspect the candidate folder and its manifest before deciding anything.

## Local checks (no network)
```
python3 tests/test_negotiation.py
python3 tests/test_negotiation_regress.py
python3 tests/test_date_tool.py
python3 tests/test_generator_structure.py
python3 builder/lint.py <workflow.json> <tool_api.json>
```

## Contest rules kept by the builder
- The phone agent model is the one in `freya.py`; the builder never changes it.
- The phone agent calls only the supplied tool API (lint rejects any other URL).
- Bank values, names and rules come from the brief and its tool API at run time; nothing from a final brief is written into the builder.

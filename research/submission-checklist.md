# Final submission checklist (local; prepared 11 Oct 2026)

Per hidden brief N (run once each, no manual step, no edit of the agent afterwards):
- [ ] `python3 builder/build.py <brief> <tool_api> --out submission/hidden-N.workflow.json 2>&1 | tee traces/hidden-N.log`
- [ ] Last trace line says `release checks PASSED`; if FAILED: `submission/hidden-N.workflow.json` was NOT written — decide from `candidates/<slot>/<time>/manifest.json` (a bug fix + rerun is allowed; no brief values in the builder).
- [ ] `manifest.json`: workflow_id, agent_id, published version, tested_hash == exported_hash, behaviour checks all true, `known_gaps` read.
- [ ] Build time well under 30 min (the trace has it; tie-break uses it).
- [ ] Both traces kept: `traces/hidden-N.log` and `traces/<slot>-<time>.log`.

Repository:
- [ ] `git status` clean of secrets: env.sh is git-ignored; secret scan (exact values + `fak_` pattern) = 0 hits (last check: 183 files, 0 hits).
- [ ] Commit the builder code + submission files + traces (only when the user decides to commit/push).
- [ ] `README_SUBMISSION.md` matches the command actually used.

Done locally on 11 Oct (no API): clean copy of the 183 committed-to-be files → 4 test suites 0 failures, `build.py --help` OK.
NOT done: a clean-copy build against Freya (needs keys and a model call), organizer-side rerun.

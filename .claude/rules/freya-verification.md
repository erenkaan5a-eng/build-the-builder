# Freya generation, evaluation and delivery

## Policy and API correctness
- Keep source references for extracted rules, exceptions and precedence. Every material rule needs an implementation location and verification status.
- Unsupported computational/structural rules must not silently become prompt-only instructions. Use bounded repair or automatic fallback within the same deadline. Record remaining gaps; do not label an incomplete candidate verified.
- Parse the supplied OpenAPI and bind semantic concepts to its request/response fields. Do not assume current ok, data paths, identity fields or enum names remain unchanged. Distinguish platform response envelopes from bank payloads.
- Runtime may derive counters from observed events and the brief; it must never invent missing bank success or identity-verification evidence.
- Separate proposed, explicitly confirmed and successfully recorded actions. Bind confirmation to the exact product/amount/date proposal; corrections invalidate the affected confirmation.
- Keep per-product state separate. Compute dates using the call's now and supplied calendar. Take product IDs and account facts from tool results. Derive retry, note, transfer and closure rules from the current brief.
- Never turn an exception into a fabricated amount, date, successful verification or successful write. Missing/failed computation must remain visible and follow a policy-compatible recovery path.
- Do not strengthen a skill's platform assumptions into universal facts: boolean types, null legality, hook behavior and routing must be checked against docs and small reproducible examples. A linter rejecting the starter does not prove the starter is wrong.
- A tool restricted to a node still requires correct entry conditions and fresh parameters. Prompt instructions and static reachability do not prove runtime enforcement or exactly-once execution.

## Evaluation integrity
- Separate development evaluation from autonomous final-condition builds. Public cases may evaluate a completed practice build externally; do not assume hidden practice customers exist.
- Use small targeted runs during iteration; use three repeats per case for final reliability claims. Preserve losses and denominator; do not report single-run success as pass^3.
- Keep repeated sessions isolated with unique result/session associations. If batching repetitions, verify the runner cannot overwrite cases or mix bank ledgers.
- Keep brief, persona script, actual call variables, expected ledger and judge checks consistent. Verify now overrides reach the call. Local mocks/schema tests are not live end-to-end proof.
- Expected outputs must not come solely from the production runtime under test. Use source rules and independently checked examples. Never weaken a test to make a wrong agent pass.
- Classify reproducible failure, variable outcomes, suspected platform failure and judge uncertainty separately. Slow responses alone do not prove the platform is responsible. Preserve original and rerun evidence.
- A dataset used for model/architecture selection is development data. Keep the sealed final hold-out unavailable to the development assistant; the builder may read its brief during the planned evaluation, not its expected answers.
- Store call IDs, scenario/style/now, workflow version when available, elapsed time and failure reasons. Report unmeasured usage as unavailable, not zero.

## Release checks
- After the last mutation: validate -> publish -> test that published candidate -> export. Any subsequent change invalidates earlier release verification.
- Record workflow/agent IDs, available published/test version metadata and a canonical workflow-content hash. export_workflow does not currently add a top-level version field; do not require an invented field.
- Compare equivalent normalized workflow content, excluding only understood volatile metadata; never strip behavior-affecting differences. Distinguish content evidence from execution-version evidence and report missing evidence honestly.
- Trace every run's start/end, each model call's model and short purpose, created/updated objects, tests, fallback decisions and known gaps. Exclude credentials and private reasoning; concise action summaries suffice.
- Keep each brief/run's output distinct and preserve earlier valid candidates. Export a candidate file; do not submit/publish a repository externally unless the user has authorized that action.
- Verify a clean setup and documented single entry point with organizer-owned credentials. A deadline or failed fallback is not grounds to fabricate a pass or hide a known rule gap.

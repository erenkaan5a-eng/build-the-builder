# Final bank mock (Cloudflare Workers) — skeleton

Prepared before the final package opens. It holds no final rule, value or name. The final mock is written FROM the
package's service contract and test customers (a task the organiser asks for separately from the builder); the builder
then reads the same contract and binds the agent's tools to this mock's URL.

## What is generic (ready)
- `src/core.js`: operations read from the contract (`contract.json`); request validation from its schemas (required,
  type, enum, pattern, date format, min/max); routing; every call recorded in the customer's ledger, including refused
  (400) and not implemented (501) calls; an unknown route is 404. No blanket success.
- `src/index.js`: Worker entry; one Durable Object per customer key (consistent read-after-write).
- `test/core.test.mjs`: `node --test workers/bank-mock/test/core.test.mjs` (4 tests, no network).

## What is written after the package opens (from its documents, not guessed now)
1. `contract.json` = the package's service contract (OpenAPI JSON). If it is not machine readable, write it from the
   contract document and keep the source mapping.
2. `customers.json` = the package's test customers; `config.json` `customer_key_field` = the contract's customer field.
3. `src/handlers.js`: one handler per operation: checks, state changes, recorded results, the contract's error answers
   and error injection the test customers describe; the ledger read route the contract or the README defines (and its auth).
4. Node tests per handler from the contract's examples before deploying.

## Deploy (needs your Cloudflare access; nothing secret goes into this repository)
- One command: `scripts/deploy_mock.sh` (offline tests -> every contract operation has a handler -> credentials present?
  -> `wrangler@3.114.17 deploy` -> smoke request (unknown route must be 404) -> `traces/mock-deploy-<time>.{log,json}`
  with mock_url, commit and contract/customers hashes). `--dry-run` bundles only (checked 11 Oct: 6.6 KiB, Durable
  Object binding present). The placeholder contract (no operations) is refused.
- Checked locally with `wrangler dev` and a synthetic contract (scratch copy, not committed): per-customer state kept
  across requests, schema violation -> 400, unknown route -> 404.
- Access, option A (this cloud session): the environment's network policy must allow `api.cloudflare.com`; a Workers
  API token (Cloudflare template "Edit Cloudflare Workers") and the account id set as `CLOUDFLARE_API_TOKEN` and
  `CLOUDFLARE_ACCOUNT_ID` in the environment's secret settings. Environment secrets reach a NEW session, not this one.
- Access, option B (your machine): `git pull`, `cd workers/bank-mock && npx wrangler@3.114.17 login && cd ../.. &&
  scripts/deploy_mock.sh`; then commit the `traces/mock-deploy-*.json` record.
- Before the first deploy: open Workers & Pages once in the dashboard so the account has a `workers.dev` subdomain
  (free). Token for option A: dashboard → My Profile → API Tokens → Create Token → template "Edit Cloudflare Workers"
  (account: Workers Scripts Edit; Account Settings Read; user: Memberships Read, User Details Read), limited to
  your account. Account ID: Workers & Pages overview, right column. Option B needs no token (browser login).
- The script runs on Linux and macOS (bash, node >= 18, npx).
- Windows (PowerShell): the script needs Git Bash, not WSL's `bash`. Check in PowerShell:
  `Test-Path "$env:ProgramFiles\Git\bin\bash.exe"; node --version; npx.cmd --version; git --version`.
  Run it with Git Bash's full path from the repository root:
  `& "$env:ProgramFiles\Git\bin\bash.exe" scripts/deploy_mock.sh --dry-run --allow-missing-handlers`.
  Login can be done in PowerShell: `cd workers\bank-mock; npx.cmd wrangler@3.114.17 login; npx.cmd wrangler@3.114.17 whoami`
  (`npx.cmd` avoids the execution-policy block on `npx.ps1`). `.gitattributes` keeps `*.sh` in LF. If Git Bash still
  reports `$'\r': command not found` (a copy checked out before that file existed), rewrite the scripts from the
  repository: `git checkout-index -f scripts/deploy_mock.sh scripts/run_final.sh`.
- Never put a token in a file or the chat. Keep the mock deployed until the results are announced. Free plan only.

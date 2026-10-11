# Final bank mock: Freya Bank statement-debt services (Cloudflare Workers)

Our mock of the bank's test environment, written from the final package (receipt `final/package/r3-20261011-2058/`):
`sources/documents/2026-10-01-service-contract.md` (sections 1-6) and `test-environment/test-customers.md`. It is the
mock the final asks for; it is not part of the builder.

- `src/service.js`: the seven services, `POST /voice/v1/<service>` (`cards.list`, `cards.balance`, `statement.week.get`,
  `statement.week.decide`, `statement.week.change`, `contact.email.get`, `statement.pdf.send`), request envelope
  `{data, call}`; lookup by `customerNo` / masked `cardNumber` / `cardNumber` + `newStatementWeek` as in test-customers.md;
  the stored status and body are returned exactly (`delaySeconds` = wait, not sent). Not in the data: the service's 404 from
  contract section 4, else 400 `INVALID_ARGUMENTS_ERROR`; missing/empty required field: 400 naming it. Nothing made up.
- `src/index.js`: Worker entry; also `POST /oauth2/token` (section 2; the token is not checked in test) and `GET /health`.
- `data/test-customers.json`: byte copy of the package's file (checked by the deploy script). Stateless, no storage
  (the organiser's README pattern: the data table inside the Worker).
- Tests: `node --test workers/bank-mock/test/statement.test.mjs` (every stored answer replayed, 404/400 cases, string/number
  equivalence, current week has no preview, masked-number lookup, required fields, contract examples, delay).
  `node workers/bank-mock/scripts/verify.mjs <url>` replays everything over HTTP (local `wrangler dev`: 617 answers +
  8 not-found/invalid + health + unknown path, 0 mismatches).
- `src/core.js`, `src/handlers.js`, `contract.json`, `customers.json`, `config.json`: the pre-final generic skeleton, not
  used by this Worker.

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

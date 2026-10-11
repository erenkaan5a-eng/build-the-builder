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
- The cloud session's network policy must allow `api.cloudflare.com` (and the package registry for `npx wrangler`).
- Login: `npx wrangler@3 login` (browser) or the environment variables `CLOUDFLARE_API_TOKEN` and
  `CLOUDFLARE_ACCOUNT_ID` set in the environment's secret settings — never in a file or the chat.
- `cd workers/bank-mock && npx wrangler@3 deploy` → prints the `https://<name>.<subdomain>.workers.dev` URL = `mock_url`.
- Keep it deployed until the results are announced. Free plan only; no paid service.

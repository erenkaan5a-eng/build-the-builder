#!/usr/bin/env bash
# Deploy the final bank mock (workers/bank-mock) to Cloudflare Workers and record its URL (= mock_url).
#   scripts/deploy_mock.sh [--dry-run] [--allow-missing-handlers]
# Needs (deploy only): network access to api.cloudflare.com and either CLOUDFLARE_API_TOKEN (+ CLOUDFLARE_ACCOUNT_ID)
# in the environment or an earlier `npx wrangler login`. Nothing secret is printed or written: presence only.
# Free plan only (Workers + SQLite Durable Objects). Every run writes its own traces/mock-deploy-<time>.{log,json}.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
W="$ROOT/workers/bank-mock"
WRANGLER="wrangler@3.114.17"
DRY=0; ALLOW=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --allow-missing-handlers) ALLOW=1 ;;
    *) echo "unknown option $a" >&2; exit 2 ;;
  esac
done
stamp="$(date -u +%Y%m%d-%H%M%S)"
log="$ROOT/traces/mock-deploy-$stamp.log"; n=1
while [ -e "$log" ]; do n=$((n+1)); log="$ROOT/traces/mock-deploy-$stamp-$n.log"; done
mkdir -p "$ROOT/traces"
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$log"; }
# sha256sum on Linux, shasum on macOS
sha16() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -c1-16; }

say "START mock deploy (dry_run=$DRY) commit $(git -C "$ROOT" rev-parse HEAD)"
if [ -n "$(git -C "$ROOT" status --porcelain -- workers/bank-mock)" ]; then
  say "NOTE workers/bank-mock has uncommitted changes: commit them so the deployed mock is reproducible"
fi
say "contract sha256 $(sha16 "$W/contract.json"), customers sha256 $(sha16 "$W/customers.json")"

# 1. offline tests of the generic core and of the handlers
node --test "$W"/test/*.test.mjs 2>&1 | tee -a "$log" | grep -E "^# (pass|fail)" || true
if node --test "$W"/test/*.test.mjs > /dev/null 2>&1; then say "tests: pass"; else say "tests: FAIL (see above)"; exit 1; fi

# 2. every contract operation has a handler (else it answers 501), and the contract has operations at all
missing="$(cd "$W" && node --input-type=module -e '
import { readFileSync } from "node:fs";
import { opsOf } from "./src/core.js";
import { handlers } from "./src/handlers.js";
const ops = Object.values(opsOf(JSON.parse(readFileSync("contract.json", "utf8"))));
if (!ops.length) { console.log("(the contract has no operations)"); process.exit(0); }
console.log(ops.filter((o) => !handlers[o.name]).map((o) => o.name).join(" "));
')"
if [ -n "$missing" ]; then
  say "operations without a handler (answer 501): $missing"
  [ "$ALLOW" = 1 ] || { say "STOP: write their handlers first (or --allow-missing-handlers)"; exit 1; }
fi

# 3. credentials: presence only
for v in CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
  if [ -n "${!v:-}" ]; then say "$v: present"; else say "$v: absent"; fi
done

export WRANGLER_SEND_METRICS=false
if [ "$DRY" = 1 ]; then
  out="$(mktemp -d)"
  (cd "$W" && npx --yes "$WRANGLER" deploy --dry-run --outdir "$out") 2>&1 | grep -E "Total Upload|bindings|CUSTOMER_STATE|error|ERROR" | tee -a "$log" || true
  say "END dry run: bundled into $out, nothing deployed"
  exit 0
fi

# 4. deploy and take the URL from wrangler's output
set +e
(cd "$W" && npx --yes "$WRANGLER" deploy) 2>&1 | tee -a "$log"
rc=${PIPESTATUS[0]}
set -e
[ "$rc" = 0 ] || { say "END deploy failed (exit $rc): nothing to record"; exit "$rc"; }
url="$(grep -oE 'https://[A-Za-z0-9.-]+\.workers\.dev' "$log" | tail -1 || true)"
[ -n "$url" ] || { say "END deployed, but no workers.dev URL in the output: read it from the Cloudflare dashboard"; exit 1; }

# 5. smoke: an unknown route must be a 404 JSON answer from this mock (not a blanket success)
code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$url/__no_such_operation__" -H 'content-type: application/json' -d '{}' || true)"
say "smoke: POST $url/__no_such_operation__ -> $code (expected 404)"
cat > "${log%.log}.json" <<EOF
{"mock_url": "$url", "commit": "$(git -C "$ROOT" rev-parse HEAD)", "deployed_at": "$(date -u +%FT%TZ)",
 "contract_sha256_16": "$(sha16 "$W/contract.json")", "customers_sha256_16": "$(sha16 "$W/customers.json")",
 "smoke_unknown_route_status": "$code"}
EOF
say "END mock_url=$url (record: ${log%.log}.json). Keep it deployed until the results are announced."

#!/usr/bin/env bash
# Deploy the final bank mock (workers/bank-mock) to Cloudflare Workers and record its URL (= mock_url).
#   scripts/deploy_mock.sh [--dry-run]
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
# Windows: run this from Git Bash (not WSL's bash, which has no Windows node): node and npx must be on PATH
for c in node npx git curl; do
  command -v "$c" >/dev/null 2>&1 || { say "STOP: '$c' not found in this shell (on Windows use Git Bash with Node.js installed)"; exit 1; }
done
say "shell $(uname -s), node $(node --version)"
if [ -n "$(git -C "$ROOT" status --porcelain -- workers/bank-mock)" ]; then
  say "NOTE workers/bank-mock has uncommitted changes: commit them so the deployed mock is reproducible"
fi
say "test data sha256 $(sha16 "$W/data/test-customers.json") (the final package's test-environment/test-customers.json, bundled in the Worker)"

# 1. offline tests of the generic core and of the handlers
node --test "$W"/test/*.test.mjs 2>&1 | tee -a "$log" | grep -E "^# (pass|fail)" || true
if node --test "$W"/test/*.test.mjs > /dev/null 2>&1; then say "tests: pass"; else say "tests: FAIL (see above)"; exit 1; fi

# 2. the bundled test data is byte-identical to the current package receipt's test-environment/test-customers.json
cur="$(sed -n 's/.*`\(r[0-9]*-[0-9-]*\)\/`.*/\1/p' "$ROOT/final/package/CURRENT.md" | head -1)"
pkgdata="$ROOT/final/package/$cur/test-environment/test-customers.json"
if [ -n "$cur" ] && [ -f "$pkgdata" ]; then
  if cmp -s "$pkgdata" "$W/data/test-customers.json"; then say "test data = package $cur (byte-identical)"; else say "STOP: bundled test data differs from package $cur"; exit 1; fi
else
  say "NOTE no current package receipt with test data found; bundled data not compared"
fi

# 3. credentials: presence only
for v in CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
  if [ -n "${!v:-}" ]; then say "$v: present"; else say "$v: absent"; fi
done

export WRANGLER_SEND_METRICS=false
if [ "$DRY" = 1 ]; then
  out="$(mktemp -d)"
  (cd "$W" && npx --yes "$WRANGLER" deploy --dry-run --outdir "$out") 2>&1 | grep -E "Total Upload|bindings|error|ERROR" | tee -a "$log" || true
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

# 5. every stored answer over the deployed URL (same status, same body), not-found/invalid cases, health, unknown path
set +e
node "$W/scripts/verify.mjs" "$url" 2>&1 | tee -a "$log"
vrc=${PIPESTATUS[0]}
set -e
verdict="$([ "$vrc" = 0 ] && echo pass || echo FAIL)"
say "verify against $url: $verdict"
cat > "${log%.log}.json" <<EOF
{"mock_url": "$url", "commit": "$(git -C "$ROOT" rev-parse HEAD)", "deployed_at": "$(date -u +%FT%TZ)",
 "test_data_sha256_16": "$(sha16 "$W/data/test-customers.json")", "package_receipt": "$cur", "verify": "$verdict"}
EOF
say "END mock_url=$url verify=$verdict (record: ${log%.log}.json). Keep it deployed until the results are announced."
[ "$vrc" = 0 ] || exit 1

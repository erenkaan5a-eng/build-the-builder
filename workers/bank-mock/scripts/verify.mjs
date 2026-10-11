// Replay the final package's test answers against a running mock over HTTP (local `wrangler dev` or the deployed URL).
//   node workers/bank-mock/scripts/verify.mjs <base url> [--skip-delay]
// Every stored answer: POST <base>/voice/v1/<service> with the contract's envelope -> same status, same body.
// Plus: unknown customer/card -> the contract's 404/400, GET /health, an unknown path -> 404. Exit 1 on any mismatch.
import { readFileSync } from "node:fs";

const base = (process.argv[2] || "").replace(/\/+$/, "");
const skipDelay = process.argv.includes("--skip-delay");
if (!/^https?:\/\//.test(base)) { console.error("usage: verify.mjs <base url> [--skip-delay]"); process.exit(2); }
const DATA = JSON.parse(readFileSync(new URL("../data/test-customers.json", import.meta.url), "utf8"));

const jobs = [];
for (const c of DATA.customers) {
  for (const [svc, v] of Object.entries(c.services)) {
    const flat = { customerNo: c.customerNo, aiFlow: "CardOps", intAddressInfoType: "E", cardNumber: "540000******0000",
                   currencyType: "TL", statementDate: "05.10.2026", emailAddress: "x@freyabank.example" };
    if ("http" in v) jobs.push({ svc, data: flat, entry: v });
    else for (const [card, w] of Object.entries(v)) {
      if ("http" in w) jobs.push({ svc, data: { cardNumber: card }, entry: w });
      else for (const [week, e] of Object.entries(w)) jobs.push({ svc, data: { cardNumber: card, newStatementWeek: week, statementDay: 5 }, entry: e });
    }
  }
}
const negatives = [
  ["cards.list", { customerNo: "11111111" }, 404, "FB_IVR_CHANNEL_102"],
  ["cards.balance", { cardNumber: "540000******9999" }, 404, "FB_IVR_CHANNEL_120"],
  ["statement.week.get", { cardNumber: "540000******9999" }, 404, "FB_IVR_CHANNEL_121"],
  ["statement.week.decide", { cardNumber: "540000******9999", newStatementWeek: 2, statementDay: 5 }, 400, "INVALID_ARGUMENTS_ERROR"],
  ["statement.week.change", { cardNumber: "540000******9999", newStatementWeek: 2, statementDay: 5 }, 400, "INVALID_ARGUMENTS_ERROR"],
  ["contact.email.get", { customerNo: "11111111", intAddressInfoType: "E" }, 400, "INVALID_ARGUMENTS_ERROR"],
  ["statement.pdf.send", { customerNo: "11111111", cardNumber: "x", currencyType: "TL", statementDate: "05.10.2026", emailAddress: "a@b.example" }, 404, "FB_IVR_CHANNEL_107"],
  ["cards.balance", { cardNumber: "" }, 400, "INVALID_ARGUMENTS_ERROR"],
];

const canon = (x) => JSON.stringify(x, (k, v) => (v && typeof v === "object" && !Array.isArray(v) ? Object.fromEntries(Object.entries(v).sort()) : v));
async function post(svc, data) {
  const res = await fetch(`${base}/voice/v1/${svc}`, { method: "POST", headers: { "content-type": "application/json", accept: "application/json" },
                                                       body: JSON.stringify({ data, call: { ani: "05000000000", lang: "tr" } }) });
  return { status: res.status, body: await res.json().catch(() => null) };
}

let bad = 0, done = 0;
const t0 = Date.now();
const todo = jobs.filter((j) => !(skipDelay && j.entry.delaySeconds));
async function worker() {
  while (todo.length) {
    const j = todo.shift();
    const got = await post(j.svc, j.data);
    done++;
    if (got.status !== j.entry.http || canon(got.body) !== canon(j.entry.response)) {
      bad++; console.log(`MISMATCH ${j.svc} ${JSON.stringify(j.data)}: got ${got.status} ${JSON.stringify(got.body).slice(0, 200)}`);
    }
  }
}
await Promise.all(Array.from({ length: 6 }, worker));
for (const [svc, data, http, code] of negatives) {
  const got = await post(svc, data);
  if (got.status !== http || got.body?.result?.code !== code || "data" in (got.body || {})) {
    bad++; console.log(`MISMATCH negative ${svc}: got ${got.status} ${JSON.stringify(got.body).slice(0, 200)}`);
  }
}
const health = await fetch(`${base}/health`);
if (health.status !== 200) { bad++; console.log(`MISMATCH GET /health -> ${health.status}`); }
const unknown = await fetch(`${base}/voice/v1/no.such.service`, { method: "POST", body: "{}" });
if (unknown.status !== 404) { bad++; console.log(`MISMATCH unknown service -> ${unknown.status}`); }
console.log(`verify ${base}: ${done} stored answers${skipDelay ? " (delayed one skipped)" : ""} + ${negatives.length} not-found/invalid + health + unknown path; `
            + `${bad} mismatch(es); ${((Date.now() - t0) / 1000).toFixed(0)} s`);
process.exit(bad ? 1 : 0);

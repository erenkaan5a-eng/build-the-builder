// Cloudflare Worker entry of the final bank mock. Per-customer state lives in one Durable Object per customer_id
// (strongly consistent: a ledger read right after a write sees it). Contract, customers and handlers are bundled files.
import contract from "../contract.json";
import customers from "../customers.json";
import config from "../config.json";
import { handlers } from "./handlers.js";
import { handle } from "./core.js";

export class CustomerState {
  constructor(state) { this.storage = state.storage; }
  async fetch(request) {
    const { op, key, value } = await request.json();
    if (op === "get") return Response.json((await this.storage.get(key)) ?? null);
    await this.storage.put(key, value);
    return Response.json({ ok: true });
  }
}

function doStore(env) {
  const stub = (k) => env.CUSTOMER_STATE.get(env.CUSTOMER_STATE.idFromName(String(k)));
  return {
    async get(k) { return (await stub(k).fetch("https://do/", { method: "POST", body: JSON.stringify({ op: "get", key: "s" }) })).json(); },
    async put(k, v) { await stub(k).fetch("https://do/", { method: "POST", body: JSON.stringify({ op: "put", key: "s", value: v }) }); },
  };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let body = {};
    if (request.method !== "GET") {
      try { body = await request.json(); } catch { return Response.json({ ok: false, error: "invalid JSON body" }, { status: 400 }); }
    }
    const r = await handle({ method: request.method, path: url.pathname, body, contract, handlers, store: doStore(env), customers,
                             now: new Date().toISOString(), keyField: config.customer_key_field || null });
    return Response.json(r.json, { status: r.status });
  },
};

// node --test workers/bank-mock/test/core.test.mjs   (no network, no Cloudflare)
import test from "node:test";
import assert from "node:assert/strict";
import { handle, validate, opsOf, MemoryStore } from "../src/core.js";

const contract = { openapi: "3.0.0", paths: {
  "/lookup": { post: { operationId: "lookup", requestBody: { content: { "application/json": { schema: {
    type: "object", required: ["cid", "kind"], properties: { cid: { type: "string" }, kind: { type: "string", enum: ["a", "b"] }, amount: { type: "number", minimum: 1 },
      day: { type: "string", format: "date" } } } } } } } },
  "/other": { post: { operationId: "other" } } } };

test("operations are read from the contract", () => {
  assert.deepEqual(Object.keys(opsOf(contract)).sort(), ["POST /lookup", "POST /other"]);
});

test("validation: required, enum, type, minimum, date format", () => {
  const s = opsOf(contract)["POST /lookup"].schema;
  assert.deepEqual(validate(s, { cid: "x", kind: "a" }), []);
  assert.ok(validate(s, { kind: "a" }).some((e) => e.includes("cid is required")));
  assert.ok(validate(s, { cid: "x", kind: "z" }).some((e) => e.includes("one of")));
  assert.ok(validate(s, { cid: "x", kind: "a", amount: "5" }).some((e) => e.includes("number")));
  assert.ok(validate(s, { cid: "x", kind: "a", amount: 0 }).some((e) => e.includes(">=")));
  assert.ok(validate(s, { cid: "x", kind: "a", day: "14.10.2026" }).some((e) => e.includes("YYYY-MM-DD")));
});

test("unknown route 404, invalid body 400 (recorded), no handler 501: never a blanket success", async () => {
  const store = new MemoryStore();
  const base = { contract, handlers: {}, store, customers: [], now: "2026-10-14T11:00", keyField: "cid" };
  assert.equal((await handle({ ...base, method: "POST", path: "/nope", body: {} })).status, 404);
  const bad = await handle({ ...base, method: "POST", path: "/lookup", body: { cid: "c1", kind: "z" } });
  assert.equal(bad.status, 400); assert.equal(bad.json.ok, false);
  const ni = await handle({ ...base, method: "POST", path: "/lookup", body: { cid: "c1", kind: "a" } });
  assert.equal(ni.status, 501);
  const st = await store.get("c1");
  assert.deepEqual(st.calls.map((c) => c.status), [400, 501]);
});

test("a handler sees the customer's stored state and test customer; every call is recorded", async () => {
  const store = new MemoryStore();
  const handlers = { lookup: async ({ state, customer }) => {
    state.count = (state.count || 0) + 1;
    return customer ? { status: 200, json: { ok: true, n: state.count, name: customer.name } } : { status: 404, json: { ok: false, error: "unknown customer" } };
  } };
  const base = { contract, handlers, store, customers: [{ cid: "c1", name: "Test" }], now: "t", keyField: "cid" };
  const r1 = await handle({ ...base, method: "POST", path: "/lookup", body: { cid: "c1", kind: "a" } });
  const r2 = await handle({ ...base, method: "POST", path: "/lookup", body: { cid: "c1", kind: "b" } });
  const r3 = await handle({ ...base, method: "POST", path: "/lookup", body: { cid: "zz", kind: "a" } });
  assert.deepEqual([r1.json.n, r2.json.n, r3.status], [1, 2, 404]);
  assert.equal((await store.get("c1")).calls.length, 2);
});

test("contract schemas behind $ref are validated like inline ones; a cycle does not loop", async () => {
  const contract = {
    paths: { "/x": { post: { operationId: "x", requestBody: { content: { "application/json": { schema: { $ref: "#/components/schemas/X" } } } } } } },
    components: { schemas: { X: { type: "object", required: ["n"], properties: { n: { type: "integer" }, me: { $ref: "#/components/schemas/X" } } } } },
  };
  const r = await handle({ method: "POST", path: "/x", body: {}, contract, handlers: {}, store: new MemoryStore(), customers: [], now: "t" });
  assert.equal(r.status, 400);
  assert.match(r.json.error, /n is required/);
});

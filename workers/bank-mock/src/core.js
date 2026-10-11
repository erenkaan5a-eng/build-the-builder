// Generic core of the final bank mock (no final rule, value or name is written here).
// The final service contract (OpenAPI JSON) and test customers are placed in ../contract.json and ../customers.json;
// the operation handlers are written FROM that contract after the package opens (handlers.js). Until an operation has a
// handler the mock answers 501: it is never a service that says yes to everything.

// inline local references ({"$ref": "#/components/schemas/X"}); a cycle or an unresolved reference is left as it is
export function deref(spec) {
  const get = (ptr) => ptr.replace(/^#\//, "").split("/").reduce((n, k) => (n && typeof n === "object" ? n[k.replace(/~1/g, "/").replace(/~0/g, "~")] : undefined), spec);
  const walk = (x, seen) => {
    if (Array.isArray(x)) return x.map((v) => walk(v, seen));
    if (!x || typeof x !== "object") return x;
    const ref = x.$ref;
    if (typeof ref === "string" && ref.startsWith("#/") && !seen.has(ref)) {
      const t = get(ref);
      if (t && typeof t === "object") {
        const rest = Object.fromEntries(Object.entries(x).filter(([k]) => k !== "$ref").map(([k, v]) => [k, walk(v, seen)]));
        return { ...walk(t, new Set([...seen, ref])), ...rest };
      }
    }
    return Object.fromEntries(Object.entries(x).map(([k, v]) => [k, walk(v, seen)]));
  };
  return walk(spec, new Set());
}

export function opsOf(contract) {
  contract = deref(contract);
  const ops = {};
  for (const [path, item] of Object.entries(contract.paths || {})) {
    for (const [method, op] of Object.entries(item || {})) {
      const m = method.toLowerCase();
      if (!["get", "post", "put", "patch", "delete"].includes(m)) continue;
      const schema = op?.requestBody?.content?.["application/json"]?.schema || { type: "object", properties: {} };
      ops[`${m.toUpperCase()} ${path}`] = { name: op.operationId || path.replace(/^\//, ""), path, method: m.toUpperCase(), schema };
    }
  }
  return ops;
}

const TYPES = {
  string: (v) => typeof v === "string",
  number: (v) => typeof v === "number" && Number.isFinite(v),
  integer: (v) => Number.isInteger(v),
  boolean: (v) => typeof v === "boolean",
  object: (v) => v !== null && typeof v === "object" && !Array.isArray(v),
  array: (v) => Array.isArray(v),
};

// request validation from the contract: required fields, types, enums, string patterns/formats, number bounds
export function validate(schema, body) {
  const errors = [];
  if (!TYPES.object(body)) return ["the request body must be a JSON object"];
  for (const k of schema.required || []) if (body[k] === undefined || body[k] === null || body[k] === "") errors.push(`${k} is required`);
  for (const [k, s] of Object.entries(schema.properties || {})) {
    const v = body[k];
    if (v === undefined || v === null) continue;
    if (s.type && TYPES[s.type] && !TYPES[s.type](v)) { errors.push(`${k} must be ${s.type}`); continue; }
    if (s.enum && !s.enum.includes(v)) errors.push(`${k} must be one of ${s.enum.join(", ")}`);
    if (typeof v === "string" && s.pattern && !new RegExp(s.pattern).test(v)) errors.push(`${k} does not match ${s.pattern}`);
    if (typeof v === "string" && s.format === "date" && !/^\d{4}-\d{2}-\d{2}$/.test(v)) errors.push(`${k} must be YYYY-MM-DD`);
    if (typeof v === "number" && s.minimum !== undefined && v < s.minimum) errors.push(`${k} must be >= ${s.minimum}`);
    if (typeof v === "number" && s.maximum !== undefined && v > s.maximum) errors.push(`${k} must be <= ${s.maximum}`);
  }
  return errors;
}

// one request: route by method+path, validate against the contract, run the operation's handler with the customer's
// stored state, record the call in the customer's ledger (also refused and failed calls)
// keyField: the request field that names the customer (from the final contract, set in config.json); null = one shared state
export async function handle({ method, path, body, contract, handlers, store, customers, now, keyField = null }) {
  const ops = opsOf(contract);
  const op = ops[`${method} ${path}`];
  if (!op) return { status: 404, json: { ok: false, error: `no operation ${method} ${path} in the contract` } };
  const errors = validate(op.schema, body);
  const cid = keyField ? (body && typeof body === "object" ? body[keyField] ?? null : null) : "_shared";
  let status, json;
  if (errors.length) {
    status = 400; json = { ok: false, error: errors.join("; ") };
  } else if (!handlers[op.name]) {
    status = 501; json = { ok: false, error: `operation ${op.name} is not implemented in this mock yet` };
  } else {
    const state = cid ? (await store.get(cid)) || { calls: [] } : { calls: [] };
    const customer = keyField && cid ? customers.find((c) => c[keyField] === cid) || null : null;
    try {
      ({ status, json } = await handlers[op.name]({ body, state, customer, now }));
    } catch (e) {
      status = 500; json = { ok: false, error: "mock handler error: " + String(e).slice(0, 200) };
    }
    if (cid) {
      state.calls.push({ tool: op.name, args: body, status, result: json, at: now });
      await store.put(cid, state);
    }
    return { status, json };
  }
  if (cid) {
    const state = (await store.get(cid)) || { calls: [] };
    state.calls.push({ tool: op.name, args: body, status, result: json, at: now });
    await store.put(cid, state);
  }
  return { status, json };
}

export class MemoryStore {
  constructor() { this.m = new Map(); }
  async get(k) { const v = this.m.get(k); return v ? JSON.parse(v) : null; }
  async put(k, v) { this.m.set(k, JSON.stringify(v)); }
}

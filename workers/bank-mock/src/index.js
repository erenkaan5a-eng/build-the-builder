// Cloudflare Worker entry of our Freya Bank statement-debt mock. The logic is in service.js; the answers are the
// final package's test-environment/test-customers.json, bundled byte for byte (data/), kept in memory (no storage).
import DATA from "../data/test-customers.json";
import { makeService, errorBody } from "./service.js";

const S = makeService(DATA);
const PREFIX = "/voice/v1/";
const json = (body, status = 200) => Response.json(body, { status });
const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "");
    if (request.method === "GET" && path === "/health") return json({ status: "ok", services: S.services });
    if (request.method === "POST" && path === "/oauth2/token") {
      // contract section 2: the token is not checked in the test environment; same answer shape
      return json({ access_token: "test-environment-token", token_type: "Bearer", expires_in: 1800 });
    }
    if (path.startsWith(PREFIX) && S.services.includes(path.slice(PREFIX.length))) {
      if (request.method !== "POST") return json(errorBody("INVALID_ARGUMENTS_ERROR", "every service is POST", "ERROR", "MethodNotAllowed"), 405);
      let body = null;
      try { body = await request.json(); } catch { body = null; }
      const a = S.answer(path.slice(PREFIX.length), body);
      if (a.delaySeconds) await sleep(a.delaySeconds);
      return json(a.response, a.http);
    }
    return json(errorBody("NOT_FOUND", `no service ${request.method} ${url.pathname}`, "ERROR", "NotFound"), 404);
  },
};

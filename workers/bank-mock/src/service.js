// Freya Bank statement-debt services (logic): our mock of the bank's test environment, on Cloudflare Workers.
// Written from the final package (sources/documents/2026-10-01-service-contract.md, sections 1-6, and
// test-environment/test-customers.md); the answers are test-environment/test-customers.json, bundled byte for byte
// in ../data/. This file is the mock (an explicit task of the final), not part of the builder.
//
// - Paths: POST /voice/v1/<service> for the seven services (contract section 5), POST /oauth2/token (section 2).
// - Request envelope {data, call}; only `data` decides the answer (section 6). Token, headers, `call`, `aiFlow` are not checked.
// - Lookup as in test-customers.md: by customerNo, by the masked cardNumber exactly as cards.list gave it, and for
//   statement.week.decide / statement.week.change by cardNumber then newStatementWeek. customerNo and newStatementWeek
//   are accepted as string or number.
// - The stored entry's status and body are returned exactly; `delaySeconds` waits before answering and is not sent.
// - No entry: that service's 404 from contract section 4, or a 400 INVALID_ARGUMENTS_ERROR where it has no 404.
//   A missing or empty required field: 400 INVALID_ARGUMENTS_ERROR naming the field. No answer is made up.
const ORIGIN = "ivr-gateway-test:ivr-channel-v0";   // the errorOrigin the contract's test-environment examples show

function guid() {
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
}

// error body in the contract's envelope (section 4): no `data`, only `result`
export function errorBody(code, message, type, rootCause) {
  const g = guid();
  return { result: { guid: g, returnCode: code, messageText: message, code, message, type,
                     details: { guid: g, rootCause, errorOrigin: ORIGIN } } };
}
const invalid = (message) => ({ http: 400, response: errorBody("INVALID_ARGUMENTS_ERROR", message, "ERROR", "InvalidArgumentsException") });
const notFound = (code, message) => ({ http: 404, response: errorBody(code, message, "WARNING", "NotFoundException") });

const empty = (v) => v === undefined || v === null || String(v).trim() === "";
const key = (v) => String(v).trim();


export function makeService(DATA) {
const CUSTOMERS = new Map();               // customerNo -> customer
const BY_CARD = {};                        // service -> Map(cardNumber -> entry or {week: entry})
for (const c of DATA.customers) {
  CUSTOMERS.set(String(c.customerNo), c);
  for (const [svc, v] of Object.entries(c.services || {})) {
    if (v && typeof v === "object" && !("http" in v)) {
      BY_CARD[svc] = BY_CARD[svc] || new Map();
      for (const [card, e] of Object.entries(v)) BY_CARD[svc].set(card, e);
    }
  }
}

// one rule per service: required data fields (the message names the field) and how the stored answer is found
const SERVICES = {
  "cards.list": {
    required: [["customerNo", "customerNo cannot be empty"]],
    find: (d) => CUSTOMERS.get(key(d.customerNo))?.services?.["cards.list"],
    missing: () => notFound("FB_IVR_CHANNEL_102", "Müşteriye ait geçerli kart bilgisi bulunamadı."),
  },
  "cards.balance": {
    required: [["cardNumber", "card number cannot be empty"]],
    find: (d) => BY_CARD["cards.balance"]?.get(key(d.cardNumber)),
    missing: () => notFound("FB_IVR_CHANNEL_120", "Kart bakiye servisi hatası: kart bulunamadı"),
  },
  "statement.week.get": {
    required: [["cardNumber", "card number cannot be empty"]],
    find: (d) => BY_CARD["statement.week.get"]?.get(key(d.cardNumber)),
    missing: () => notFound("FB_IVR_CHANNEL_121", "Kart bulunamadı"),
  },
  "statement.week.decide": {
    required: [["cardNumber", "card number cannot be empty"], ["newStatementWeek", "newStatementWeek cannot be empty"]],
    find: (d) => BY_CARD["statement.week.decide"]?.get(key(d.cardNumber))?.[key(d.newStatementWeek)],
    missing: () => invalid("no statement week preview for this card and week"),
  },
  "statement.week.change": {
    required: [["cardNumber", "card number cannot be empty"], ["newStatementWeek", "newStatementWeek cannot be empty"],
               ["statementDay", "statementDay cannot be empty"]],
    find: (d) => BY_CARD["statement.week.change"]?.get(key(d.cardNumber))?.[key(d.newStatementWeek)],
    missing: () => invalid("no statement week change for this card and week"),
  },
  "contact.email.get": {
    required: [["customerNo", "customerNo cannot be empty"], ["intAddressInfoType", "intAddressInfoType cannot be empty"]],
    find: (d) => CUSTOMERS.get(key(d.customerNo))?.services?.["contact.email.get"],
    missing: () => invalid("customer not found"),
  },
  "statement.pdf.send": {
    required: [["customerNo", "customerNo cannot be empty"], ["cardNumber", "card number cannot be empty"],
               ["currencyType", "currencyType cannot be empty"], ["statementDate", "statementDate cannot be empty"],
               ["emailAddress", "emailAddress cannot be empty"]],
    find: (d) => CUSTOMERS.get(key(d.customerNo))?.services?.["statement.pdf.send"],
    missing: () => notFound("FB_IVR_CHANNEL_107", "Pdf dokümanı bulunamadı"),
  },
};

// the answer for one service request body: {http, response, delaySeconds?}
function answer(service, body) {
  const svc = SERVICES[service];
  if (!body || typeof body !== "object" || !body.data || typeof body.data !== "object" || Array.isArray(body.data)) {
    return invalid("data cannot be empty");
  }
  const d = body.data;
  for (const [field, message] of svc.required) if (empty(d[field])) return invalid(message);
  return svc.find(d) || svc.missing();
}
return { answer, services: Object.keys(SERVICES) };
}

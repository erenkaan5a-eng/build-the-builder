// node --test workers/bank-mock/test/statement.test.mjs   (no network)
// Contract tests of our statement-debt mock against the final package's test data and service contract (section 4-6).
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { makeService } from "../src/service.js";

const DATA = JSON.parse(readFileSync(new URL("../data/test-customers.json", import.meta.url), "utf8"));
const S = makeService(DATA);
const req = (data) => ({ data, call: { ani: "05000000000", lang: "tr" } });

// every stored answer, with the request that must get it
function* fixtures() {
  for (const c of DATA.customers) {
    for (const [svc, v] of Object.entries(c.services)) {
      if ("http" in v) {
        const data = { customerNo: c.customerNo, aiFlow: "CardOps", intAddressInfoType: "E", cardNumber: "540000******0000",
                       currencyType: "TL", statementDate: "05.10.2026", emailAddress: "x@freyabank.example" };
        yield { svc, data, entry: v, who: c.customerNo };
      } else {
        for (const [card, w] of Object.entries(v)) {
          if ("http" in w) yield { svc, data: { cardNumber: card }, entry: w, who: card };
          else for (const [week, e] of Object.entries(w)) yield { svc, data: { cardNumber: card, newStatementWeek: Number(week), statementDay: 5 }, entry: e, who: `${card} w${week}` };
        }
      }
    }
  }
}

test("every stored answer comes back exactly: same status, same body, delay kept out of the body", () => {
  let n = 0;
  for (const f of fixtures()) {
    const a = S.answer(f.svc, req(f.data));
    assert.equal(a.http, f.entry.http, `${f.svc} ${f.who}`);
    assert.deepEqual(a.response, f.entry.response, `${f.svc} ${f.who}`);
    assert.ok(!("delaySeconds" in a.response));
    n++;
  }
  assert.ok(n > 600, `replayed ${n} answers`);
});

test("customerNo and newStatementWeek: string and number give the same answer", () => {
  const c = DATA.customers[0];
  assert.deepEqual(S.answer("cards.list", req({ customerNo: Number(c.customerNo) })), S.answer("cards.list", req({ customerNo: String(c.customerNo) })));
  const [card, weeks] = Object.entries(c.services["statement.week.decide"])[0];
  const wk = Object.keys(weeks)[0];
  assert.deepEqual(S.answer("statement.week.decide", req({ cardNumber: card, newStatementWeek: wk, statementDay: 1 })),
                   S.answer("statement.week.decide", req({ cardNumber: card, newStatementWeek: Number(wk), statementDay: 1 })));
});

const r = (svc, data) => S.answer(svc, req(data));
const code = (a) => a.response.result.code;

test("not in the data: the service's 404 from contract section 4, else 400 INVALID_ARGUMENTS_ERROR; never data", () => {
  const cases = [
    ["cards.list", { customerNo: "11111111" }, 404, "FB_IVR_CHANNEL_102"],
    ["cards.balance", { cardNumber: "540000******9999" }, 404, "FB_IVR_CHANNEL_120"],
    ["statement.week.get", { cardNumber: "540000******9999" }, 404, "FB_IVR_CHANNEL_121"],
    ["statement.week.decide", { cardNumber: "540000******9999", newStatementWeek: 2, statementDay: 5 }, 400, "INVALID_ARGUMENTS_ERROR"],
    ["statement.week.change", { cardNumber: "540000******9999", newStatementWeek: 2, statementDay: 5 }, 400, "INVALID_ARGUMENTS_ERROR"],
    ["contact.email.get", { customerNo: "11111111", intAddressInfoType: "E" }, 400, "INVALID_ARGUMENTS_ERROR"],
    ["statement.pdf.send", { customerNo: "11111111", cardNumber: "540000******9999", currencyType: "TL", statementDate: "05.10.2026", emailAddress: "a@b.example" }, 404, "FB_IVR_CHANNEL_107"],
  ];
  for (const [svc, data, http, c] of cases) {
    const a = r(svc, data);
    assert.equal(a.http, http, svc); assert.equal(code(a), c, svc);
    assert.ok(!("data" in a.response), `${svc}: an error answer has no data object`);
    const res = a.response.result;
    assert.equal(res.returnCode, res.code); assert.equal(res.messageText, res.message);
    assert.equal(res.details.guid, res.guid);
    assert.equal(res.type, http === 404 ? "WARNING" : "ERROR");
  }
  // cards.list 404 message from the contract
  assert.equal(r("cards.list", { customerNo: "11111111" }).response.result.message, "Müşteriye ait geçerli kart bilgisi bulunamadı.");
  assert.equal(r("statement.pdf.send", { customerNo: "11111111", cardNumber: "x", currencyType: "TL", statementDate: "05.10.2026", emailAddress: "a@b.example" }).response.result.message, "Pdf dokümanı bulunamadı");
});

test("the card's current week has no preview or change entry: 400, nothing made up", () => {
  for (const svc of ["statement.week.decide", "statement.week.change"]) {
    for (const c of DATA.customers) {
      for (const [card, weeks] of Object.entries(c.services[svc] || {})) {
        const missing = ["1", "2", "3", "4"].filter((w) => !(w in weeks));
        for (const w of missing) {
          const a = r(svc, { cardNumber: card, newStatementWeek: w, statementDay: 5 });
          assert.equal(a.http, 400); assert.equal(code(a), "INVALID_ARGUMENTS_ERROR");
        }
      }
    }
  }
});

test("a card is only found by the masked number exactly as cards.list gave it", () => {
  const c = DATA.customers.find((x) => x.services["cards.balance"]);
  const card = Object.keys(c.services["cards.balance"])[0];
  const balanceMasked = card.slice(0, 4) + "********" + card.slice(-4);   // the cards.balance answer's own masking
  assert.equal(r("cards.balance", { cardNumber: card }).http, c.services["cards.balance"][card].http);
  assert.equal(r("cards.balance", { cardNumber: balanceMasked }).http, 404);
  assert.equal(r("cards.balance", { cardNumber: card.slice(-4) }).http, 404);
});

test("required data fields: missing or empty is 400 INVALID_ARGUMENTS_ERROR naming the field; no data object is 400", () => {
  const cases = [
    ["cards.list", {}, "customerNo"], ["cards.balance", { cardNumber: "" }, "card number"], ["statement.week.get", {}, "card number"],
    ["statement.week.decide", { cardNumber: "540000******1234" }, "newStatementWeek"],
    ["statement.week.change", { cardNumber: "540000******1234", newStatementWeek: 2 }, "statementDay"],
    ["contact.email.get", { customerNo: "90000001", intAddressInfoType: "" }, "intAddressInfoType"],
    ["statement.pdf.send", { customerNo: "90000001", cardNumber: "540000******1234", currencyType: "TL", statementDate: "05.10.2026" }, "emailAddress"],
  ];
  for (const [svc, data, field] of cases) {
    const a = r(svc, data);
    assert.equal(a.http, 400, svc); assert.equal(code(a), "INVALID_ARGUMENTS_ERROR", svc);
    assert.ok(a.response.result.message.includes(field), `${svc}: ${a.response.result.message}`);
  }
  for (const body of [null, {}, { data: null }, { data: [] }, { call: {} }]) assert.equal(S.answer("cards.list", body).http, 400);
});

test("the contract's own examples: customer 90000001 card list and section 5.3 customer 92220795 joint statement", () => {
  const a = r("cards.list", { customerNo: "90000001", aiFlow: "CardOps" });
  assert.equal(a.http, 200); assert.equal(a.response.result.returnCode, "1");
  assert.equal(a.response.data.cards[0].cardNumber, "540000******1234");
  const w = r("statement.week.get", { cardNumber: "540000******3201" });
  assert.equal(w.http, 200); assert.equal(w.response.data.relationType, "M"); assert.equal(w.response.data.relatedCardNumber, "540000******3202");
});

test("the one delayed answer keeps its delay (waited by the Worker, not sent)", () => {
  const delayed = [...fixtures()].filter((f) => f.entry.delaySeconds);
  assert.ok(delayed.length >= 1);
  for (const f of delayed) assert.equal(S.answer(f.svc, req(f.data)).delaySeconds, f.entry.delaySeconds);
});

// Operation handlers of the final bank mock, keyed by operationId (or the path without '/').
// EMPTY ON PURPOSE before the final package opens: each handler is written from the final service contract and its test
// customers (validation, recording, error behaviour). Signature:
//   async ({ body, state, customer, now }) => ({ status, json })
// `state` is this customer's stored object ({ calls: [...] } plus anything the handler keeps); it is saved after the call.
export const handlers = {};

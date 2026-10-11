# Final run: checks after the run (outside the build run; the run's own trace and release verdict are unchanged)

Run: traces/final-r3-20261011-2058-20261011-184634.log (source commit 0f05b94, fallback path), workflow 6d079c07-c690-40f5-9692-3e16c0389aea
v1, agent 67005014-5987-4a80-9f9b-9858b578819c, export sha256-16 16df802a3766a667 (== tested). The run's own release check
FAILED: its one behaviour check (a chat API smoke turn) got HTTP 504 four times.

| when (İstanbul) | check | result |
|---|---|---|
| 22:11 | chat API, final workflow, customer 95004361, "Merhaba" | 504 after 13 s (same as in the run) → `final-postrun-probe.json` |
| 22:11 | chat API, control: practice workflow loc-ab, "Hello?" | answered in 2 s → the chat API itself works; the 504 is specific to the final workflow |
| 22:12 | one text simulation (the scoring channel), persona = example-scenarios Example 1 (customer 95004361, now 2026-10-12T10:30:00+03:00) | completed in 23 s; the agent called cards.list, cards.balance, contact.email.get on our mock, read the card (last four 2000, Yıldız Premium, statement 5 Oct 2026) and the TL amounts 12.000 / 4.800 / 9.500 / 2.000 from the service, then routed to the main menu on "no thanks" → `final-postrun-sim.json` |

Reading: the workflow runs three bank calls and four code steps before its first sentence; the chat API's gateway
answers 504 after ~13 s while the simulation channel completes the same flow. This is one run of one example: not a
pass^3 claim, not a policy-correctness claim. Known rule gaps are listed by the fallback agent in the trace (GAPS lines).

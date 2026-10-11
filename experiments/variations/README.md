# Conversation variations (development; public practice customers with a changed script)

`hardship-own-offer.json`: PUB-05's customer (personal loan 780.00, floor 260.00, 21 days late, now Wed 14 Oct 2026)
says the hardship and his own offer in one message. Expected values are derived from Brief A, not from the runtime:
rule 32 last sentence (a customer who still names a date or amount is recorded under sections 7 and 8), rule 27
(260 <= 300 <= 780 is accepted), rule 19 (Fri 16 Oct is a business day before the late-band deadline 23 Oct).
Expected: one promise p1 300.00 on 2026-10-16, outcome promise, no notes, no transfer.
Run: `FREYA_AUTH_VIA_PROXY=1 python3 tools/run_cases_cloud.py <cl-a agent> --cases experiments/variations/hardship-own-offer.json --reps N`

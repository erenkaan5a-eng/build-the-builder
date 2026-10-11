# Final package receipts (originals are never edited; each receipt is its own folder)

| receipt | folder | received (UTC / İstanbul) | source | files (sha256) | status |
|---|---|---|---|---|---|
| r1 | `r1-20261011-2016/` | BRIEF.md 17:13:48 / 20:13:48 (same file uploaded again 17:16:49, identical hash); statement-debt-call-flow.pdf 17:16:49 / 20:16:49 | chat upload by the user from the organiser's link (only these two files visible there at the time) | BRIEF.md `9f7a9256a108ff0bddf176688633b8add3c7a05e4c407752b3a2ed208c872ef1`; statement-debt-call-flow.pdf `1092fe84329911c89477e794ed874f8216aeb31cc4c825931c4e017374eb69ca` | INCOMPLETE: BRIEF.md lists README.md, sources/ (emails, documents incl. the integration document section 6, meetings), test-environment/, example-scenarios.md, cloudflare-mock/; none received. The flow PDF's place in the pack (BRIEF: `sources/documents/`) is not confirmed, so it is kept flat as received |
| r2 | `r2-20261011-2053/` | README.md and example-scenarios.md 17:53:04 / 20:53:04; BRIEF.md and the flow PDF carried over from r1 unchanged | chat upload by the user (README arrived as upload `README_1.md`; on the user's computer it is `README (1).md` because of a download-name clash; it is the pack's `README.md` and is stored under that name; no earlier README existed, nothing was overwritten) | BRIEF.md `9f7a9256…2ef1` (= r1); README.md `476f99af2e66739de8ed4a192b04c003cc6ab5d31a9bce6825af4d9608852cc6`; example-scenarios.md `c7534cb5d591d6399a72c3c717f35d75c81ff2d07c1587ba5ab90245d283d989`; statement-debt-call-flow.pdf `1092fe84…69ca` (= r1) | INCOMPLETE: sources/ (emails + attachments, documents incl. the service contract, meetings), test-environment/ (test-customers.json/.md), cloudflare-mock/ not received. README places the flow PDF at the folder root, so the flat placement matches the pack |

Drive: the shared folder "Build the Builder - Final Case" (owner yavuz@freyavoice.ai, created 17:04:10Z) is visible through
the Drive connector, but its files cannot be listed or downloaded through it (11 Oct 20:15 İstanbul); no file was taken
from Drive.
Reading check (r1, builder's own reader `builder/case_input.py`, no model call): both files read, no error. The PDF is a
one-page vector flow drawing: all box/diamond/edge labels are extracted as text, but the arrows (which branch leads where)
are not; the fallback agent is told to open the original PDF (it reads pages visually).

## Current package view
`CURRENT.md` names the receipt folder that holds every file received so far (one folder, earlier files carried over
unchanged). New receipts are made with `scripts/package_receipt.py` (never overwrites a receipt; changed files are
listed in `<name>.diff.md`; inventory with sha256 in `<name>.inventory.json`, outside the case folder).

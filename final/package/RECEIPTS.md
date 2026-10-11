# Final package receipts (originals are never edited; each receipt is its own folder)

| receipt | folder | received (UTC / İstanbul) | source | files (sha256) | status |
|---|---|---|---|---|---|
| r1 | `r1-20261011-2016/` | BRIEF.md 17:13:48 / 20:13:48 (same file uploaded again 17:16:49, identical hash); statement-debt-call-flow.pdf 17:16:49 / 20:16:49 | chat upload by the user from the organiser's link (only these two files visible there at the time) | BRIEF.md `9f7a9256a108ff0bddf176688633b8add3c7a05e4c407752b3a2ed208c872ef1`; statement-debt-call-flow.pdf `1092fe84329911c89477e794ed874f8216aeb31cc4c825931c4e017374eb69ca` | INCOMPLETE: BRIEF.md lists README.md, sources/ (emails, documents incl. the integration document section 6, meetings), test-environment/, example-scenarios.md, cloudflare-mock/; none received. The flow PDF's place in the pack (BRIEF: `sources/documents/`) is not confirmed, so it is kept flat as received |

Drive: the shared folder "Build the Builder - Final Case" (owner yavuz@freyavoice.ai, created 17:04:10Z) is visible through
the Drive connector, but its files cannot be listed or downloaded through it (11 Oct 20:15 İstanbul); no file was taken
from Drive.
Reading check (r1, builder's own reader `builder/case_input.py`, no model call): both files read, no error. The PDF is a
one-page vector flow drawing: all box/diamond/edge labels are extracted as text, but the arrows (which branch leads where)
are not; the fallback agent is told to open the original PDF (it reads pages visually).

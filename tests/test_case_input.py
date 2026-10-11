"""Case folder input (builder/case_input.py) on synthetic documents made here. No model or network call.
The documents are invented test data (Turkish text included); none of it is read by the builder at run time."""
import json, pathlib, sys, tempfile, zipfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
sys.path.insert(0, str(ROOT / "tests"))
import case_input as CI  # noqa: E402
from negotiation_harness import check, FAILS  # noqa: E402

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_docx(p, body_xml):
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:document {W}><w:body>{body_xml}</w:body></w:document>')


def para(text, style=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>"


def table(rows):
    return "<w:tbl>" + "".join("<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>" for c in r) + "</w:tr>" for r in rows) + "</w:tbl>"


def make_pdf(p, text):
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"]
    stream = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET"
    objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offs = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out.encode()))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    x = len(out.encode())
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n"
    pathlib.Path(p).write_bytes(out.encode())


CONTRACT = {"openapi": "3.0.0", "info": {"title": "test"}, "servers": [{"url": "https://placeholder.invalid/v1"}],
            "paths": {"/lookup": {"post": {"requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"id": {"type": "string"}}}}}},
                                           "responses": {"200": {"content": {"application/json": {"schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}}}}}}}}}}

with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    (d / "README.md").write_text("# Okuma sırası\nÖnce BRIEF.md okunur.\n", encoding="utf-8")
    (d / "BRIEF.md").write_text("# Kredi kartı ekstre borcu (test)\nMüşteriye 'Bugün ödeyebilir misiniz?' diye sorulur. Tutar 1.234,56 TL; son tarih 15.11.2026.\n", encoding="utf-8")
    (d / "docs").mkdir()
    make_docx(d / "docs" / "politika.docx", para("Ödeme kuralları", "Heading1") + para("Asgari tutar: ekstre tutarının %20'si.")
              + table([["Gecikme günü", "Son tarih"], ["1-7", "12. iş günü"]]) + para("Ek kural", "Balk2"))
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Tatiller"
    ws.append(["Tarih", "Ad"]); ws.append(["2026-10-29", "Cumhuriyet Bayramı"]); wb.save(d / "docs" / "takvim.xlsx")
    make_pdf(d / "docs" / "memo.pdf", "Memo: late band deadline is the 5th business day")
    (d / "docs" / "bozuk.docx").write_bytes(b"this is not a zip file")
    (d / "contract.json").write_text(json.dumps(CONTRACT), encoding="utf-8")
    case = CI.load_case(d)
    t = case["text"]
    order = [it["file"] for it in case["inventory"]]
    check("F1 reading order: BRIEF.md, README.md, then the other files by path", order[:2] == ["BRIEF.md", "README.md"] and order[2:] == sorted(order[2:], key=str.lower), order)
    check("F2 Turkish text kept as UTF-8 (ı, ş, ğ, ö, ü, ç; '1.234,56 TL'; '15.11.2026')", "Kredi kartı ekstre borcu" in t and "1.234,56 TL" in t and "15.11.2026" in t and "Bugün ödeyebilir" in t, t[:300])
    check("F3 Word: heading levels (also a Turkish 'Balk2' style) and table rows kept", "# Ödeme kuralları" in t and "## Ek kural" in t and "| Gecikme günü | Son tarih |" in t and "| 1-7 | 12. iş günü |" in t, t)
    check("F4 Excel: sheet name and rows as a table", "## Sheet: Tatiller" in t and "| 2026-10-29 | Cumhuriyet Bayramı |" in t, t)
    check("F5 PDF: page text read", "late band deadline is the 5th business day" in t, t[-400:])
    check("F6 each file starts with a FILE header naming it (source kept)", "===== FILE: docs/politika.docx (docx" in t and "===== FILE: docs/takvim.xlsx" in t, "")
    check("F7 an unreadable document is a visible error, not skipped silently", any(e.startswith("docs/bozuk.docx") for e in case["errors"])
          and [it for it in case["inventory"] if it["file"] == "docs/bozuk.docx" and it.get("error")], case["errors"])
    check("F8 the package note says example customers/conversations are not rules and later files do not override by date",
          "not rules" in t and "does not automatically replace" in t, t[:400])
    c = CI.find_contract(d)
    check("F9 the one OpenAPI contract of the folder is found", c.name == "contract.json", c)
    out = d / "bound.json"
    note = CI.bind_contract(c, "https://bank-mock.example.workers.dev", out)
    check("F10 the mock URL becomes the server; the contract's '/v1' path is kept and logged", json.load(open(out))["servers"][0]["url"] == "https://bank-mock.example.workers.dev/v1" and "kept" in note, note)
    CI.bind_contract(c, "https://bank-mock.example.workers.dev/api/", out)
    check("F11 a mock URL with its own path is used as given", json.load(open(out))["servers"][0]["url"] == "https://bank-mock.example.workers.dev/api", json.load(open(out))["servers"])
    try:
        CI.bind_contract(c, "http://insecure.example", out); bad = False
    except RuntimeError:
        bad = True
    check("F12 a non-https mock URL is refused", bad, "")
    (d / "contract2.yaml").write_text("openapi: 3.0.0\npaths: {}\n", encoding="utf-8")
    try:
        CI.find_contract(d); two = False
    except RuntimeError as e:
        two = "several" in str(e)
    check("F13 two contracts in a folder: an explicit error (no guess)", two, "")

with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    (d / "notes.md").write_text("no brief here", encoding="utf-8")
    case = CI.load_case(d)
    check("F14 a folder without BRIEF.md is reported", any("BRIEF.md" in e for e in case["errors"]), case["errors"])
    try:
        CI.find_contract(d); none = False
    except RuntimeError as e:
        none = "nothing is invented" in str(e)
    check("F15 no contract in the folder: an explicit error, no endpoint invented", none, "")

# e-mail, HTML, PowerPoint, images (synthetic)
d2 = pathlib.Path(tempfile.mkdtemp())
(d2 / "BRIEF.md").write_text("# Görev\nÖrnek.", encoding="utf-8")
(d2 / "mails").mkdir()
(d2 / "mails" / "thread.eml").write_bytes((
    "From: Banka <a@example.com>\r\nTo: Ekip <b@example.com>\r\nSubject: =?utf-8?b?w5Zuc2Vt?=\r\nDate: Mon, 5 Oct 2026 10:00:00 +0300\r\n"
    "MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=XX\r\n\r\n--XX\r\nContent-Type: text/plain; charset=utf-8\r\n"
    "Content-Transfer-Encoding: 8bit\r\n\r\nKural: ikinci sürüm geçerlidir.\r\n--XX\r\nContent-Type: application/pdf\r\n"
    "Content-Disposition: attachment; filename=analiz-v2.pdf\r\n\r\nJVBERi0=\r\n--XX--\r\n").encode("utf-8"))
(d2 / "page.html").write_text("<html><head><style>p{}</style><script>var x=1;</script></head><body><h1>Başlık</h1>"
                              "<p>Satır bir</p><table><tr><td>a</td><td>b</td></tr></table></body></html>", encoding="utf-8")
with zipfile.ZipFile(d2 / "deck.pptx", "w") as z:
    A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    for i, t in ((1, "Birinci slayt"), (2, "İkinci slayt")):
        z.writestr(f"ppt/slides/slide{i}.xml", f'<?xml version="1.0"?><p:sld xmlns:p="x" {A}><a:p><a:r><a:t>{t}</a:t></a:r></a:p></p:sld>')
(d2 / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\n")
(d2 / "note.msg").write_bytes(b"binary")
r2 = CI.load_case(d2)
inv2 = {i["file"]: i for i in r2["inventory"]}
check("C20 e-mail: headers, decoded subject, text body and the attachment name are read",
      all(x in r2["text"] for x in ("From: Banka", "Subject: Önsem", "Kural: ikinci sürüm geçerlidir.", "[attachment: analiz-v2.pdf]")), r2["text"][:400])
check("C21 HTML: visible text with headings and table cells; script and style left out",
      "Başlık" in r2["text"] and "Satır bir" in r2["text"] and "| a" in r2["text"] and "var x" not in r2["text"] and "p{}" not in r2["text"])
check("C22 PowerPoint: slide text in slide order", r2["text"].find("[slide 1]") < r2["text"].find("Birinci slayt") < r2["text"].find("[slide 2]") < r2["text"].find("İkinci slayt"))
check("C23 an image is a visible warning (visual only), not an error", inv2["diagram.png"].get("visual_only") is True
      and any("diagram.png" in w for w in r2["warnings"]) and not any("diagram.png" in e for e in r2["errors"]), (r2["warnings"], r2["errors"]))
check("C24 a type without a reader is still a visible error", any(e.startswith("note.msg: unsupported document type") for e in r2["errors"]), r2["errors"])
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

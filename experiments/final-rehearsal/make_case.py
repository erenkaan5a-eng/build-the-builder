"""Synthetic rehearsal case folder in the final package's form, built only from PRACTICE material (no final data):
BRIEF.md = practice Brief A, README.md (Turkish package notes), a Turkish Word memo that changes only the conversation
language, and the practice tool API rewritten as a service contract with Turkish operation paths, $ref schemas and 201
answers. Checks the builder's folder input, Word reading, cross-document amendment, Turkish handling and the
role -> operation binding with a real extraction.

    python3 experiments/final-rehearsal/make_case.py <out_dir>
    python3 builder/build.py <out_dir> https://rehearsal-mock.example.workers.dev --slot rehearsal-tr --local-only
"""
import copy, json, pathlib, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
PATHS = {"verify_identity": "musteri/kimlik-dogrula", "get_account": "musteri/hesap-ozeti", "create_promise": "odeme/soz-kaydet",
         "add_note": "gorusme/not-ekle", "schedule_callback": "gorusme/geri-arama", "transfer_to_agent": "gorusme/temsilciye-aktar",
         "close_call": "gorusme/kapat"}


def para(text, style=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>"


def main(out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "BRIEF.md").write_text((ROOT / "briefs" / "brief-a.md").read_text(encoding="utf-8"), encoding="utf-8")
    (out / "README.md").write_text(
        "# Paket notları (prova)\n\n- BRIEF.md görüşme kurallarını verir.\n- `servis-sozlesmesi.json` bankanın servis sözleşmesidir.\n"
        "- `dil-notu.docx` yalnız görüşme dilini değiştirir; başka kural değişmez.\n", encoding="utf-8")
    body = (para("Operasyon notu", "Heading1")
            + para("Kapsam: yalnız görüşme dili. Bu nottan itibaren müşteriyle tüm görüşme Türkçe yapılır; ajan Türkçe konuşur, "
                   "tarihleri ve tutarları Türkçe söyler. Brief'teki diğer bütün kurallar, tutarlar, tarihler ve kapanış tablosu aynen geçerlidir."))
    with zipfile.ZipFile(out / "dil-notu.docx", "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:document {W}><w:body>{body}</w:body></w:document>')
    spec = json.load(open(ROOT / "tools" / "openapi.json", encoding="utf-8"))
    c = copy.deepcopy(spec)
    c["servers"] = [{"url": "https://banka.example/v2"}]
    c["paths"] = {}
    schemas = c.setdefault("components", {}).setdefault("schemas", {})
    for p, item in spec["paths"].items():
        role = p.rsplit("/", 1)[-1]
        item = copy.deepcopy(item)
        op = item.get("post") or item.get("get")
        key = role.title().replace("_", "")
        body = op["requestBody"]["content"]["application/json"]
        schemas[key + "Istek"], body["schema"] = body["schema"], {"$ref": f"#/components/schemas/{key}Istek"}
        ok = op["responses"].pop("200")
        schemas[key + "Yanit"] = ok["content"]["application/json"]["schema"]
        ok["content"]["application/json"]["schema"] = {"$ref": f"#/components/schemas/{key}Yanit"}
        op["responses"]["201"] = ok
        op.pop("operationId", None)
        c["paths"]["/" + PATHS[role]] = item
    (out / "servis-sozlesmesi.json").write_text(json.dumps(c, indent=1, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main(sys.argv[1])

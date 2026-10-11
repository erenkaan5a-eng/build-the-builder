"""Case folder input: read every document of a case package into one source text, and bind the service contract to
the mock URL. Nothing here knows any brief; it only reads files.

    load_case(folder)            -> {"text", "inventory", "errors", "warnings"}
    find_contract(folder)        -> path of the one machine-readable service contract (OpenAPI JSON/YAML) or raises
    bind_contract(path, url, out)-> writes the contract with its server set to the mock URL; returns a log line

Reading order: BRIEF.md, then README.md (as the package asks), then every other file by path. Each file starts with a
header line naming it, so the extraction step can cite the source and see which document a rule comes from; a later
document is not assumed to override an earlier one (amendments are judged by the extraction step from their text and
scope). Tables keep their rows ('| a | b |'); Word headings keep their level ('#'). A file that cannot be read is
listed in errors (visible in the trace); a missing BRIEF.md is an error.
"""
import csv, hashlib, io, json, pathlib, re, shutil, subprocess, urllib.parse, zipfile
import xml.etree.ElementTree as ET

TEXT_EXT = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml"}
VISUAL_ONLY = "[image: no text can be extracted from this file; open the original to see it]"
SKIP_NAMES = {".ds_store", "thumbs.db"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def sha16(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


def _row(cells):
    return "| " + " | ".join(str(c if c is not None else "").replace("\n", " ").strip() for c in cells) + " |"


# ---------------------------------------------------------------- readers
def read_docx(path):
    """Paragraphs (headings as '#') and tables in document order. python-docx if installed, else the XML in the zip."""
    out = []
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    for el in list(body if body is not None else []):
        if el.tag == W + "p":
            style = el.find(f"{W}pPr/{W}pStyle")
            sid = style.get(W + "val") if style is not None else ""
            txt = "".join(t.text or "" for t in el.iter(W + "t")).strip()
            if not txt:
                continue
            m = re.match(r"(?i)^(heading|başlık|baslik|balk|title)\s*(\d?)$", sid or "")
            lvl = (int(m.group(2)) if m.group(2) else 1) if m else 0
            out.append(("#" * lvl + " " if lvl else "") + txt)
        elif el.tag == W + "tbl":
            for tr in el.iter(W + "tr"):
                cells = ["".join(t.text or "" for t in tc.iter(W + "t")) for tc in tr.findall(W + "tc")]
                out.append(_row(cells))
            out.append("")
    return "\n".join(out)


def read_xlsx(path):
    """Every sheet as a table ('## Sheet: name' then rows). openpyxl if installed, else the XML in the zip."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        out = []
        for ws in wb.worksheets:
            out.append(f"## Sheet: {ws.title}")
            for row in ws.iter_rows(values_only=True):
                if any(c not in (None, "") for c in row):
                    out.append(_row(row))
            out.append("")
        return "\n".join(out)
    except ImportError:
        pass
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(S + "si"):
                shared.append("".join(t.text or "" for t in si.iter(S + "t")))
        wbx = ET.fromstring(z.read("xl/workbook.xml"))
        names = [s.get("name") for s in wbx.iter(S + "sheet")]
        out = []
        for i, name in enumerate(names, 1):
            p = f"xl/worksheets/sheet{i}.xml"
            if p not in z.namelist():
                continue
            out.append(f"## Sheet: {name}")
            for r in ET.fromstring(z.read(p)).iter(S + "row"):
                vals = []
                for c in r.findall(S + "c"):
                    v = c.find(S + "v")
                    t = c.get("t")
                    if t == "s" and v is not None:
                        vals.append(shared[int(v.text)])
                    elif t == "inlineStr":
                        vals.append("".join(x.text or "" for x in c.iter(S + "t")))
                    else:
                        vals.append(v.text if v is not None else "")
                if any(vals):
                    out.append(_row(vals))
            out.append("")
        return "\n".join(out)


def read_pdf(path):
    """Text of every page. pypdf if installed, else the pdftotext tool; no silent empty result."""
    try:
        import pypdf
        r = pypdf.PdfReader(str(path))
        txt = "\n\n".join(f"[page {i + 1}]\n" + (p.extract_text() or "") for i, p in enumerate(r.pages))
        if txt.replace("[page", "").strip(" \n0123456789]"):
            return txt
    except ImportError:
        pass
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout
    raise RuntimeError("no PDF reader (install pypdf or poppler pdftotext)")


def read_csv(path):
    raw = pathlib.Path(path).read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(raw[:4000], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return "\n".join(_row(r) for r in csv.reader(io.StringIO(raw), dialect) if any(r))


class _HTMLText(__import__("html.parser").parser.HTMLParser):
    """Visible text of an HTML/XML/SVG document; block elements and <br> become line breaks; script/style skipped."""
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section", "article", "header",
             "footer", "ul", "ol", "dt", "dd", "title", "text", "tspan"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def read_html(path):
    h = _HTMLText()
    h.feed(pathlib.Path(path).read_text(encoding="utf-8-sig", errors="replace"))
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in "".join(h.out).splitlines()]
    return "\n".join(l for l in lines if l)


def read_eml(path):
    """An e-mail as received: its headers, its text body (HTML bodies as text) and the names of its attachments."""
    import email
    from email import policy
    msg = email.message_from_bytes(pathlib.Path(path).read_bytes(), policy=policy.default)
    out = [f"{h}: {msg[h]}" for h in ("Date", "From", "To", "Cc", "Subject") if msg[h]]
    for part in msg.walk():
        if part.is_multipart():
            continue
        name = part.get_filename()
        if name:
            out.append(f"[attachment: {name}]")
        elif part.get_content_type() == "text/plain":
            out.append(part.get_content())
        elif part.get_content_type() == "text/html":
            h = _HTMLText(); h.feed(part.get_content()); out.append("".join(h.out))
    return "\n".join(str(x).strip() for x in out if str(x).strip())


def read_pptx(path):
    """Slide text of a PowerPoint file, one block per slide in slide order."""
    with zipfile.ZipFile(path) as z:
        slides = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)), key=lambda n: int(re.findall(r"\d+", n)[-1]))
        out = []
        for i, n in enumerate(slides, 1):
            root = ET.fromstring(z.read(n))
            paras = []
            for para in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}p"):
                t = "".join(x.text or "" for x in para.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t")).strip()
                if t:
                    paras.append(t)
            out.append(f"[slide {i}]\n" + "\n".join(paras))
    return "\n".join(out)


IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}


def read_any(path):
    ext = pathlib.Path(path).suffix.lower()
    if ext in IMAGE_EXT:
        # not an error: an image has no text to extract; its content is only in the original (opened visually)
        return VISUAL_ONLY
    if ext in (".html", ".htm", ".xml", ".svg", ".xhtml"):
        return read_html(path)
    if ext == ".eml":
        return read_eml(path)
    if ext == ".pptx":
        return read_pptx(path)
    if ext in TEXT_EXT:
        return pathlib.Path(path).read_text(encoding="utf-8-sig")
    if ext == ".docx":
        return read_docx(path)
    if ext in (".xlsx", ".xlsm"):
        return read_xlsx(path)
    if ext == ".pdf":
        return read_pdf(path)
    if ext == ".csv":
        return read_csv(path)
    raise RuntimeError(f"unsupported document type {ext or '(none)'}")


# ---------------------------------------------------------------- package
def _order(folder):
    files = [p for p in sorted(pathlib.Path(folder).rglob("*")) if p.is_file() and p.name.lower() not in SKIP_NAMES
             and not any(part.startswith(".") for part in p.relative_to(folder).parts)]
    def key(p):
        n = p.name.lower()
        return (0 if n == "brief.md" else 1 if n == "readme.md" else 2, str(p.relative_to(folder)).lower())
    return sorted(files, key=key)


def load_case(folder):
    folder = pathlib.Path(folder)
    if not folder.is_dir():
        raise RuntimeError(f"case folder {folder} not found")
    parts, inventory, errors, warnings = [], [], [], []
    files = _order(folder)
    if not files or files[0].name.lower() != "brief.md":
        errors.append("BRIEF.md not found in the case folder (the package says to read it first)")
    for p in files:
        rel = str(p.relative_to(folder)).replace("\\", "/")
        item = {"file": rel, "type": p.suffix.lower().lstrip("."), "bytes": p.stat().st_size, "sha256_16": sha16(p)}
        try:
            txt = read_any(p)
            if not txt.strip():
                raise RuntimeError("no text could be read")
            item["chars"] = len(txt)
            if txt == VISUAL_ONLY:
                item["visual_only"] = True
                warnings.append(f"{rel}: image, no text extracted (the original is in the case folder)")
            parts.append(f"\n===== FILE: {rel} ({item['type']}, sha256 {item['sha256_16']}) =====\n{txt.strip()}\n")
        except Exception as e:
            item["error"] = str(e)[:200]
            errors.append(f"{rel}: {item['error']}")
        inventory.append(item)
    head = ("CASE PACKAGE (" + str(len(files)) + " files). Each file starts with a FILE header. Read BRIEF.md first, then README.md. "
            "A later or dated document does not automatically replace an earlier one: apply a change only within the scope it states. "
            "Test customers and example conversations illustrate the rules and serve testing; they are not rules, and their names, "
            "numbers and dates must not become fixed values of the agent.\n")
    return {"text": head + "".join(parts), "inventory": inventory, "errors": errors, "warnings": warnings}


def _load_contract(p):
    raw = pathlib.Path(p).read_text(encoding="utf-8-sig")
    if p.suffix.lower() == ".json":
        return json.loads(raw)
    try:
        import yaml
    except ImportError:
        raise RuntimeError(f"{p.name} is YAML and PyYAML is not installed")
    return yaml.safe_load(raw)


def find_contract(folder):
    """The single OpenAPI/Swagger document of the package (JSON or YAML with 'paths')."""
    found = []
    for p in _order(folder):
        if p.suffix.lower() not in (".json", ".yaml", ".yml"):
            continue
        try:
            d = _load_contract(p)
        except Exception:
            continue
        if isinstance(d, dict) and (d.get("openapi") or d.get("swagger")) and isinstance(d.get("paths"), dict):
            found.append(p)
    if not found:
        raise RuntimeError("no machine-readable service contract (OpenAPI JSON/YAML with 'paths') in the case folder; "
                           "nothing is invented: name the contract file with --contract")
    if len(found) > 1:
        raise RuntimeError("several service contracts in the case folder: " + ", ".join(str(p.relative_to(folder)) for p in found)
                           + "; name the one to use with --contract")
    return found[0]


def bind_contract(contract_path, mock_url, out_path):
    """Write the contract as JSON with servers[0].url = the mock URL. If the contract's server has a path (e.g. '/v1') and
    the mock URL has none, that path is kept (logged)."""
    u = urllib.parse.urlparse(mock_url)
    if u.scheme != "https" or not u.netloc:
        raise RuntimeError(f"mock_url must be an https URL, got {mock_url!r}")
    spec = _load_contract(pathlib.Path(contract_path))
    old = ((spec.get("servers") or [{}])[0] or {}).get("url", "")
    base = mock_url.rstrip("/")
    note = f"contract server {old!r} -> {base!r}"
    op = urllib.parse.urlparse(old).path.rstrip("/") if old else ""
    if op and not u.path.strip("/"):
        base = base + op
        note = f"contract server {old!r} -> {base!r} (the contract's path {op!r} kept on the mock host)"
    spec["servers"] = [{"url": base}] + [s for s in (spec.get("servers") or [])[1:]]
    pathlib.Path(out_path).write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
    return note

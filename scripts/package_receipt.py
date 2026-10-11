"""Record a new receipt of the final package without touching earlier ones.

    python3 scripts/package_receipt.py --name r3 [--prev final/package/r2-...] [--zip upload.zip] \
        [--add <uploaded file>=<path in the package> ...] --source "how it arrived"

Makes final/package/<name>-<YYYYMMDD-HHMM>/ (İstanbul time): the previous receipt's files (copied, unchanged), then the
ZIP's files with their folder structure (a single top folder in the ZIP is taken as the package root), then the added
files at the given package paths. A path that already exists with other content is replaced in the NEW view only and
reported as changed; the earlier receipt keeps its copy. Unsafe ZIP paths (absolute, '..') stop the receipt.
Writes final/package/<name>.inventory.json (path, bytes, sha256, origin, source file and its modification time) and
final/package/<name>.diff.md next to the folder (never inside it, so the builder does not read them as case documents),
then reads the folder with the builder's own reader and prints every error and warning.
"""
import argparse, datetime, hashlib, json, os, pathlib, shutil, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKG = ROOT / "final" / "package"
sys.path.insert(0, str(ROOT / "builder"))


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def mtime(p):
    return datetime.datetime.fromtimestamp(os.stat(p).st_mtime, datetime.timezone.utc).isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True); ap.add_argument("--prev"); ap.add_argument("--zip")
    ap.add_argument("--add", action="append", default=[]); ap.add_argument("--source", required=True)
    a = ap.parse_args()
    stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime("%Y%m%d-%H%M")
    new = PKG / f"{a.name}-{stamp}"
    if new.exists() or (PKG / f"{a.name}.inventory.json").exists():
        sys.exit(f"{new} or {a.name}.inventory.json exists: choose another --name")
    files = {}   # package path -> record
    if a.prev:
        prev = pathlib.Path(a.prev)
        for p in sorted(prev.rglob("*")):
            if p.is_file():
                rel = str(p.relative_to(prev)).replace("\\", "/")
                files[rel] = {"src": p, "origin": f"carried from {prev.name}", "source_mtime": mtime(p)}
    if a.zip:
        z = zipfile.ZipFile(a.zip)
        names = [n for n in z.namelist() if not n.endswith("/") and not n.startswith("__MACOSX/") and not n.split("/")[-1].startswith("._")]
        for n in names:
            if n.startswith("/") or ".." in pathlib.PurePosixPath(n).parts or ":" in n.split("/")[0]:
                sys.exit(f"unsafe path in the ZIP: {n!r}; nothing written")
        tops = {n.split("/")[0] for n in names}
        strip = len(tops) == 1 and all("/" in n for n in names)
        tmp = PKG / f".{a.name}-zip"
        shutil.rmtree(tmp, ignore_errors=True)
        for n in names:
            rel = "/".join(n.split("/")[1:]) if strip else n
            out = tmp / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(n))
            files[rel] = {"src": out, "origin": f"zip {pathlib.Path(a.zip).name}" + (f" (top folder {next(iter(tops))!r} taken as root)" if strip else ""),
                          "source_mtime": mtime(a.zip), "replaces": files.get(rel)}
    for spec in a.add:
        src, _, rel = spec.partition("=")
        if not rel:
            sys.exit(f"--add needs <file>=<package path>: {spec!r}")
        files[rel] = {"src": pathlib.Path(src), "origin": f"added from {pathlib.Path(src).name}", "source_mtime": mtime(src), "replaces": files.get(rel)}
    new.mkdir(parents=True)
    inv, diff = [], {"added": [], "changed": [], "unchanged": [], "removed": []}
    prev_hash = {}
    if a.prev:
        prev = pathlib.Path(a.prev)
        prev_hash = {str(p.relative_to(prev)).replace("\\", "/"): sha(p) for p in prev.rglob("*") if p.is_file()}
    for rel, rec in sorted(files.items()):
        out = new / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rec["src"], out)
        h = sha(out)
        inv.append({"path": rel, "bytes": out.stat().st_size, "sha256": h, "origin": rec["origin"], "source": str(rec["src"]),
                    "source_mtime_utc": rec["source_mtime"]})
        if rel not in prev_hash:
            diff["added"].append(f"{rel} ({h[:16]})")
        elif prev_hash[rel] != h:
            diff["changed"].append(f"{rel} ({prev_hash[rel][:16]} -> {h[:16]})")
        else:
            diff["unchanged"].append(rel)
    diff["removed"] = [r for r in prev_hash if r not in files]
    shutil.rmtree(PKG / f".{a.name}-zip", ignore_errors=True)
    (PKG / f"{a.name}.inventory.json").write_text(json.dumps({"receipt": new.name, "source": a.source, "files": inv}, indent=1, ensure_ascii=False), encoding="utf-8")
    (PKG / f"{a.name}.diff.md").write_text(f"# {pathlib.Path(a.prev).name if a.prev else '(none)'} -> {new.name}\n"
                                           + "".join(f"- {k}: " + (", ".join(v) if v else "none") + "\n" for k, v in diff.items()), encoding="utf-8")
    import case_input
    r = case_input.load_case(new)
    print(f"receipt {new.relative_to(ROOT)}: {len(inv)} files")
    for k, v in diff.items():
        print(f"  {k}: {len(v)}" + (": " + ", ".join(v) if v and k != "unchanged" else ""))
    for w in r.get("warnings") or []:
        print("  NOTE", w)
    for e in r["errors"]:
        print("  PROBLEM", e)
    print("  reader:", "all files read" if not r["errors"] else f"{len(r['errors'])} file(s) not read")


if __name__ == "__main__":
    main()

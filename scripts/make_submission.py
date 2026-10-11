"""Prepare the submission files for ONE finished builder run (nothing is sent anywhere).

    python3 scripts/make_submission.py <candidate folder> --team "<team>" --member "<name>,<email>" [--member ...] \
        --repo <repo url> --mock-url <mock url> [--allow-failed-checks]

Writes, for the e-mail and the repository:
  submission.json                      team, members [{name, email}], repo, commit, run_command, workflow, trace, mock_url
  submission/final.workflow.json       e-mail copy of the run's export (byte copy of <candidate>/export.json)
  submission/final.trace-bundle.zip    the run's plain trace, its full model-session logs (traces/<run>.sessions/*.jsonl),
                                       its terminal log if any, and the candidate's manifest
"commit" is HEAD, which must already hold the run's outputs (a commit cannot hold a file naming its own hash, so
submission.json itself goes into the next commit). "workflow" and "trace" are the run's own files in that commit:
<candidate>/export.json and the plain trace (it names every session file with its sha256; the session logs are next to it).

Checks (nothing is written if one fails):
- release checks passed (or --allow-failed-checks), exported hash == tested hash, the trace exists and names this candidate
- the run's mock_url is the given one
- commit: HEAD is reported. HEAD may be later than the run's source commit (it holds the run's outputs), but between the
  two nothing that affects a build may differ: only traces/, candidates/, submission/, submission.json, research/ and
  .freya-agents.json may change. The working tree has no uncommitted change outside those paths.
- no secret value from the environment appears in the files that are submitted
Team and member names are never filled in by this script: they must be given.
"""
import argparse, hashlib, json, os, pathlib, re, shutil, subprocess, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
OUTPUT_PATHS = ("traces/", "candidates/", "submission/", "submission.json", "research/", ".freya-agents.json")


def git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=ROOT).decode().strip()


def changed_paths():
    """Paths with uncommitted changes (porcelain lines keep their leading status column; no strip before parsing)."""
    out = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).decode()
    return [l[3:] for l in out.splitlines() if len(l) > 3]


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def is_output(path):
    return any(path == o.rstrip("/") or path.startswith(o) for o in OUTPUT_PATHS)


def run_command(man, cand_case_folder):
    """The command as run, with the case folder replaced by {case_folder} (the organiser's placeholder)."""
    argv = list(man.get("argv") or [])
    if not argv:
        return None
    out = []
    for x in argv:
        if cand_case_folder and pathlib.Path(x).resolve() == cand_case_folder:
            out.append("{case_folder}")
        else:
            out.append(x)
    return "python3 builder/build.py " + " ".join(f'"{x}"' if " " in x else x for x in out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate"); ap.add_argument("--team", required=True)
    ap.add_argument("--member", action="append", required=True, help='"Name,email" (repeat per member)')
    ap.add_argument("--repo", required=True); ap.add_argument("--mock-url", required=True)
    ap.add_argument("--allow-failed-checks", action="store_true")
    ap.add_argument("--out-dir", default=str(ROOT), help="where submission.json and submission/ are written (default: repo root)")
    a = ap.parse_args()
    cand = (ROOT / a.candidate).resolve() if not pathlib.Path(a.candidate).is_absolute() else pathlib.Path(a.candidate)
    man = json.load(open(cand / "manifest.json", encoding="utf-8"))
    problems = []
    members = []
    for m in a.member:
        name, _, email = m.rpartition(",")
        if not name.strip() or "@" not in email:
            problems.append(f"member {m!r} is not 'Name,email'")
        members.append({"name": name.strip(), "email": email.strip()})
    if not man.get("release_checks_passed") and not a.allow_failed_checks:
        problems.append("release checks did not pass for this candidate")
    if not man.get("exported_hash") or man.get("exported_hash") != man.get("tested_hash"):
        problems.append("exported hash differs from the tested hash")
    if not (cand / "export.json").exists():
        problems.append("the candidate has no export.json")
    trace = pathlib.Path(man.get("trace", ""))
    trace = trace if trace.is_absolute() else ROOT / trace
    tt = trace.read_text(encoding="utf-8") if trace.exists() else ""
    if not tt:
        problems.append(f"trace {trace} not found")
    elif cand.name not in tt:
        problems.append("the trace does not name this candidate folder (not the same run)")
    inputs = man.get("inputs") or {}
    if inputs.get("mock_url") and inputs["mock_url"].rstrip("/") != a.mock_url.rstrip("/"):
        problems.append(f"the run used mock_url {inputs['mock_url']}, not {a.mock_url}")
    m = re.search(r"source commit ([0-9a-f]{40})", tt)
    run_commit = m.group(1) if m else None
    head = git("rev-parse", "HEAD")
    if not run_commit:
        problems.append("the trace records no source commit")
    else:
        changed = [p for p in git("diff", "--name-only", run_commit, head).splitlines() if p and not is_output(p)]
        if changed:
            problems.append("between the run's commit and HEAD, files that affect a build changed: " + ", ".join(changed[:10]))
    dirty = [p for p in changed_paths() if not is_output(p)]
    if dirty:
        problems.append("uncommitted changes outside the output paths: " + ", ".join(dirty[:10]))
    sessions = pathlib.Path(man["sessions"]) if man.get("sessions") else trace.with_suffix(".sessions")
    sessions = sessions if sessions.is_absolute() else ROOT / sessions
    session_files = sorted(sessions.glob("*.jsonl")) if sessions.exists() else []
    if man.get("model_calls") and not session_files:
        problems.append(f"the run made model calls but has no session logs in {sessions} (full session log missing)")
    for f in session_files:
        h = sha(f)[:16]
        if f"sha256 {h}" not in tt:
            problems.append(f"session log {f.name}: sha256 {h} is not the one the trace recorded at the end of the run")
    terminal = sorted(trace.parent.glob(f"final-*.terminal.log"))
    terminal = [t for t in terminal if cand.name in t.read_text(encoding="utf-8", errors="replace")]
    files = [trace] + session_files + terminal + [cand / "manifest.json", cand / "export.json"]
    # the reported commit (HEAD) must already hold the run's export, trace and session logs, unchanged
    for f in [trace, cand / "export.json", cand / "manifest.json"] + session_files:
        r = str(f.resolve().relative_to(ROOT))
        if subprocess.run(["git", "ls-files", "--error-unmatch", r], cwd=ROOT, capture_output=True).returncode != 0:
            problems.append(f"{r} is not committed: commit and push the run's outputs first, then write the submission")
        elif git("status", "--porcelain", "--", r):
            problems.append(f"{r} differs from the committed version")
    secrets = [(k, v) for k, v in os.environ.items() if re.search(r"(KEY|TOKEN|SECRET|PASSWORD)", k, re.I) and v and len(v) >= 8]
    for f in files:
        if f.exists():
            body = f.read_text(encoding="utf-8", errors="replace")
            for k, v in secrets:
                if v in body:
                    problems.append(f"{f.name} contains the value of {k}")
    if problems:
        print("NOT WRITTEN:\n- " + "\n- ".join(problems)); sys.exit(1)

    out = pathlib.Path(a.out_dir).resolve()
    sub_dir = out / "submission"
    sub_dir.mkdir(parents=True, exist_ok=True)
    wf = sub_dir / "final.workflow.json"
    shutil.copyfile(cand / "export.json", wf)
    bundle = sub_dir / "final.trace-bundle.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files[:-1]:
            if f.exists():
                z.write(f, str(f.resolve().relative_to(ROOT)))
    case = pathlib.Path(inputs["brief_arg"]).resolve() if inputs.get("brief_arg") and pathlib.Path(inputs["brief_arg"]).is_dir() else None
    sub = {"team": a.team, "members": members, "repo": a.repo, "commit": head,
           "run_command": run_command(man, case) or "(not recorded)",
           "workflow": str((cand / "export.json").resolve().relative_to(ROOT)), "trace": str(trace.resolve().relative_to(ROOT)),
           "mock_url": a.mock_url}
    (out / "submission.json").write_text(json.dumps(sub, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(sub, indent=1, ensure_ascii=False))
    print(f"\nrun commit {run_commit} -> reported commit (HEAD) {head}: no build-affecting change between them; "
          f"export, trace and session logs are committed in it")
    print(f"workflow copy sha256 {sha(wf)[:16]} == export {sha(cand / 'export.json')[:16]}")
    print(f"trace bundle: {bundle.relative_to(out)} ({len(session_files)} session log(s), {len(terminal)} terminal log(s))")
    print("e-mail attachments: submission.json, submission/final.workflow.json, submission/final.trace-bundle.zip "
          "(commit and push them first; the e-mail is sent by a person)")


if __name__ == "__main__":
    main()

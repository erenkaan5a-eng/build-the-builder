"""Write submission.json for ONE finished builder run: the export and the trace of that same run.

    python3 scripts/make_submission.py <candidate folder> --team "<team>" --member "<name>" [--member ...] \
        --repo <repo url> --mock-url <mock url> [--run-command "<command as run>"] [--out submission.json]

Checks before writing: the candidate's manifest says release checks passed (or --allow-failed-checks), its export hash
equals the tested hash, its trace file exists and names this candidate folder, and the commit is the current HEAD with
a clean builder/ tree. Team and member names are never filled in by this script: they must be given.
"""
import argparse, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))


def git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=ROOT).decode().strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate"); ap.add_argument("--team", required=True); ap.add_argument("--member", action="append", required=True)
    ap.add_argument("--repo", required=True); ap.add_argument("--mock-url", required=True); ap.add_argument("--run-command")
    ap.add_argument("--out", default="submission.json"); ap.add_argument("--allow-failed-checks", action="store_true")
    a = ap.parse_args()
    cand = (ROOT / a.candidate).resolve() if not pathlib.Path(a.candidate).is_absolute() else pathlib.Path(a.candidate)
    man = json.load(open(cand / "manifest.json", encoding="utf-8"))
    problems = []
    if not man.get("release_checks_passed") and not a.allow_failed_checks:
        problems.append("release checks did not pass for this candidate")
    if not man.get("exported_hash") or man.get("exported_hash") != man.get("tested_hash"):
        problems.append("exported hash differs from the tested hash")
    trace = pathlib.Path(man.get("trace", ""))
    if not trace.is_absolute():
        trace = ROOT / trace
    if not trace.exists():
        problems.append(f"trace {trace} not found")
    elif cand.name not in trace.read_text(encoding="utf-8"):
        problems.append("the trace does not name this candidate folder (not the same run)")
    if (man.get("inputs") or {}).get("mock_url") and man["inputs"]["mock_url"].rstrip("/") != a.mock_url.rstrip("/"):
        problems.append(f"the run used mock_url {man['inputs']['mock_url']}, not {a.mock_url}")
    tt = trace.read_text(encoding="utf-8") if trace.exists() else ""
    head = git("rev-parse", "HEAD")
    if "source commit " in tt and f"source commit {head}" not in tt:
        problems.append("the run was made from another commit than HEAD: check out that commit before writing the submission")
    if git("status", "--porcelain", "--", "builder"):
        problems.append("builder/ has uncommitted changes")
    if problems:
        print("NOT WRITTEN:\n- " + "\n- ".join(problems)); sys.exit(1)
    rel = lambda p: str(pathlib.Path(p).resolve().relative_to(ROOT))
    sub = {"team": a.team, "members": a.member, "repo": a.repo, "commit": git("rev-parse", "HEAD"),
           "run_command": a.run_command or f"python3 builder/build.py {man['inputs'].get('brief_arg')} {man['inputs'].get('tool_api_arg')}",
           "workflow": rel(cand / "export.json"), "trace": rel(trace), "mock_url": a.mock_url}
    pathlib.Path(a.out).write_text(json.dumps(sub, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(sub, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

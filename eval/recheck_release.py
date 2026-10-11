"""Re-run the release behaviour checks on a candidate's PUBLISHED workflow without rebuilding or changing it.

    FREYA_AUTH_VIA_PROXY=1 python3 eval/recheck_release.py candidates/<slot>/<time> [--practice CASE_ID]

Use it when the build's own check could not run (for example a platform 5xx on the chat API). It reads the live
workflow, requires its content hash to equal the candidate's exported hash (so the checked agent is the exported one),
runs builder/behavior.py's checks, and writes recheck-<time>.json next to the manifest. The manifest is not edited.
"""
import argparse, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
import common, behavior  # noqa: E402
from build import _retry_5xx  # noqa: E402  (same bounded platform-5xx retry as the build's own check)


class _Trace:
    def __init__(self, path):
        self.f = open(path, "a", encoding="utf-8")

    def log(self, kind, msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} [{kind}] {msg}"
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate")
    ap.add_argument("--practice")
    ap.add_argument("--raw-answers", action="store_true", help="practice with the identity values unformatted (ISO date regression)")
    a = ap.parse_args()
    cand = pathlib.Path(a.candidate)
    man = json.load(open(cand / "manifest.json", encoding="utf-8"))
    pol = json.load(open(cand / "policy.json", encoding="utf-8"))
    exported = common.wf_hash(json.load(open(cand / "export.json", encoding="utf-8"))["workflow"])
    live = common.wf_hash(common.get_workflow(man["workflow_id"]))
    pv = common.published_version(man["workflow_id"])
    tr = _Trace(ROOT / "traces" / f"{man['slot']}-recheck-{time.strftime('%Y%m%d-%H%M%S')}.log")
    tr.log("RECHECK", f"candidate {cand} workflow {man['workflow_id']} published version {pv['version_number']} live hash {live} exported hash {exported}")
    out = {"raw_answers": bool(a.raw_answers), "candidate": str(cand), "workflow_id": man["workflow_id"], "published_version": pv["version_number"], "live_hash": live, "exported_hash": exported, "checks": []}
    if live != exported:
        tr.log("RECHECK", "live workflow differs from the exported candidate: not checked")
    else:
        budget = common.Budget(10)
        res = _retry_5xx(lambda: behavior.structural(man["workflow_id"], pol, tr), budget, tr)
        if a.practice:
            pres, _ = _retry_5xx(lambda: behavior.practice(man["workflow_id"], a.practice, tr, raw_answers=a.raw_answers), budget, tr)
            res += pres
        out["checks"] = [[n, ok] for n, ok, _ in res]
    out["all_passed"] = bool(out["checks"]) and all(ok for _, ok in out["checks"])
    p = cand / f"recheck-{time.strftime('%Y%m%d-%H%M%S')}.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    tr.log("RECHECK", f"{'PASSED' if out['all_passed'] else 'FAILED'}; written {p}")


if __name__ == "__main__":
    main()

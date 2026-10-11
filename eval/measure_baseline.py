"""One repetition of a fixed candidate on public cases, recorded run by run (development measurement).

    FREYA_AUTH_VIA_PROXY=1 python3 eval/measure_baseline.py <label> <slot> <brief A|B> <cases comma list> <rep> \
        <expected version number> <expected content hash16>

Before the simulation it checks that the slot's PUBLISHED version is the expected one and that the live workflow
content hash equals the candidate's exported hash; it refuses to run otherwise (no measurement of another version).
It runs tools/run_cases_cloud.py once (--reps 1), then records for every case: pass/fail and the scorer's reasons, the
bank ledger calls with their arguments, the simulation's agentVersionNumber/agentVersionId (execution evidence), call
id, slowest turn and ended reason. Customer/session ids of the practice bank are NOT written to the repository.
A run whose simulation did not complete, or with no judge verdict, is marked platform_issue (kept, counted apart).
Output: research/cloud-runs/baseline/<label>-rep<k>.json and one line per run in research/cloud-runs/baseline/runs.jsonl.
"""
import json, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import cloud_proxy  # noqa: E402
cloud_proxy.apply()
from score import http  # noqa: E402

OUT = ROOT / "research" / "cloud-runs" / "baseline"
TMP = pathlib.Path("/tmp") / "measure_baseline"


def main():
    label, slot, brief, cases, rep, want_ver, want_hash = sys.argv[1:8]
    extra = sys.argv[8:]          # passed to run_cases (e.g. --style asks_back, --cases experiments/custom/cases-dev.json)
    rep, want_ver = int(rep), int(want_ver)
    st = json.load(open(ROOT / ".freya-agents.json"))[slot]
    wid, agent = st["workflow_id"], st["agent_id"]
    vs = common.freya.api("GET", f"/api/v2/versions/workflow/{wid}", workspaceId=common.freya.workspace_id())["versions"]
    pub = [v for v in vs if v.get("isPublished")]
    live = common.wf_hash(common.get_workflow(wid))
    pre = {"published": [(v["versionNumber"], v["id"]) for v in pub], "live_hash": live}
    if not pub or pub[0]["versionNumber"] != want_ver or live != want_hash:
        print("REFUSED: the live candidate is not the expected one", json.dumps(pre))
        sys.exit(3)
    TMP.mkdir(parents=True, exist_ok=True)
    raw = TMP / f"{label}-rep{rep}.json"
    t0 = time.time()
    p = subprocess.run([sys.executable, str(ROOT / "tools" / "run_cases_cloud.py"), agent, "--brief", brief, "--only", cases, "--out", str(raw)] + extra,
                       capture_output=True, text=True)
    log = p.stdout + p.stderr
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{label}-rep{rep}.log").write_text(log, encoding="utf-8")
    rec = {"label": label, "slot": slot, "workflow_id": wid, "agent_id": agent, "expected_version": want_ver, "expected_hash": want_hash,
           "precheck": pre, "run_cases_extra_args": extra, "rep": rep, "cases": cases.split(","), "exit_code": p.returncode, "seconds": round(time.time() - t0), "runs": []}
    if p.returncode != 0 or not raw.exists():
        rec["platform_issue"] = "run_cases did not finish: " + log[-600:]
    else:
        res = json.load(open(raw))
        rec.update({"simulation_id": res["simulation_id"], "iteration_id": res["iteration_id"]})
        it = common.freya.get_iteration(res["simulation_id"], res["iteration_id"])
        by_call = {r.get("callId"): r for r in it["runs"]}
        for row in res["rows"]:
            sim = by_call.get(row.get("call_id")) or {}
            led = http("/v1/practice/ledger/" + row["customer_id"])
            calls = []
            for c in led.get("calls") or []:
                a = c.get("args") or c.get("request") or {}
                calls.append([c.get("tool"), {k: a.get(k) for k in ("field", "answer", "product_id", "amount", "date", "reason", "outcome", "queue", "time") if k in a},
                              (c.get("result") or {}).get("ok") if isinstance(c.get("result"), dict) else None])
            judge_missing = any("no verdict" in f for f in row["failed"])
            rec["runs"].append({"case": row["id"], "rep": rep, "pass": row["pass"], "failed": row["failed"], "call_id": row.get("call_id"),
                                "agentVersionNumber": sim.get("agentVersionNumber"), "agentVersionId": sim.get("agentVersionId"),
                                "judge_outcome": sim.get("outcome"), "slowest_turn_s": row.get("slowest_turn_s"), "ended": row.get("ended"),
                                "ledger": {k: led.get(k) for k in ("outcome", "reason", "promises", "notes", "callbacks", "transfers")}, "ledger_calls": calls,
                                "version_ok": sim.get("agentVersionNumber") == want_ver,
                                "platform_issue": "judge gave no verdict" if judge_missing else None})
        raw.unlink()
    (OUT / f"{label}-rep{rep}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    with open(OUT / "runs.jsonl", "a", encoding="utf-8") as f:
        for r in rec["runs"]:
            f.write(json.dumps({"label": label, "slot": slot, "version": want_ver, "hash": want_hash, "case": r["case"], "rep": rep, "pass": r["pass"],
                                "agentVersionNumber": r["agentVersionNumber"], "platform_issue": r["platform_issue"], "simulation_id": rec.get("simulation_id"),
                                "call_id": r["call_id"]}) + "\n")
        if rec.get("platform_issue"):
            f.write(json.dumps({"label": label, "slot": slot, "version": want_ver, "hash": want_hash, "case": cases, "rep": rep, "pass": None,
                                "platform_issue": rec["platform_issue"][:300]}) + "\n")
    for r in rec["runs"]:
        print(("PASS" if r["pass"] else "FAIL"), r["case"], "rep", rep, "v", r["agentVersionNumber"], "|", "; ".join(r["failed"])[:240])
    if rec.get("platform_issue"):
        print("PLATFORM ISSUE:", rec["platform_issue"][:300])


if __name__ == "__main__":
    main()

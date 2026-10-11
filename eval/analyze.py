"""Dump compact transcripts of a run_cases.py result file.

    python eval/analyze.py results/run.json [--all]
Writes results/transcripts/<case>.txt (agent/customer lines, tool calls with args and results, node changes).
"""
import json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "builder"))
import common  # noqa: E402

run = json.load(open(sys.argv[1], encoding="utf-8"))
outdir = common.KIT / "results" / "transcripts"
outdir.mkdir(parents=True, exist_ok=True)
for row in run["rows"]:
    if row["pass"] and "--all" not in sys.argv:
        continue
    lines = [f"{row['id']} pass={row['pass']} tools={' > '.join(row['tools'])}"] + [f"FAIL: {f}" for f in row["failed"]]
    if row.get("call_id"):
        call = common.freya.get_call(row["call_id"])
        lines.append(f"endedReason={call.get('endedReason')} duration={call.get('duration')}")
        for m in call.get("messages", []):
            role, msg, t = m.get("role"), m.get("message") or "", m.get("secondsFromStart")
            if role in ("assistant", "user"):
                lines.append(f"[{t}] {role.upper()}: {msg}")
            elif role == "system":
                try:
                    ev = json.loads(msg)
                except Exception:
                    continue
                e = ev.get("event")
                if e == "node_enter":
                    lines.append(f"[{t}]   -> node {ev.get('node')} (from {ev.get('from_node')})")
                elif e == "function_call_start":
                    args = ev.get("args") or {}
                    lines.append(f"[{t}]   CALL {ev.get('function')} body={json.dumps(args.get('body', args))[:300]}")
                elif e == "function_call_complete":
                    res = ev.get("result") or {}
                    lines.append(f"[{t}]   RESULT {ev.get('function')} {json.dumps(res.get('data', res) if isinstance(res, dict) else res)[:300]}")
                elif e == "function_call_error":
                    lines.append(f"[{t}]   CALL-ERROR {ev.get('function')} {str(ev.get('error') or ev.get('message') or ev)[:300]}")
                elif e == "error":
                    lines.append(f"[{t}]   ERROR {ev.get('message')} {str(ev.get('details'))[:200]}")
    (outdir / f"{row['id']}.txt").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", outdir / f"{row['id']}.txt")

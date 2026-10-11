"""builder/common.py publish(): a slot id stored in the committed .freya-agents.json may not exist in another workspace
(an organiser running the builder from a clean checkout with their own key). A clear 404/403/400 on reading that
workflow leads to a new workflow (the old entry is kept under '<slot>@unreachable-<time>'); a platform 5xx is raised,
so a passing outage never creates duplicate workflows. Fake Freya client and a temporary slot file: no network."""
import json, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "builder"))
sys.path.insert(0, str(ROOT / "tests"))
import common  # noqa: E402
from negotiation_harness import check, FAILS  # noqa: E402


class Trace:
    def __init__(self): self.lines = []
    def log(self, kind, msg): self.lines.append((kind, msg))


def run(get_status, stored, create_status=None):
    calls = []
    def api(method, path, body=None, **params):
        calls.append((method, path))
        if method == "GET" and path.startswith("/api/v2/workflow/"):
            if get_status:
                raise RuntimeError(f"GET {path} -> {get_status}: not here")
            return {"workflow": {"id": path.rsplit("/", 1)[-1]}}
        if method == "GET" and path.startswith("/api/v2/versions/workflow/"):
            return {"versions": [{"versionNumber": 1, "id": "v1", "isPublished": True}]}
        raise AssertionError(f"unexpected call {method} {path}")
    fake = type("F", (), {})()
    fake.api = api
    fake.workspace_id = lambda: "ws"
    def create(name, wf):
        calls.append(("CREATE", name))
        if create_status:
            raise RuntimeError(f"POST /api/v2/workflow -> {create_status}: busy")
        return {"workflow_id": "new-id", "agent_id": "new-agent"}
    fake.create_workflow = create
    fake.update_workflow = lambda wid, wf: calls.append(("UPDATE", wid))
    tmp = pathlib.Path(tempfile.mkdtemp())
    if stored:
        (tmp / ".freya-agents.json").write_text(json.dumps({"s": {"workflow_id": "theirs", "agent_id": "a"}}))
    real_freya, real_kit = common.freya, common.KIT
    common.freya, common.KIT = fake, tmp
    tr = Trace()
    try:
        out, err = common.publish("s", {"nodes": {}}, tr), None
    except (RuntimeError, common.CreateFailed) as e:
        out, err = None, f"{type(e).__name__}: {e}"
    finally:
        common.freya, common.KIT = real_freya, real_kit
    state = json.loads((tmp / ".freya-agents.json").read_text()) if (tmp / ".freya-agents.json").exists() else {}
    return out, err, calls, state, tr.lines


for code in (404, 403, 400):
    out, err, calls, state, lines = run(code, True)
    check(f"P1 stored id answered {code}: a new workflow is created and updated", err is None and any(c[0] == "CREATE" for c in calls)
          and ("UPDATE", "new-id") in calls and ("UPDATE", "theirs") not in calls and out["workflow_id"] == "new-id", (err, calls))
    check(f"P2 {code}: the old entry is kept under an @unreachable key, the slot points to the new workflow",
          state.get("s", {}).get("workflow_id") == "new-id" and any(k.startswith("s@unreachable-") and v["workflow_id"] == "theirs" for k, v in state.items()), state)
    check(f"P3 {code}: the trace says why a new workflow was made", any("not in this workspace" in m for _, m in lines), lines)

out, err, calls, state, lines = run(502, True)
check("P4 a 5xx while reading the stored workflow is raised: no new workflow, nothing updated, slot file unchanged",
      err and "-> 502" in err and not [c for c in calls if c[0] in ("CREATE", "UPDATE")] and state == {"s": {"workflow_id": "theirs", "agent_id": "a"}}, (err, calls, state))

out, err, calls, state, lines = run(None, True)
check("P5 a reachable stored workflow is updated in place (no new workflow)",
      err is None and ("UPDATE", "theirs") in calls and not [c for c in calls if c[0] == "CREATE"] and out["version_id"] == "v1", (err, calls))

out, err, calls, state, lines = run(None, False)
check("P6 no stored slot: a workflow is created without a read first",
      err is None and calls[0][0] == "CREATE" and ("UPDATE", "new-id") in calls and state["s"]["workflow_id"] == "new-id", calls)
out, err, calls, state, lines = run(404, True, create_status=503)
check("P7 a 5xx while creating is raised as CreateFailed (not a RuntimeError, so the build's 5xx retry does not repeat a create)",
      err and err.startswith("CreateFailed") and "-> 503" in err and not issubclass(common.CreateFailed, RuntimeError)
      and [c[0] for c in calls].count("CREATE") == 1, (err, calls))
print("FAILURES:", len(FAILS)); sys.exit(1 if FAILS else 0)

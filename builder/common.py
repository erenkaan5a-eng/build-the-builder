"""Shared pieces of the builder: env loading, trace, deadline, Freya publish/test/export, workflow hashing."""
import hashlib, json, os, pathlib, re, sys, time

KIT = pathlib.Path(__file__).resolve().parent.parent


def load_env(path=KIT / "env.sh"):
    """Read `export KEY=value` lines from env.sh into os.environ (does not override values already set)."""
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)=(.*)$", line)
        if not m:
            continue
        val = m.group(2).split(" #")[0].strip().strip('"').strip("'")
        os.environ.setdefault(m.group(1), val)
    return True


load_env()
sys.path.insert(0, str(KIT))
import freya  # noqa: E402  (reads FREYA_API_KEY at import time, so env must be loaded first)
sys.path.insert(0, str(KIT / "tools"))
import cloud_proxy  # noqa: E402  (opt-in FREYA_AUTH_VIA_PROXY=1: headers left to a credential-injecting proxy)
PROXY_MODE = cloud_proxy.apply()


class Budget:
    """One wall-clock budget for the whole build: main path, repair, fallback and final checks all draw from it."""

    def __init__(self, minutes):
        self.start = time.time()
        self.end = self.start + minutes * 60

    def left(self):
        return self.end - time.time()

    def elapsed(self):
        return time.time() - self.start


class Trace:
    """Plain-text trace: start/end, every model call (model + one-line purpose), what was created on Freya, tests."""

    def __init__(self, slot):
        (KIT / "traces").mkdir(exist_ok=True)
        base = f"{slot}-{time.strftime('%Y%m%d-%H%M%S')}"
        self.path, n = KIT / "traces" / f"{base}.log", 1
        while self.path.exists():          # a second run in the same second never overwrites an earlier trace
            n += 1
            self.path = KIT / "traces" / f"{base}-{n}.log"
        self.f = self.path.open("x", encoding="utf-8")
        self.model_calls = 0

    def log(self, kind, msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} [{kind}] {msg}"
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()

    def model_call(self, model, purpose, usage=None):
        self.model_calls += 1
        extra = f" usage={json.dumps(usage)}" if usage else ""
        self.log("MODEL", f"#{self.model_calls} model={model} purpose={purpose}{extra}")


def normalize(workflow):
    """Canonical form of a workflow for hashing: layout-only keys removed, keys sorted."""
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in sorted(o.items()) if k not in ("nodePositions", "position")}
        if isinstance(o, list):
            return [strip(x) for x in o]
        return o
    return strip(workflow)


def wf_hash(workflow):
    return hashlib.sha256(json.dumps(normalize(workflow), sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def get_workflow(workflow_id):
    return freya.api("GET", f"/api/v2/workflow/{workflow_id}", workspaceId=freya.workspace_id())["workflow"]["workflow"]


def published_version(workflow_id):
    vs = freya.api("GET", f"/api/v2/versions/workflow/{workflow_id}", workspaceId=freya.workspace_id())["versions"]
    pub = [v for v in vs if v.get("isPublished")]
    v = max(pub or vs, key=lambda v: v["versionNumber"])
    return {"version_number": v["versionNumber"], "version_id": v["id"], "is_published": bool(v.get("isPublished"))}


class CreateFailed(Exception):
    """Creating a workflow failed; deliberately not a RuntimeError so platform-5xx retries skip it."""


def publish(slot, workflow, trace):
    """Create or update the slot's workflow, make sure the event model is set, publish. Returns ids + published version."""
    state_file = KIT / ".freya-agents.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    if slot in state:
        # the slot file is committed: in another workspace (e.g. an organiser's clean checkout) its id does not exist there.
        # Only a clear 'not found / not allowed' leads to a new workflow; a platform 5xx is raised (no duplicate workflows).
        try:
            freya.api("GET", f"/api/v2/workflow/{state[slot]['workflow_id']}", workspaceId=freya.workspace_id())
        except RuntimeError as e:
            if not re.search(r"-> (404|403|400):", str(e)):
                raise
            old = state.pop(slot)
            state[f"{slot}@unreachable-{time.strftime('%Y%m%d-%H%M%S')}"] = old
            trace.log("FREYA", f"stored workflow {old['workflow_id']} for slot {slot} is not in this workspace ({str(e)[:80]}); a new one is created")
    if slot not in state:
        try:
            made = freya.create_workflow(f"{slot} {time.strftime('%m%d-%H%M%S')}", workflow)
        except RuntimeError as e:
            # not a RuntimeError, so build.py's 5xx retry does not repeat it: a lost answer could leave a second workflow
            raise CreateFailed(f"creating the workflow failed (not retried): {e}") from None
        state[slot] = made
        state_file.write_text(json.dumps(state, indent=1))
        trace.log("FREYA", f"created workflow {made['workflow_id']} agent {made['agent_id']}")
    wid = state[slot]["workflow_id"]
    freya.update_workflow(wid, workflow)  # saves, sets the event model, publishes the newest version
    pv = published_version(wid)
    trace.log("FREYA", f"published workflow {wid} version {pv['version_number']} ({pv['version_id']})")
    return {**state[slot], **pv}


def chat_smoke(workflow_id, variables, trace, message="Hello?"):
    """One chat turn against the published workflow. Returns the agent's first reply (or raises)."""
    r = freya.api("POST", "/api/v2/chat/message", {"workflowId": workflow_id, "message": message, "customerVariables": variables})
    reply = r.get("response") or ""
    trace.log("TEST", f"chat smoke callId={r.get('callId')} reply={reply[:200]!r}")
    return r


def counts(workflow):
    nodes = workflow.get("nodes", {})
    tools = sum(len(n.get("tools") or []) + len(n.get("pre_actions") or []) for n in nodes.values()) + len(workflow.get("tools") or [])
    return {"nodes": len(nodes), "global_nodes": len(workflow.get("global_nodes") or {}), "tool_functions": tools}

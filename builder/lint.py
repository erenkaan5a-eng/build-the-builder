"""Static checks of a workflow against the platform rules (docs/) and the brief's tool API file.

    python builder/lint.py <workflow.json> <tool_api.json> [--dry-run]
Prints one line per problem and OK when there is none. Exit code 1 on problems.
"""
import json, re, sys

NODE_TYPES = {"conversation", "api_request", "code", "end_call"}
ENGINE_HANDLERS = {"__function__:end_call", "__function__:code_exec"}


def load_api(path):
    spec = json.load(open(path, encoding="utf-8"))
    base = (spec.get("servers") or [{}])[0].get("url", "").rstrip("/")
    ops = {}
    for p, item in spec.get("paths", {}).items():
        op = item.get("post") or item.get("get") or {}
        schema = (((op.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema") or {}
        resp = ((((op.get("responses") or {}).get("200") or {}).get("content") or {}).get("application/json") or {}).get("schema") or {}
        ops[p.strip("/")] = {"url": base + p, "props": schema.get("properties", {}), "required": schema.get("required", []),
                             "resp": resp.get("properties", {})}
    return base, ops


def lint(wf, api_path):
    probs = []
    base, ops = load_api(api_path)
    s = json.dumps(wf)
    if "null" in re.findall(r":\s*(null)", s):
        probs.append("warn: a value is null (docs say strict; Freya dry-run accepted nulls in the kit example)")
    if not wf.get("test_variables"):
        probs.append("test_variables is empty: put the brief's example call variables there (the builder's smoke test uses them)")
    if "agent_config" in wf:
        probs.append("agent_config must be left out")
    nodes, gnodes = wf.get("nodes", {}), wf.get("global_nodes", {}) or {}
    if wf.get("initial_node") not in nodes:
        probs.append(f"initial_node {wf.get('initial_node')!r} is not a node")
    allnodes = {**nodes, **gnodes}
    has_end = False
    close_calls = 0
    for key, n in allnodes.items():
        where = f"node {key}"
        nt = n.get("node_type")
        if nt not in NODE_TYPES:
            probs.append(f"{where}: node_type {nt!r} not one of {sorted(NODE_TYPES)}")
        if n.get("name") != key:
            probs.append(f"{where}: name {n.get('name')!r} differs from key")
        if nt == "end_call":
            has_end = True
        if n.get("tools") and nt != "conversation":
            probs.append(f"{where}: tools only work on conversation nodes (they are silently dropped)")
        if n.get("pre_actions") and nt == "conversation":
            probs.append(f"{where}: pre_actions are dropped on conversation nodes")
        for t in n.get("transitions") or []:
            tgt = t.get("target_node")
            if tgt not in allnodes and tgt != "__previous__":
                probs.append(f"{where}: transition to unknown node {tgt!r}")
            c = t.get("condition") or {}
            if c.get("logic") == "and":
                probs.append(f"{where}: top-level condition logic must be 'or'")
        if n.get("passthrough"):
            tr = n.get("transitions") or []
            if not tr or (tr[-1].get("condition") or {}).get("operator") != "always":
                probs.append(f"{where}: passthrough node must end with an 'always' transition")
        if n.get("max_node_turns") and not n.get("max_turn_transition"):
            probs.append(f"warn: {where}: max_node_turns without max_turn_transition has no effect")
        for e in n.get("extraction_schema") or []:
            if "min_confidence" not in e:
                probs.append(f"{where}: extraction {e.get('name')} has no min_confidence (default 0.95 drops values silently)")
        for m in n.get("response_mapping") or []:
            if not str(m.get("path", "")).startswith("data."):
                probs.append(f"{where}: response_mapping path {m.get('path')!r} should start with 'data.'")
        for t in n.get("pre_actions") or []:
            url = (((t.get("function") or {}).get("parameters") or {}).get("properties") or {}).get("url", {}).get("default", "")
            if url.startswith(base):
                check_mappings(n.get("response_mapping"), url[len(base):].strip("/"), where, ops, probs)
        fns = list(n.get("tools") or []) + list(n.get("pre_actions") or [])
        if n.get("terminal"):
            fns.append(n["terminal"])
        for t in fns:
            if (t.get("function") or {}).get("handler") == "__function__:end_call":
                has_end = True
            close_calls += check_fn(t, where, ops, base, probs)
    for t in wf.get("tools") or []:
        close_calls += check_fn(t, "workflow tools", ops, base, probs)
        if not (t.get("config") or {}).get("alwaysRunsAt"):
            probs.append("workflow-level tool without config.alwaysRunsAt never runs")
    if not has_end:
        probs.append("nothing ends the call (no end_call node or end_call tool)")
    if close_calls == 0 and "close_call" in ops:
        probs.append("close_call is never called")
    return probs


def check_mappings(mappings, op, where, ops, probs):
    """Observed on Freya (run fb-a-v4-f2): a response field that is a list is NOT stored in the mapped variable;
    only the flattened keys <node or tool>_response.data.<field>.<i>.<key> exist."""
    for m in mappings or []:
        path = str(m.get("path", ""))
        if not path.startswith("data.") or op not in ops:
            continue
        field = path[5:].split(".")[0]
        typ = (ops[op]["resp"].get(field) or {}).get("type")
        if typ in ("array", "object") and path == "data." + field:
            probs.append(f"{where}: mapping {path!r} -> {m.get('variable')!r} maps a {typ}; observed: lists are not stored in the "
                         f"variable. Read the flattened keys <name>_response.{path}.<i>.<field> in a code node instead")


def check_fn(t, where, ops, base, probs):
    f = t.get("function") or {}
    h = f.get("handler", "")
    name = f.get("name", "")
    props = (f.get("parameters") or {}).get("properties") or {}
    if h == "__function__:code_exec":
        code = (props.get("code") or {}).get("default", "")
        if "{{" in code or "}}" in code:
            probs.append(f"{where}: code_exec code contains '{{{{' or '}}}}'")
        if re.search(r"^\s*(global|nonlocal)\s", code, re.M):
            # the platform runs code inside a function: 'global' rebinding fails there (seen in a chat run, 11 Oct)
            probs.append(f"{where}: code_exec code uses a global/nonlocal statement (the platform runs code inside a function)")
        try:
            compile("def _run(vars, params):\n" + "\n".join("    " + l for l in code.splitlines()) + "\n", "<code>", "exec")
        except SyntaxError as e:
            probs.append(f"{where}: code_exec code does not compile inside a function: {e}")
        return 0
    if h in ENGINE_HANDLERS:
        return 0
    if h != "__function__:api_call":
        probs.append(f"{where}: tool {name} has unknown handler {h!r}")
        return 0
    if "const" in json.dumps(props.get("url", {})):
        probs.append(f"{where}: tool {name} uses const for url (use default)")
    url = (props.get("url") or {}).get("default", "")
    if not url.startswith(base):
        probs.append(f"{where}: tool {name} calls {url!r}, outside the tool API server {base!r}")
        return 0
    op = url[len(base):].strip("/")
    if op not in ops:
        probs.append(f"{where}: tool {name} calls unknown endpoint {op!r}")
        return 0
    body = (props.get("body") or {}).get("properties") or {}
    for field, spec in body.items():
        if field not in ops[op]["props"]:
            probs.append(f"{where}: {op} body field {field!r} is not in the tool API")
            continue
        allowed = ops[op]["props"][field].get("enum")
        used = spec.get("enum")
        if allowed and used and set(used) - set(allowed):
            probs.append(f"{where}: {op}.{field} enum {sorted(set(used) - set(allowed))} not allowed by the tool API")
        d = spec.get("default")
        if allowed and isinstance(d, str) and "{{" not in d and d not in allowed:
            probs.append(f"{where}: {op}.{field} default {d!r} not allowed by the tool API")
    for req in ops[op]["required"]:
        if req not in body:
            probs.append(f"{where}: {op} misses required body field {req!r}")
    for m in t.get("response_mapping") or []:
        if not str(m.get("path", "")).startswith("data."):
            probs.append(f"{where}: tool {name} mapping path {m.get('path')!r} should start with 'data.'")
    check_mappings(t.get("response_mapping"), op, where, ops, probs)
    return 1 if op == "close_call" else 0


if __name__ == "__main__":
    wf = json.load(open(sys.argv[1], encoding="utf-8"))
    probs = lint(wf, sys.argv[2])
    if "--dry-run" in sys.argv and not [p for p in probs if not p.startswith("warn:")]:
        sys.path.insert(0, __import__("os").path.dirname(__file__))
        import common  # noqa: F401  loads env.sh
        try:
            common.freya.validate_workflow("lint dry run", wf)
        except Exception as e:
            probs.append("Freya dry-run rejected the workflow: " + str(e)[:1200])
    errs = [p for p in probs if not p.startswith("warn:")]
    for p in probs:
        print("WARNING:" if p.startswith("warn:") else "PROBLEM:", p)
    print("OK" if not errs else f"{len(errs)} problem(s)")
    sys.exit(1 if errs else 0)

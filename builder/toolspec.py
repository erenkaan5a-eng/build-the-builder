"""Read a tool API (OpenAPI) file deterministically: server URL, and for each operation its request and response fields."""
import json


def deref(spec):
    """Inline the contract's local references ({"$ref": "#/components/schemas/X"}); sibling keys of a $ref are kept.
    A reference cycle or a reference that does not resolve is left as it is (the validation then reports missing fields)."""
    def get(ptr):
        node = spec
        for part in ptr.lstrip("#/").split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def walk(x, seen):
        if isinstance(x, dict):
            ref = x.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/") and ref not in seen:
                target = get(ref)
                if isinstance(target, dict):
                    merged = {**walk(target, seen | {ref}), **{k: walk(v, seen) for k, v in x.items() if k != "$ref"}}
                    return merged
            return {k: walk(v, seen) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v, seen) for v in x]
        return x
    return walk(spec, frozenset())


def ok_response(op):
    """The schema of the operation's success answer: 200, else the first 2xx the contract lists."""
    rs = op.get("responses") or {}
    code = "200" if "200" in rs else next((c for c in sorted(rs) if str(c).startswith("2")), None)
    return ((((rs.get(code) or {}) if code else {}).get("content") or {}).get("application/json") or {}).get("schema") or {}


def load(path):
    spec = deref(json.load(open(path, encoding="utf-8")))
    base = (spec.get("servers") or [{}])[0].get("url", "").rstrip("/")
    ops = {}
    for p, item in spec.get("paths", {}).items():
        op = item.get("post") or item.get("get") or {}
        req = (((op.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema") or {}
        resp = ok_response(op)
        rprops = resp.get("properties", {})
        items = {k: (v.get("items") or {}).get("properties", {}) for k, v in rprops.items() if v.get("type") == "array"}
        ops[p.strip("/")] = {"url": base + p, "summary": op.get("summary", ""), "request": req.get("properties", {}),
                             "required": req.get("required", []), "response": rprops, "items": items}
    return {"base": base, "ops": ops, "description": (spec.get("info") or {}).get("description", "")}


def summary(ts):
    """Compact text of the API for the extraction prompt."""
    out = [f"server: {ts['base']}", f"description: {ts['description']}"]
    for name, op in ts["ops"].items():
        out.append(f"\n{name}: {op['summary']}")
        for f, s in op["request"].items():
            out.append(f"  request {f}: {s.get('type')}{' enum=' + str(s['enum']) if s.get('enum') else ''}"
                       f"{' required' if f in op['required'] else ''}{' - ' + s['description'] if s.get('description') else ''}")
        for f, s in op["response"].items():
            out.append(f"  response {f}: {s.get('type')}{' enum=' + str(s['enum']) if s.get('enum') else ''}")
        for lf, props in op["items"].items():
            for f, s in props.items():
                out.append(f"  response {lf}[].{f}: {s.get('type')}{' enum=' + str(s['enum']) if s.get('enum') else ''}"
                           f"{' - ' + s['description'] if s.get('description') else ''}")
    return "\n".join(out)


def bind_roles(ts, mapping, roles):
    """The fixed components call operations by role name (verify_identity, get_account, ...). Point each role at the
    contract operation the policy names for it in `operations` (role -> operation name exactly as summary() lists it);
    a role left empty keeps an operation of the same name if there is one. Nothing is guessed: an unknown name, a
    clash with a same-named operation or one operation bound to two roles is a problem for the repair step.
    Returns (ts with the role keys added, {role: operation}, problems)."""
    mapping = mapping if isinstance(mapping, dict) else {}
    bound, probs = {}, []
    for role in roles:
        name = mapping.get(role)
        if name in (None, "", "null", "none"):
            if role in ts["ops"]:
                bound[role] = role
            continue
        if name not in ts["ops"]:
            probs.append(f"operations.{role}: {name!r} is not an operation of the tool API (operations: {', '.join(sorted(ts['ops']))})")
        elif role in ts["ops"] and name != role:
            probs.append(f"operations.{role}: {name!r} given, but the tool API also has an operation named {role!r}")
        else:
            bound[role] = name
    names = list(bound.values())
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        probs.append(f"operations: one tool API operation bound to several roles: {dup}")
    ops = dict(ts["ops"])
    for role, name in bound.items():
        ops[role] = ts["ops"][name]
    return {**ts, "ops": ops, "roles": bound}, bound, probs

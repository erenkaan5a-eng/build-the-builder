"""Read a tool API (OpenAPI) file deterministically: server URL, and for each operation its request and response fields."""
import json


def load(path):
    spec = json.load(open(path, encoding="utf-8"))
    base = (spec.get("servers") or [{}])[0].get("url", "").rstrip("/")
    ops = {}
    for p, item in spec.get("paths", {}).items():
        op = item.get("post") or item.get("get") or {}
        req = (((op.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema") or {}
        resp = ((((op.get("responses") or {}).get("200") or {}).get("content") or {}).get("application/json") or {}).get("schema") or {}
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

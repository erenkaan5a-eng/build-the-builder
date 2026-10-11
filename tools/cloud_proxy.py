"""Opt-in cloud proxy mode for the kit's Freya and bank clients.

In a cloud session whose egress proxy adds the credentials (the environment's Network secrets: `Authorization: Bearer`
for staging-app.freyavoice.ai, `x-team-key` for freya-bank-mock.freyavoice.workers.dev), FREYA_API_KEY and
FREYA_BANK_TEAM_KEY may be absent from the process. Set FREYA_AUTH_VIA_PROXY=1 to send those requests without the
header so the proxy can add it.

Without that variable nothing changes: freya.py and tools/score.py read the keys from the environment (or env.sh) as
before. A key that IS present is always sent as before, also in proxy mode. The kit files themselves stay unchanged;
this module patches the imported clients in the current process only. It never reads or prints a header value.
"""
import json, os, pathlib, sys, urllib.error, urllib.request

_TOOLS = pathlib.Path(__file__).resolve().parent
for _p in (_TOOLS, _TOOLS.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def enabled():
    return os.environ.get("FREYA_AUTH_VIA_PROXY", "").strip() == "1"


def apply():
    """Patch freya.HEADERS and score.http when proxy mode is on. Returns a short status line without secrets."""
    if not enabled():
        return "off"
    import freya, score
    done = []
    if not os.environ.get("FREYA_API_KEY"):
        freya.HEADERS.pop("Authorization", None)
        done.append("Freya Authorization left to the proxy")
    if not os.environ.get("FREYA_BANK_TEAM_KEY") and not getattr(score.http, "_via_proxy", False):
        def http(path, body=None):
            # same request as score.http, minus the x-team-key header that the proxy adds
            req = urllib.request.Request(score.HOST + path, data=json.dumps(body).encode() if body is not None else None,
                                         headers=dict(score.UA), method="POST" if body is not None else "GET")
            try:
                return json.load(urllib.request.urlopen(req, timeout=20))
            except urllib.error.HTTPError as e:
                return json.load(e)
        http._via_proxy = True
        score.http = http
        done.append("bank x-team-key left to the proxy")
    return "on: " + ("; ".join(done) or "keys present in the environment, nothing changed")

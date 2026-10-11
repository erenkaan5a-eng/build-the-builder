"""Full session logs of the builder's model runs (Claude Agent SDK), one JSONL file per session, next to the run's trace.

Each SDK call gets its own new session id (a builder started from inside another Claude Code session would otherwise
inherit that session's id and write into its transcript) and a session store that mirrors every transcript entry the
CLI writes: prompts, model answers, tool calls and tool results, subagent transcripts (own files). Entries are written
as they arrive to traces/<run>.sessions/<session_id>[__<subpath>].jsonl. Secret values are replaced by
[REDACTED:<NAME>] markers; nothing else is changed. The plain trace names each session file, and the end of the run
records each file's entry count and sha256."""
import hashlib, json, os, re, uuid

from claude_agent_sdk import InMemorySessionStore

SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.I)
PATTERNS = [(re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"), "[REDACTED:anthropic-key]"),
            (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/\-]{16,}=*"), r"\1[REDACTED:bearer]"),
            (re.compile(r"(?i)(x-team-key[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9._\-]{8,}"), r"\1[REDACTED:team-key]")]


def secret_values():
    """(name, value) of environment variables whose name says secret, long enough to match safely."""
    return sorted(((k, v) for k, v in os.environ.items() if SECRET_NAME.search(k) and v and len(v) >= 8),
                  key=lambda kv: -len(kv[1]))


def redact(text, secrets):
    n = 0
    for name, value in secrets:
        if value in text:
            n += text.count(value)
            text = text.replace(value, f"[REDACTED:{name}]")
    for pat, rep in PATTERNS:
        text, k = pat.subn(rep, text)
        n += k
    return text, n


class RunSessionStore(InMemorySessionStore):
    """Session store of one builder run: keeps the SDK's in-memory copy and appends every entry to a JSONL file."""

    def __init__(self, folder, trace):
        super().__init__()
        self.folder, self.trace = folder, trace
        self.files, self.redactions = {}, 0
        self.secrets = secret_values()

    async def append(self, key, entries):
        await super().append(key, entries)
        sub = key.get("subpath")
        name = key["session_id"] + ("__" + re.sub(r"[^A-Za-z0-9._-]+", "_", sub) if sub else "") + ".jsonl"
        path = self.folder / name
        if name not in self.files:
            self.folder.mkdir(parents=True, exist_ok=True)
            self.files[name] = 0
            self.trace.log("SESSION", f"session {key['session_id']}{' ' + sub if sub else ''} -> {path.relative_to(self.trace.path.parent.parent)}")
        with path.open("a", encoding="utf-8") as f:
            for e in entries:
                line, n = redact(json.dumps(e, ensure_ascii=False), self.secrets)
                self.redactions += n
                f.write(line + "\n")
                self.files[name] += 1

    def summary(self):
        """Log every session file with its entry count and sha256 (call at the end of the run)."""
        for name, count in sorted(self.files.items()):
            p = self.folder / name
            h = hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "missing"
            self.trace.log("SESSION", f"{p.relative_to(self.trace.path.parent.parent)}: {count} entries, sha256 {h}")
        self.trace.log("SESSION", f"{len(self.files)} session file(s); {self.redactions} secret value(s) redacted")


def options(trace):
    """Keyword arguments for ClaudeAgentOptions: a fresh session id and this run's session store."""
    if getattr(trace, "session_store", None) is None:
        trace.session_store = RunSessionStore(trace.path.with_suffix(".sessions"), trace)
    sid = str(uuid.uuid4())
    return {"session_id": sid, "session_store": trace.session_store, "env": {"CLAUDE_CODE_SESSION_ID": sid}}

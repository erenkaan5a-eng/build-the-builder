"""Build a Freya phone agent from one brief and its tool API file.

    python3 builder/build.py <brief_path> <tool_api_path> [--slot NAME] [--out PATH] [--mode auto|main|fallback]
                             [--budget-min 30] [--practice CASE_ID]

Main path: one Claude call extracts policy.json from the brief and tool API; fixed, parameterized components
(builder/components.py) generate the workflow. Fallback path: a time-bounded agent writes the workflow with the skill.
One wall-clock budget covers everything, including the final sequence validate -> publish -> test that version -> export.
Every run writes a candidate folder candidates/<slot>/<time>/; --out is written only when the release checks pass.
"""
import argparse, asyncio, hashlib, json, os, pathlib, re, shutil, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402  (loads env.sh, imports freya)
import lint as linter  # noqa: E402
import toolspec, spec_extract, components, behavior, case_input, session_log  # noqa: E402
from common import KIT, Budget, Trace  # noqa: E402

RESERVE_S = 5 * 60            # kept for validate, publish, behaviour test, export
FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "claude-sonnet-5-5")
EXTRACT_MODEL = os.environ.get("EXTRACT_MODEL", "claude-opus-5-5")
AGENT_GAPS = []               # "GAP:" lines the fallback agent reported


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


# ------------------------------------------------------------------ main path
def run_main(brief, tool_api, cand, budget, trace, reuse_policy=None):
    ts = toolspec.load(tool_api)
    text = pathlib.Path(brief).read_text(encoding="utf-8")
    inputs = {"brief": str(brief), "brief_sha256": sha(brief), "tool_api": str(tool_api), "tool_api_sha256": sha(tool_api)}
    (cand / "inputs.json").write_text(json.dumps(inputs, indent=1), encoding="utf-8")
    left = budget.left() - RESERVE_S
    if left < 180:
        raise RuntimeError("not enough budget for the main path")
    if reuse_policy:
        # development only: the policy of an earlier traced run of the same inputs, no model call (e.g. that run failed
        # on a platform error after its extraction). The final runs extract.
        src = pathlib.Path(reuse_policy)
        rec = src.parent / "inputs.json"
        if rec.exists():
            old = json.loads(rec.read_text(encoding="utf-8"))
            if (old.get("brief_sha256"), old.get("tool_api_sha256")) != (inputs["brief_sha256"], inputs["tool_api_sha256"]):
                raise RuntimeError(f"reused policy {src} was extracted from other inputs")
            trace.log("MAIN", f"policy reused from {src} (sha256 {sha(src)[:16]}); inputs match the recorded hashes; no model call")
        else:
            trace.log("MAIN", f"policy reused from {src} (sha256 {sha(src)[:16]}); that run recorded no input hashes (brief sha256 now "
                              f"{inputs['brief_sha256'][:16]}, API {inputs['tool_api_sha256'][:16]}); no model call")
        pol = json.loads(src.read_text(encoding="utf-8"))
    else:
        pol = spec_extract.extract(text, toolspec.summary(ts), EXTRACT_MODEL, trace, timeout_s=min(left, 900))
    (cand / "policy.raw.json").write_text(json.dumps(pol, indent=1), encoding="utf-8")

    def check(pol):
        # the policy binds the fixed components' roles to the contract's operations; validation runs on those roles
        ts_roles, bound, probs = toolspec.bind_roles(ts, pol.get("operations"), components.ROLES)
        return ts_roles, bound, probs + spec_extract.validate(pol, ts_roles)
    ts_roles, bound, probs = check(pol)
    if probs and not reuse_policy and budget.left() - RESERVE_S > 180:
        trace.log("MAIN", f"policy validation: {len(probs)} problem(s); one bounded repair call")
        for p in probs:
            trace.log("MAIN", "  " + p)
        fix = ("Your policy JSON has these problems against the tool API:\n- " + "\n- ".join(probs)
               + "\nReturn the full corrected JSON object only.\n\nYOUR JSON:\n" + json.dumps(pol))
        pol = spec_extract.parse_json(asyncio.run(asyncio.wait_for(spec_extract._ask(
            "TOOL API:\n" + toolspec.summary(ts) + "\n\nBRIEF:\n<<<\n" + text + "\n>>>\n\n" + fix,
            "Answer with JSON only.\n\nPROJECT INSTRUCTIONS (binding):\n" + spec_extract.project_instructions(),
            EXTRACT_MODEL, trace, "repair policy.json against the tool API validation problems"), timeout=min(budget.left() - RESERVE_S, 600))))
        ts_roles, bound, probs = check(pol)
    for role, name in bound.items():
        trace.log("MAIN", f"operation for {role}: {name} ({ts['ops'][name]['url']})")
    pol["operation_urls"] = {role: ts["ops"][name]["url"] for role, name in bound.items()}  # read by behavior.py
    (cand / "policy.json").write_text(json.dumps(pol, indent=1), encoding="utf-8")
    if probs:
        raise RuntimeError("policy invalid after repair: " + "; ".join(probs)[:800])
    ts = ts_roles
    structural = [r for r in pol.get("extra_rules") or [] if r.get("kind") == "structural"]
    if structural and budget.left() - RESERVE_S > 120:
        # a rule the fixed components already carry can be misclassified (11 Oct, A+B: the 'no notes after a transfer' rule);
        # one bounded re-check with only the rules and the generic capability list, before giving up the main path
        trace.log("MAIN", f"{len(structural)} rule(s) classified structural; one bounded re-check call")
        try:
            verdicts = spec_extract.recheck_structural(structural, EXTRACT_MODEL, trace, timeout_s=min(budget.left() - RESERVE_S, 300))
            for r, vd in zip(structural, verdicts):
                trace.log("MAIN", f"  re-check: {vd.get('kind')} - {str(r.get('text'))[:100]} ({str(vd.get('why'))[:120]})")
                if vd.get("kind") in ("computational", "stateful", "conversational"):
                    r["kind"], r["recheck"] = vd["kind"], vd.get("why")
            (cand / "policy.json").write_text(json.dumps(pol, indent=1), encoding="utf-8")
        except Exception as e:
            trace.log("MAIN", f"structural re-check failed: {e}"[:300])
        structural = [r for r in pol.get("extra_rules") or [] if r.get("kind") == "structural"]
    if structural:
        raise RuntimeError("structural rules the generator cannot express: " + "; ".join(r.get("text", "")[:120] for r in structural))
    for a in pol.get("amendments") or []:
        trace.log("POLICY", f"amendment: {a.get('change')} | scope {a.get('scope')} | replaces {a.get('replaces')}")
    need = sorted(set(components.REQUIRED_OPS) - set(ts["ops"]))
    if need:
        # the fixed components are written for these operations; a contract without them goes to the fallback path visibly
        raise RuntimeError("the service contract lacks operations the fixed components use: " + ", ".join(need)
                           + " (contract has: " + ", ".join(sorted(ts["ops"])) + ")")
    wf = components.build(pol, ts)
    path = cand / "workflow.json"
    path.write_text(json.dumps(wf, indent=1), encoding="utf-8")
    (cand / "support_boundary.json").write_text(json.dumps(components.support_boundary(pol), indent=1), encoding="utf-8")
    return path, pol, components.known_gaps(pol)


# ------------------------------------------------------------------ fallback path
async def _fallback_agent(brief, tool_api, out, seconds, trace, workdir, repair=None, case_folder=None):
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, ToolUseBlock, query
    minutes = max(1, int(seconds // 60))
    prompt = (f"Use the build-phone-agent-final skill. Brief: {brief}. Tool API file: {tool_api}. "
              f"Your work dir for this run is {workdir}: write every file there and nowhere else; do not read or reuse files from other folders under out/ or candidates/. "
              f"Write the workflow to {out}. Check it with: python builder/lint.py {out} {tool_api} --dry-run . "
              f"You have {minutes} minutes in total; stop before that with the best lint-clean version on disk.")
    if case_folder:
        # the brief file is the text extraction of the case folder; drawings, page layout and tables are only in the originals
        prompt += (f" The brief file is the text extraction of the case folder {case_folder}; open its original files too "
                   f"(read only, do not change them): PDF pages, drawings and tables keep structure the text lost.")
    if repair:
        prompt += " REPAIR TASK: the workflow at " + out + " already exists. " + repair + " Change only what this needs, re-run the linter, keep everything else."
    so = session_log.options(trace)   # own session id + full session log of this agent run (incl. tool calls and results)
    options = ClaudeAgentOptions(
        cwd=str(KIT), model=FALLBACK_MODEL, skills=["build-phone-agent-final"], setting_sources=["project"],
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"], disallowed_tools=["Read(./env.sh)", "Read(**/env.sh)"],
        permission_mode="dontAsk", max_turns=80, session_id=so["session_id"], session_store=so["session_store"],
        add_dirs=[str(case_folder)] if case_folder else [],
        env={"BASH_DEFAULT_TIMEOUT_MS": "120000", "BASH_MAX_TIMEOUT_MS": "300000", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1", **so["env"]})
    async for m in query(prompt=prompt, options=options):
        if isinstance(m, AssistantMessage):
            tools = [f"{b.name}({str(b.input)[:60]})" for b in m.content if isinstance(b, ToolUseBlock)]
            full = " ".join(b.text for b in m.content if isinstance(b, TextBlock))
            for line in full.splitlines():
                if line.strip().startswith("GAP:"):
                    AGENT_GAPS.append(line.strip()[4:].strip())
            trace.model_call(m.model, "fallback builder step: " + ("; ".join(tools) or full[:100].replace("\n", " ") or "thinking"))
        elif isinstance(m, ResultMessage):
            u = m.usage or {}
            trace.log("AGENT", f"fallback agent done: session={m.session_id} turns={m.num_turns} duration_s={m.duration_ms/1000:.0f} is_error={m.is_error} "
                               f"tokens_in={u.get('input_tokens')} cache_create={u.get('cache_creation_input_tokens')} "
                               f"cache_read={u.get('cache_read_input_tokens')} tokens_out={u.get('output_tokens')}")


def run_fallback(brief, tool_api, out, budget, trace, workdir, repair=None, case_folder=None):
    seconds = budget.left() - RESERVE_S
    if seconds < 120:
        trace.log("FALLBACK", "not enough budget left to run the fallback agent")
        return None
    trace.log("FALLBACK", f"starting fallback agent, model {FALLBACK_MODEL}, {seconds/60:.1f} min")
    try:
        asyncio.run(asyncio.wait_for(_fallback_agent(brief, tool_api, out, seconds, trace, workdir, repair, case_folder), timeout=seconds))
    except (asyncio.TimeoutError, TimeoutError):
        trace.log("FALLBACK", "fallback agent stopped at its time limit")
    except Exception as e:
        trace.log("FALLBACK", f"fallback agent error: {e!r}"[:500])
    return out if pathlib.Path(out).exists() else None


# ------------------------------------------------------------------ release
def _retry_5xx(fn, budget, trace, waits=(30, 90, 180)):
    """Run fn; on a platform 5xx (chat API) wait and try again while the shared budget keeps 2 minutes for export."""
    last = None
    for i, w in enumerate((0,) + tuple(waits)):
        if w:
            if budget.left() - w < 120:
                break
            trace.log("TEST", f"platform 5xx ({str(last)[:90]}); waiting {w}s, retry {i} of {len(waits)}")
            time.sleep(w)
        try:
            return fn()
        except RuntimeError as e:
            if not re.search(r"-> 5\d\d", str(e)):
                raise
            last = e
    raise last


def final_sequence(slot, wf_path, tool_api, cand, budget, trace, pol=None, practice=None):
    """validate -> publish -> test that published version -> export. Every step checks the shared budget."""
    st = {"release_checks_passed": False, "policy_correctness": "not measured by the build"}
    wf = json.load(open(wf_path, encoding="utf-8"))
    allp = linter.lint(wf, tool_api)
    for w in [p for p in allp if p.startswith("warn:")]:
        trace.log("VALIDATE", "WARNING " + w[5:].strip())
    probs = [p for p in allp if not p.startswith("warn:")]
    if not probs:
        try:
            # a dry run writes nothing, so a platform 5xx is retried within the shared budget (11 Oct: one 504)
            _retry_5xx(lambda: common.freya.validate_workflow(f"{slot} dry run", wf), budget, trace)
        except Exception as e:
            probs.append("Freya dry-run: " + str(e)[:800])
    for p in probs:
        trace.log("VALIDATE", "PROBLEM " + p)
    st["lint_problems"] = len(probs)
    if probs:
        trace.log("VALIDATE", "not published: the candidate failed validation")
        return st
    if budget.left() < 60:
        trace.log("RELEASE", "budget exhausted before publish")
        return st
    try:
        # updating an existing slot only adds a version, so a platform 5xx is retried within the budget; creating a new
        # slot is not retried (a lost answer could leave a second workflow)
        exists = slot in json.loads((KIT / ".freya-agents.json").read_text()) if (KIT / ".freya-agents.json").exists() else False
        pub = _retry_5xx(lambda: common.publish(slot, wf, trace), budget, trace) if exists else common.publish(slot, wf, trace)
        st.update(pub)
        tested = _retry_5xx(lambda: common.get_workflow(pub["workflow_id"]), budget, trace)
    except Exception as e:
        trace.log("RELEASE", f"publish failed: {e}"[:400])
        return st
    st["tested_hash"] = common.wf_hash(tested)
    trace.log("TEST", f"testing published version {pub['version_number']} hash {st['tested_hash']}")
    checks = []
    if budget.left() > 45:
        try:
            if pol:
                checks = _retry_5xx(lambda: behavior.structural(pub["workflow_id"], pol, trace), budget, trace)
            else:
                tv = dict(wf.get("test_variables") or {})
                tv["customer_id"] = "c_smoke_test"
                r = _retry_5xx(lambda: common.chat_smoke(pub["workflow_id"], tv, trace), budget, trace)
                checks = [("opening line spoken (fallback: structural checks need a policy)", bool((r.get("response") or "").strip()), "")]
            if practice and budget.left() > 60:
                pres, _ = _retry_5xx(lambda: behavior.practice(pub["workflow_id"], practice, trace), budget, trace)
                checks += pres
        except Exception as e:
            trace.log("TEST", f"behaviour test error: {e}"[:400])
            checks.append(("behaviour test ran", False, str(e)[:200]))
    else:
        trace.log("TEST", "budget too low for behaviour tests")
    st["checks"] = [[n, ok] for n, ok, _ in checks]
    if budget.left() < 15:
        trace.log("RELEASE", "budget exhausted before export")
        return st
    exp = cand / "export.json"
    common.freya.export_workflow(pub["workflow_id"], str(exp))
    st["exported_hash"] = common.wf_hash(json.load(open(exp, encoding="utf-8"))["workflow"])
    trace.log("EXPORT", f"{exp} hash {st['exported_hash']} (tested {st['tested_hash']}, published version {pub['version_number']})")
    st["release_checks_passed"] = bool(checks) and all(ok for _, ok, _ in checks) and st["exported_hash"] == st["tested_hash"]
    st.update(common.counts(tested))
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief"); ap.add_argument("tool_api")
    ap.add_argument("--slot"); ap.add_argument("--out"); ap.add_argument("--mode", default="auto", choices=["auto", "main", "fallback"])
    ap.add_argument("--budget-min", type=float, default=30); ap.add_argument("--practice")
    ap.add_argument("--reuse-policy", help="development only: policy.json of an earlier traced run of the same brief and API (no model call)")
    ap.add_argument("--local-only", action="store_true", help="extract and generate, run the local lint, write the candidate; no Freya call at all")
    ap.add_argument("--contract", help="with a case folder and a mock URL: the service contract file (OpenAPI JSON/YAML) to bind to the mock URL, "
                                       "when the folder has none or several")
    a = ap.parse_args()
    slot = a.slot or pathlib.Path(a.brief).stem
    budget, trace = Budget(a.budget_min), Trace(slot)
    cand = KIT / "candidates" / slot / time.strftime("%Y%m%d-%H%M%S")
    k = 1
    while cand.exists():                   # never reuse an earlier run's candidate folder
        k += 1
        cand = KIT / "candidates" / slot / (time.strftime("%Y%m%d-%H%M%S") + f"-{k}")
    cand.mkdir(parents=True)
    trace.log("START", f"slot={slot} brief={a.brief} tool_api={a.tool_api} mode={a.mode} budget_min={a.budget_min} candidate={cand}")
    try:
        import subprocess
        g = lambda *x: subprocess.check_output(["git"] + list(x), cwd=KIT, stderr=subprocess.DEVNULL).decode().strip()
        trace.log("START", f"source commit {g('rev-parse', 'HEAD')} builder tree {g('rev-parse', 'HEAD:builder')} "
                           f"uncommitted builder changes: {'yes' if g('status', '--porcelain', '--', 'builder') else 'no'}")
    except Exception:
        trace.log("START", "source commit: not a git checkout")
    trace.log("START", f"credentials: FREYA_API_KEY {'set' if os.environ.get('FREYA_API_KEY') else 'absent'}, "
                       f"FREYA_BANK_TEAM_KEY {'set' if os.environ.get('FREYA_BANK_TEAM_KEY') else 'absent'}, cloud proxy mode {common.PROXY_MODE}")
    # inputs: a brief file + a tool API file (kit form), or a case folder + a mock URL (the service contract is found in
    # the folder and bound to the mock URL); every file read is listed in the trace with its hash
    brief_in, api_in, input_problems, inputs_meta = a.brief, a.tool_api, [], {"brief_arg": a.brief, "tool_api_arg": a.tool_api}
    try:
        if pathlib.Path(a.brief).is_dir():
            case = case_input.load_case(a.brief)
            (cand / "case_inventory.json").write_text(json.dumps({"folder": a.brief, "files": case["inventory"], "errors": case["errors"]},
                                                                 indent=1, ensure_ascii=False), encoding="utf-8")
            for it in case["inventory"]:
                trace.log("INPUT", f"{it['file']} ({it['type']}, {it['bytes']} bytes, sha256 {it['sha256_16']}): "
                                   + (f"NOT READ: {it['error']}" if it.get("error") else f"{it.get('chars')} chars read"))
            for e in case["errors"]:
                trace.log("INPUT", "PROBLEM " + e)
            input_problems += case["errors"]
            brief_in = str(cand / "case_brief.md")
            pathlib.Path(brief_in).write_text(case["text"], encoding="utf-8")
            inputs_meta["case_files"] = len(case["inventory"])
        if re.match(r"^https?://", a.tool_api):
            if not pathlib.Path(a.brief).is_dir():
                raise RuntimeError("a mock URL needs a case folder as the first argument (the service contract is read from it)")
            contract = pathlib.Path(a.contract) if a.contract else case_input.find_contract(a.brief)
            api_in = str(cand / "tool_api.json")
            note = case_input.bind_contract(contract, a.tool_api, api_in)
            trace.log("INPUT", f"service contract {contract} (sha256 {case_input.sha16(contract)}); {note}")
            # the binding replaces the contract's own server on purpose; say so in the case text so the extraction does not
            # report the two addresses as a conflict (rehearsal 11 Oct: 'unresolved conflict: Server URL')
            bound = json.loads(pathlib.Path(api_in).read_text(encoding="utf-8"))["servers"][0]["url"]
            run_note = (f"RUN NOTE (written by the builder, not a case document): the service contract {contract.name} is bound to this "
                        f"run's bank mock at {bound}; its own 'servers' address is replaced on purpose. The TOOL API section is that "
                        f"bound contract. This replacement is not a conflict.\n\n")
            pathlib.Path(brief_in).write_text(run_note + pathlib.Path(brief_in).read_text(encoding="utf-8"), encoding="utf-8")
            inputs_meta.update({"mock_url": a.tool_api, "contract": str(contract), "contract_sha256_16": case_input.sha16(contract)})
    except Exception as e:
        trace.log("INPUT", f"PROBLEM {e}"[:600])
        trace.log("END", f"inputs could not be read: nothing built. elapsed {budget.elapsed():.0f}s")
        sys.exit(2)
    wf_path, path_used, pol, gaps = None, None, None, []
    if a.mode in ("auto", "main"):
        try:
            wf_path, pol, gaps = run_main(brief_in, api_in, cand, budget, trace, reuse_policy=a.reuse_policy)
            path_used = "main"
        except Exception as e:
            trace.log("MAIN", f"main path failed: {e}"[:900])
            if a.mode == "main":
                trace.log("END", f"main only: no workflow. elapsed {budget.elapsed():.0f}s")
                sys.exit(2)
    if not wf_path:
        work = cand / "workflow.json"
        wf_path, path_used = run_fallback(brief_in, api_in, str(work), budget, trace, str(cand),
                                          case_folder=a.brief if pathlib.Path(a.brief).is_dir() else None), "fallback"
        gaps = AGENT_GAPS + ["coverage not fully assessed: the fallback path reports only the gaps its agent noticed"]
    if not wf_path:
        trace.log("END", f"no workflow produced. elapsed {budget.elapsed():.0f}s")
        sys.exit(2)
    if a.local_only:
        probs = [p for p in linter.lint(json.load(open(wf_path, encoding="utf-8")), api_in) if not p.startswith("warn:")]
        for p in probs:
            trace.log("VALIDATE", "PROBLEM " + p)
        manifest = {"path": path_used, "slot": slot, "local_only": True, "lint_problems": len(probs), "build_seconds": round(budget.elapsed()),
                    "model_calls": trace.model_calls, "trace": str(trace.path), "known_gaps": gaps}
        (cand / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        trace.log("END", f"local only: lint {'OK' if not probs else str(len(probs)) + ' problem(s)'}; nothing published, nothing tested on Freya")
        return
    st = final_sequence(slot, wf_path, api_in, cand, budget, trace, pol=pol, practice=a.practice)
    if input_problems:
        st["release_checks_passed"] = False      # a document that could not be read may hold a rule: never a silent pass
        trace.log("RELEASE", f"{len(input_problems)} input problem(s): release checks fail")
    for g in gaps:
        trace.log("GAPS", "Known rule gap: " + g)
    manifest = {"path": path_used, "slot": slot, "build_seconds": round(budget.elapsed()), "model_calls": trace.model_calls,
                "trace": str(trace.path), "known_gaps": gaps, "inputs": inputs_meta, "input_problems": input_problems, **st}
    if pol:
        manifest["support_boundary"] = components.support_boundary(pol)
    (cand / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    if a.out and st["release_checks_passed"]:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cand / "export.json", a.out)
        trace.log("OUT", f"release checks passed: candidate copied to {a.out}")
    elif a.out:
        trace.log("OUT", f"release checks did NOT pass: {a.out} left unchanged; candidate kept in {cand}")
    trace.log("SUMMARY", f"workflow {st.get('workflow_id')} agent {st.get('agent_id')} published version {st.get('version_number')} "
                         f"nodes {st.get('nodes')} global nodes {st.get('global_nodes')} tool functions {st.get('tool_functions')} "
                         f"checks {sum(1 for _, ok in st.get('checks') or [] if ok)}/{len(st.get('checks') or [])} passed, "
                         f"export {cand / 'export.json'} hash {st.get('exported_hash')}, manifest {cand / 'manifest.json'}")
    trace.log("RESULT", json.dumps(manifest)[:3000])
    trace.log("END", f"build time {budget.elapsed():.0f}s, path {path_used}, model calls {trace.model_calls}, release checks "
                     f"{'PASSED' if st['release_checks_passed'] else 'FAILED'} (validation, behaviour checks on the published version, tested==exported hash; not policy correctness)")


if __name__ == "__main__":
    main()

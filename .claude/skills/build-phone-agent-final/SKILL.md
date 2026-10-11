---
name: build-phone-agent-final
description: Write a Freya phone-agent workflow JSON from ONE bank brief and ITS tool API file, under a time limit, checking it with the static linter. Used by builder/build.py in fallback mode.
---

# Write a phone agent from a brief (final conditions)

You get a brief file, a tool API file (OpenAPI), an output path and a deadline; when the case came as a folder of documents, also that folder. Your only job is to write a correct workflow JSON to the output path and make `python builder/lint.py <out> <tool_api> --dry-run` print OK. The builder publishes, tests and exports it after you stop. Do not save, publish, simulate or export yourself. There are no practice customers for this brief: do not run tools/run_cases.py.

## Steps

1. Read the whole brief. Most failures come from one skipped rule. List every rule with its source to yourself: the call's stages and branches, checks the brief asks for, dates, amounts, special intents, confirmations, transfers, closing, exact sentences. The examples in this skill come from a debt-collection practice brief; use one only where your brief has such a rule, never because the practice had it.
   If you were given a case folder, open its original files too (PDF pages, drawings, tables, spreadsheets): arrows, branches and table layout are lost in the text extraction you get as the brief. Documents written at different times: an amendment applies within its stated scope; the newest document does not override everything; list a conflict you cannot settle as a `GAP:` line with the choice you made.
2. Read the tool API file: server URL, endpoint names, every body field, enum and response field. Use only these. Field names and enum values can differ from any example.
3. Read `docs/workflow-format.md` and `docs/tools-and-code.md` once. Use `examples/base-agent.json` only as a JSON shape example; its rules are not your brief's rules.
4. Write the workflow. Then run the linter, fix every problem, repeat until OK. Finish with one line: `WROTE <path>`.

## Design that works on the fixed phone-agent model

- One conversation node per stage of the brief's call flow, with strict rules (in the practice brief: opening/who is on the line, identity, stating the debt and negotiating, read-back/confirm, closing). Checks the brief requires before an action come before it. A node lists only the tools allowed in that stage (in the practice: no account or promise tool before identity was verified). This narrows what the model can call; it does not by itself prove the call happens at the right time or exactly once, so entry conditions and fresh parameters still matter.
- Leave a node on a tool result (a transition on a mapped variable), not on what the customer says.
- The docs report that booleans from results arrive as strings: test both "true" and "True". The docs' working builder used mapping paths starting with `data.`. Bind to the field names of THIS tool API file.
- When the brief has date rules, do date arithmetic in a passthrough `code` node from the `now` call variable, never from the real clock: today, weekday, business days, holidays, and whatever dates the brief's rules need (in the practice: deadlines per product and band, "this <weekday>" / "next <weekday>" dates, the next business day). Write the results as one text block variable and put it in the prompts with `{{var}}`. Code reads `vars.get(...)`, never raises (try/except with fallback values), contains no `{{` or `}}`, writes strings for routing flags.
- If the brief has payment-promise date rules (a promised day within a deadline of business days), the dates are decided by code, not by the model: write `<work dir>/date_config.json` from the brief (see the docstring of `builder/runtime/date_tool.py`: now variable, weekend days, holidays, bands with their deadline in business days, how often to ask for an exact day, and the sentences to say, in the brief's own wording). Run `python builder/runtime/date_tool.py <work dir>/date_config.json <negotiation_node>` and merge its output exactly as its `instructions` say (tool in the negotiation node, its transition first, its two nodes added; products_vars must name the variable your account step stores the product list in). The model only turns the customer's words into YYYY-MM-DD with the calendar lines your code node writes (this/next weekday per the brief) or passes 'vague', and never says itself whether a day is allowed. If the brief's date rules cannot be expressed with that config, do not force them: write your own code for them and end your work with a line `GAP: <rule> - <why>`.
- On every api_call tool add a `post_process_code` hook that pops `header` and adds `result['data']['what_to_do_next']`: one plain sentence saying what the result means and what to say or call next (for example: wrong answer and how many are left, ask the same question again; promise not recorded, try once more; promise recorded, say the confirmation sentence). Tell the model in the prompt to follow `what_to_do_next`.
- After every tool result the model must speak or call the next tool. One tool call per message.
- Customers mix answers with questions ("Are you a robot? My salary comes on the 6th"). Every node's prompt, including its entry line after a transition, must first answer a question in the customer's last message as the brief requires (for example an AI/robot or scam question), in one short sentence, and only then continue.
- Exact sentences from the brief go into prompts in quotes, with "say exactly".
- Model-filled body fields use `"default": "{{<field>}}"` with a description and enum; fixed fields use literal defaults. Never `const`. A field that identifies the customer takes the call variable the brief defines for it (`"{{<that variable>}}"`); the model never asks for or invents it.
- Ids (products, cards, accounts and the like) come from tool results; never invent them. Observed on Freya: a list in a response (such as the product list) is NOT stored in a mapped variable; only flattened keys like `<node>_response.data.<list>.0.<field>` (api_request node) or `<tool>_response.data.<list>.0.<field>` (tool) exist. Read lists from those keys in a code node, and route on a value your code writes, never on a mapped list being set.
- If the brief or the tool API has a closing/outcome tool, every call ends with it exactly once, as the last tool call, with the outcome the brief requires; otherwise end the call the way the brief says (hand-off, transfer or end). Say goodbye before ending where the brief does.
- Retries of a write are not left to the model's memory. If the brief allows N more tries after a failed write, set that tool's `config.maxRetries` to N so the platform retries it; otherwise `maxRetries: 0`. Tell the model: when the tool still reports failure, the allowed tries are used up, do not call it again, follow the brief's failure path. (A failed call can arrive as an error with no result body, so hooks do not run on it.)
- Set `min_confidence` (0.6-0.7) on every extraction field, and `max_turn_transition` wherever you set `max_node_turns`.
- Set top-level `test_variables` to the example values the brief gives for its call variables (the builder's smoke test sends them).
- Leave out `agent_config`. Prefer omitting optional fields over `null` (docs call the schema strict; a dry-run accepted some nulls).

## Rules

- Follow the project instructions (CLAUDE.md and .claude/rules/freya-verification.md). Never read or print env.sh or credentials.

- Take every value (names, numbers, holidays, enum values, sentences, outcomes) from this brief and this tool API file only.
- Never tell the customer something is recorded unless the tool returned success. Sentences about an action's status say plainly which state it is in: done, not done (nothing was saved), or being tried again. A failed call can arrive as an error with no result, so state this in the prompt, not only in a hook.
- If a call variable the brief defines (for example the current date) is missing, do not substitute a default value; take a visible error path.
- Report any brief rule you could not implement as a line `GAP: <rule> - <why>` at the end of your work.
- Stop before the deadline you were given, with the best lint-clean version on disk.

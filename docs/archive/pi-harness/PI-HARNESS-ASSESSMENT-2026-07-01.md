# Pi harness assessment - 2026-07-01

## Verdict

Pi (`earendil-works/pi`, `@earendil-works/pi-coding-agent`) can be developed and run through the terminal on this Windows repo. It is a good fit as a hackable local agent harness, but it should not replace the existing repo-specific DeepSeek tooling yet.

Best architecture:

1. Keep `tools/codex_orchestrator/deepseek_repo_agent.py` as the authoritative cached FS-aware LOCATE tier for bounty work.
2. Use Pi as an optional terminal/UI harness for ad hoc local sessions with DeepSeek v4 flash/pro and GLM 5.2.
3. If Claude Code and Codex need the same capabilities directly, expose the repo tools through a small local stdio MCP server instead of trying to make Claude/Codex drive Pi's TUI.
4. Optionally add a Pi TypeScript extension later that wraps the same Python tools as Pi-native tools.

## Local install test

Installed into an isolated temp prefix, not globally:

```powershell
$prefix = Join-Path $env:TEMP 'pi-agent-test'
npm install --prefix $prefix --ignore-scripts @earendil-works/pi-coding-agent@0.80.3
```

Observed:

- Node: `v23.3.0`
- npm: `10.9.1`
- Pi: `0.80.3`
- Pi package installed successfully in `%TEMP%\pi-agent-test`
- `pi` was not previously installed globally.

Pi CLI capabilities observed from `--help`:

- modes: interactive, print, JSON, RPC
- built-in tools: `read`, `bash`, `edit`, `write`
- optional read-only tools: `grep`, `find`, `ls`
- model selection: `--provider`, `--model`, `--thinking`
- context control: `--no-context-files`, `--no-tools`, `--tools`
- extension loading: `--extension`
- custom resource loading: skills, prompt templates, themes

## Model compatibility

Pi does not read this repo's `.env` automatically. The repo's Python wrappers do. For Pi, keys must be exported into the process, stored in Pi auth, passed with `--api-key`, or referenced from `~/.pi/agent/models.json`.

DeepSeek:

```powershell
pi --offline --list-models deepseek
```

after mapping `.env` key to `DEEPSEEK_API_KEY` showed:

- `deepseek-v4-flash`
- `deepseek-v4-pro`

Both have 1M context and 384K max output in Pi's model registry.

ZAI/GLM:

Pi expects `ZAI_API_KEY`. This repo commonly uses `ZHIPUAI_API_KEY`, `GLM_API_KEY`, or related aliases. Mapping the repo key to `ZAI_API_KEY` showed:

- `glm-4.5-air`
- `glm-4.7`
- `glm-5-turbo`
- `glm-5.1`
- `glm-5.2`
- `glm-5v-turbo`

Current runtime status:

- DeepSeek v4 flash/pro ping: OK
- DeepSeek balance: about USD 3.46
- GLM/ZAI ping: blocked by HTTP 429, insufficient balance/resource package

## Pi API smoke tests

DeepSeek direct model ping through Pi:

```powershell
pi --provider deepseek --model deepseek-v4-flash --no-session --no-context-files --no-tools -p "Reply exactly PI_OK."
```

Result:

```text
PI_OK
```

DeepSeek tool-use through Pi:

```powershell
pi --provider deepseek --model deepseek-v4-flash --no-session --no-context-files --tools grep,find,ls,read -p "Use the available file-search tools to find the file that contains the heading DEEPSEEK-REPO-AGENT under tools/codex_orchestrator. Answer with only the relative path."
```

Result:

```text
tools/codex_orchestrator/DEEPSEEK-REPO-AGENT.md
```

This confirms Pi can run a cheap DeepSeek agent with local file-search tools in this repo.

## Fit for this repo

Pi's generic grep/find/read tools work. The existing repo harness is still stronger for bounty work because it already has:

- cached DeepSeek tool-use loop: `research/sweep/deepseek_agent_cache.sqlite`
- repo-confined tools: `repo_grep`, `read_file`, `glob`, `list_dir`, `recover_class`
- provider preflight and balance checks
- concurrency caps and batch mode
- existing VRP honesty rules and LOCATE/GATE split

Pi is best used as:

- a terminal agent shell for interactive DeepSeek/GLM sessions
- a TypeScript extension host for custom repo tools
- an RPC target for custom wrappers
- a model-switching sandbox for cheap external agents

It is not sufficient by itself as the authoritative VRP controller unless we rebuild the repo-specific caches, gates, ledgers, prior-disposition checks, and promotion rules as Pi extensions/tools.

## Claude Code / Codex integration

Direct shell invocation works today:

```powershell
pi --provider deepseek --model deepseek-v4-flash --tools grep,find,ls,read -p "..."
```

Claude Code and Codex can also invoke the existing Python tools directly with shell commands.

For first-class tool invocation inside both Claude Code and Codex, build a small stdio MCP server exposing:

- `repo_grep_cached`
- `deepseek_locate`
- `external_agent`
- `reconcile_lead`
- `recover_class`
- `promote_gate_check`
- `frontier_status`
- `cache_stats`

This is better than wrapping Pi as the shared substrate because both Claude Code and Codex support MCP stdio servers directly, while Pi currently has no built-in MCP server role. Pi can still consume the same underlying Python tools via a Pi extension.

## Minimal next build

1. Create `tools/mcp_vrp_agent/` with a Python stdio MCP server.
2. Wrap only read-only and cache-backed tools first: grep/read/glob/deepseek locate/cache stats.
3. Add project-scoped Codex config under `.codex/config.toml` only if the operator wants repo-local config committed.
4. Add Claude Code `.mcp.json` only if the operator wants shared project MCP config.
5. Keep Pi temp/global install separate and add a `PI-RUNBOOK.md` or PowerShell wrapper if Pi becomes part of the workflow.

## Sources checked

- Pi repo: https://github.com/earendil-works/pi
- Pi docs: https://pi.dev/docs/latest
- Pi custom models docs: https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/models.md
- Pi custom providers docs: https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/custom-provider.md
- Pi RPC docs: https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/rpc.md
- Pi extensions docs: `%TEMP%\pi-agent-test\node_modules\@earendil-works\pi-coding-agent\docs\extensions.md`
- Codex MCP docs: https://developers.openai.com/codex/mcp
- Claude Code MCP docs: https://code.claude.com/docs/en/mcp

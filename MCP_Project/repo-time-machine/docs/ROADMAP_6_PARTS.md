# RepoTime Machine: seven-part build and learning roadmap

Use this alongside [project.md](project.md). Complete each part in order. Build the project yourself; the lists below tell you what to study, what to implement, and how to check your work.

## Before you start: scope and decisions

- **Target:** one local Git repository containing Python files, one read-only MCP server, one custom MCP client, and a CLI that can optionally use DeepSeek.
- **Evidence rule:** a commit, diff, file snapshot, and source location are facts you can verify. A claim about *why* a developer made a change is an inference unless a commit message or other evidence supports it. Label the two clearly in outputs.
- **Function identity:** start with `path + qualified function name` (for example, `src/auth.py::AuthService.login`). Renames and moves are hard to track reliably; document them as limitations of version one.
- **Security from the start:** every Git or file operation must stay inside the configured repository and be read-only. Add input limits and validation as each operation is introduced; Part 7 hardens and tests the complete boundary.
- **Version decision:** pin compatible FastMCP 4 and MCP Python SDK v2 versions. Use FastMCP for the server; the existing custom client still uses the official SDK. Check each library's documentation before coding and avoid mixing examples from different releases. Confirm DeepSeek API access before Part 6; Parts 1–5 work without it.
- **Time check:** the brief estimates 30–40 hours over 14 days. That is ambitious for a first MCP project, especially with HTTP, caching, and a custom client. Keep each part working before expanding it.

## Part 1 — Project foundation and MCP conversation (roughly days 1–2)

**Goal:** prove that your own client can start and talk to your own server.

### Topics to learn

1. Python project structure, `uv`, virtual environments, and CLI entry points.
2. MCP host, client, and server roles; what a tool is; how capability discovery works.
3. JSON-RPC request, response, and error shapes; MCP initialization and lifecycle.
4. `stdio` transport, asynchronous Python basics, and why protocol output must stay separate from diagnostic logs.
5. Basic Pydantic input models and small, structured tool results.

### Build

- Initialize the package, configuration, and a fixed `REPOSITORY_PATH`.
- Add an MCP server exposing `get_repository_name` and `get_repository_status`.
- Add a custom client that launches the server, initializes a session, lists tools, prints their schemas, and calls both tools.
- Inspect the same server with MCP Inspector. Keep analysis logic outside the server handlers.

### Done when

- The client discovers and invokes both tools; an unknown tool produces a controlled error.
- A missing or invalid repository path fails with a clear message.
- You can explain the messages exchanged from connection through tool result.

**Likely files:** `pyproject.toml`, `src/repotime/config.py`, `server.py`, `client.py`.

## Part 2 — Git history engine and factual MCP data (roughly days 3–4)

**Goal:** return verifiable repository history without an LLM.

### Topics to learn

1. Git commits, trees, blobs, parent commits, SHAs, branches, and revision ranges.
2. Git log, show, and diff; how file history behaves across renames and merges.
3. GitPython or safe Git CLI usage; avoiding user-controlled shell commands.
4. Path normalization, repository containment, revision validation, pagination, and result-size limits.
5. MCP tools versus resources versus resource templates; URI design and discovery.

### Build

- Write a Git engine with `list_commits`, `get_commit_details`, `get_file_history`, and `compare_revisions` as independent functions.
- Expose these as MCP tools with bounded inputs and structured outputs containing commit SHAs and paths.
- Add `repo://metadata`, `repo://commit/{sha}`, and `repo://file/{sha}/{path}` resources or templates.
- Make a tiny fixture repository with known commits and file changes.

### Done when

- Results match manual Git inspection for known commits.
- Your client can read a historical file at two SHAs and see the expected differences.
- Invalid revisions, missing files, traversal attempts, and oversized requests fail safely.

**Likely files:** `analysis/git_engine.py`, `analysis/diff_engine.py`, `tools/git_tools.py`, `resources/repository.py`, `tests/test_git_engine.py`.

## Part 3 — Python function evolution (roughly day 5)

**Goal:** identify how a named function changed across commits.

### Topics to learn

1. Python `ast.parse`, `FunctionDef`, `AsyncFunctionDef`, classes, decorators, and source line spans.
2. Qualified function names, nested functions, methods, signatures, annotations, and calls.
3. Comparing function snapshots: source diff versus structural changes.
4. Parse failures, deleted functions, and commits where the file did not exist.

### Build

- Parse a historical Python file from a Git blob, without checking out that commit.
- Implement `get_function_at_revision`, `trace_function_evolution`, and `compare_function_versions`.
- Report the SHA, path, qualified name, line numbers, signature, and meaningful changes for every snapshot.
- Test against a fixture history that adds, edits, and deletes a function.

### Done when

- You can name the commits that changed a function and show what changed at each one.
- A syntax error or missing function returns a useful result instead of crashing the server.
- You can state which changes the AST can detect and which require reading the diff.

**Likely files:** `analysis/ast_engine.py`, `tools/function_tools.py`, `tests/test_ast_engine.py`.

## Part 4 — Dependency graph and impact analysis (roughly day 6)

**Goal:** connect function history to a cautious estimate of affected code.

### Topics to learn

1. Static call graphs, directed edges, callers versus callees, and NetworkX traversal.
2. Import resolution and its limits: aliases, dynamic calls, reflection, and runtime dispatch.
3. Direct versus transitive impact; why graph reachability means *potential* impact.
4. Reading Python imports and call expressions with AST; recording unresolved calls instead of guessing their targets.

### Build

- Build a graph for clearly resolvable calls in the current repository revision. Record unresolved calls separately.
- Implement `get_function_dependencies` and `analyze_change_impact` with depth and result limits.
- Expose the two analyses as MCP tools and call them from the client against the known fixture.

### Done when

- A known `A -> B -> C` fixture produces the expected callers, dependencies, and potential impact.
- Outputs distinguish confirmed call edges from unresolved cases; they do not promise that code will break.
- The client can distinguish direct callers, indirect callers, and unresolved calls without DeepSeek.

**Likely files:** `analysis/dependency_graph.py`, `tools/impact_tools.py`, `tests/test_dependency_graph.py`.

## Part 5 — MCP prompts and investigation workflows (roughly day 7)

**Goal:** make repeatable investigation instructions available through MCP, using the Git, function, and impact tools already built.

### Topics to learn

1. MCP prompt discovery and retrieval: `prompts/list` and `prompts/get`.
2. Prompt arguments and the messages a server returns to a client.
3. How a prompt suggests a workflow while the client or model decides which tool calls to make.
4. How to separate Git evidence, potential impact, and inferred explanations in an investigation.

### Build

- Add `investigate_function_change`, `explain_commit`, and `analyze_revert_impact` prompts.
- Register them on the existing MCP server and extend the client to list and retrieve prompts with arguments.
- Use a retrieved prompt to guide one investigation with the existing MCP tools and resources, without DeepSeek.

### Done when

- The client discovers all three prompts and retrieves each with valid arguments.
- One investigation produces verifiable SHAs and paths, plus cautious impact claims, using only MCP calls.
- You can explain that retrieving a prompt returns instructions and does not itself execute tools.

**Likely files:** `prompts/investigation.py`, `server.py`, `client.py`, `tests/test_mcp_prompts.py`.

## Part 6 — DeepSeek agent and evidence-backed answers (roughly days 8–9)

**Goal:** turn a natural-language question into bounded MCP calls and a verifiable answer.

### Topics to learn

1. DeepSeek function/tool calling and conversion from discovered MCP tool schemas.
2. The model -> tool call -> MCP result -> model loop, including multiple calls and stop conditions.
3. Model-generated arguments as untrusted input; timeouts and maximum iterations.
4. Evidence provenance, citation design, context-window limits, and hallucination checks.

### Build

- Add the natural-language CLI and the DeepSeek orchestration loop.
- Feed the model the tools discovered from the server, not a separate hard-coded list.
- Set a maximum number of tool calls, response-size limits, and clear handling for tool errors.
- Require answers to cite actual SHAs, paths, and relevant source locations. Separate observations from inferred explanations.
- Create five questions with known expected evidence; test at least one that requires multiple tools.

### Done when

- The CLI answers a function-history question with citations that you can verify against Git.
- It says when evidence is insufficient and does not invent commits or file paths.
- It terminates cleanly when the model requests bad arguments or too many calls.

**Likely files:** `agent.py`, CLI entry point, `tests/test_integration.py`.

## Part 7 — Second transport, reliability, and handoff (roughly days 10–14)

**Goal:** make the completed application safe, testable, repeatable, and usable by another developer.

### Topics to learn

1. Streamable HTTP versus stdio, session behavior, and concurrent clients.
2. Trust boundaries, symlinks, path traversal, secret handling, and structured errors.
3. SQLite cache keys and invalidation; why immutable commit SHAs are easier to cache than moving branch names.
4. Async concurrency, logging, latency measurement, and request correlation IDs.
5. Unit, MCP integration, and end-to-end tests; Python packaging and clean installation.

### Build

- Add Streamable HTTP and connect with an HTTP MCP client. Compare results with stdio.
- Review every tool and resource for repository containment, input limits, read-only behavior, timeouts, and secret exposure.
- Add SQLite caching for repeated historical AST work, keyed by SHA and path; check cached and uncached results match.
- Log useful timing and errors without logging API keys or sensitive file contents.
- Run tests at three levels: analysis engine, MCP protocol, and DeepSeek investigation.
- Write a README with setup, configuration, run commands, limitations, and three reproducible demonstrations.

### Done when

- The same investigation works over both transports.
- Tests cover malformed inputs and concurrent requests; the full suite passes.
- A clean install can reproduce the three demos, and every cited SHA/path can be checked.
- The completion checklist in `project.md` is satisfied or remaining limitations are stated plainly.

**Likely files:** `storage/cache.py`, `tests/test_security.py`, `tests/test_resources.py`, `README.md`, `docs/architecture.md`, `docs/protocol-notes.md`.

## Practical study order

Before each part, read only the topics listed for that part. Then implement the smallest working version, run its **Done when** checks, and record what you learned. Use the official documentation linked in `project.md` for MCP, Git, Python AST, NetworkX, DeepSeek, and pytest. Keep one small fixture repository throughout the project so each new feature has known evidence to check against.

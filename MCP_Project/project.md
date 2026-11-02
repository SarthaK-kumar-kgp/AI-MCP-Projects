# RepoTime Machine

**An AI-powered Git repository archaeologist built with Model Context Protocol (MCP).**

RepoTime Machine is a learning-focused project designed to explore MCP from fundamentals to advanced concepts by building a practical developer tool from scratch.

The application allows developers to investigate Git history, understand how functions evolved, identify dependencies, and estimate the impact of code changes through natural-language questions.

**Duration:** 14 days (~30–40 hours)  
**Language:** Python  
**Core technologies:** MCP, Git, Python AST, NetworkX, SQLite, DeepSeek API  
**Cost:** Free local infrastructure; DeepSeek usage depends on existing API credits or quota.

---

## 1. Project Objective

The primary objective is to understand MCP deeply by implementing both an MCP server and a custom MCP client.

Rather than building a simple tool wrapper, this project explores:

- MCP architecture and protocol fundamentals
- JSON-RPC communication
- Client-server interaction
- Tools, resources, resource templates, and prompts
- Capability discovery and protocol lifecycle
- stdio and Streamable HTTP transports
- LLM tool-calling orchestration
- Structured outputs and error handling
- Security, validation, and access restrictions
- Asynchronous execution and concurrency
- Testing, observability, and performance optimization

By the end, the project should be a functional application and a practical demonstration of MCP engineering.

## 2. Problem Statement

Understanding why a particular function changed in a large repository can require manually inspecting Git commits, comparing historical file versions, and tracing dependencies.

Existing code assistants often focus on the current state of a repository rather than its evolution.

RepoTime Machine aims to answer questions such as:

- Why was a particular function modified?
- Which commits changed its implementation?
- How did its behavior evolve over time?
- Which functions depend on it?
- What might break if a particular change is reverted?
- What evidence supports the explanation?

The application combines deterministic repository analysis with LLM-based reasoning.

**Important:** The system should distinguish verified Git facts from inferred explanations. It cannot reliably determine developer intent without supporting evidence.

## 3. System Architecture

```text
                 USER
                   |
                   v
           Natural Language CLI
                   |
                   v
          +-------------------+
          |  DeepSeek Agent   |
          |  MCP Client       |
          |                   |
          | Tool Discovery    |
          | Tool Orchestration|
          +-------------------+
                   |
              MCP Protocol
             (JSON-RPC)
                   |
          stdio / HTTP
                   |
                   v
       +-------------------------+
       | RepoTime MCP Server     |
       |                         |
       | Tools                   |
       | Resources               |
       | Resource Templates      |
       | Prompts                 |
       |                         |
       | Validation / Security   |
       +-------------------------+
                   |
                   v
       +-------------------------+
       | Repository Analysis     |
       |                         |
       | Git History Engine      |
       | Python AST Parser       |
       | Dependency Graph        |
       | Change Impact Analyzer  |
       +-------------------------+
                   |
             +-----+-----+
             |           |
             v           v
       Local Git      SQLite
       Repository     Cache
```

### Component responsibilities

**MCP Server**

Exposes repository-analysis capabilities through standardized MCP primitives. Does not require an LLM to operate.

**MCP Client**

Connects to the server, discovers capabilities, invokes tools, and handles results.

**DeepSeek Orchestrator**

Converts discovered tool schemas into LLM-compatible tool definitions, executes the model's requested MCP calls, and produces evidence-grounded answers.

**Repository Analysis Engine**

Performs deterministic Git, AST, and dependency analysis independently of MCP.

## 4. Core Features

### 4.1 Git History Investigation

Inspect commits, retrieve file history, and identify changes.

Planned tools:

| Tool | Description |
|---|---|
| `list_commits` | Retrieve recent commits with filters |
| `get_commit_details` | Inspect commit metadata and changed files |
| `get_file_history` | Find commits affecting a file |
| `compare_revisions` | Compare two Git revisions |

### 4.2 Function Evolution Analysis

Track Python functions across repository history.

Planned tools:

| Tool | Description |
|---|---|
| `get_function_at_revision` | Retrieve a function at a specific commit |
| `trace_function_evolution` | Identify changes across revisions |
| `compare_function_versions` | Compare signatures, calls, and implementations |

Use Python's `ast` module to analyze:

- Function definitions
- Parameters and return annotations
- Decorators
- Function calls
- Structural code changes

### 4.3 Dependency and Impact Analysis

Construct a static dependency graph.

Planned tools:

| Tool | Description |
|---|---|
| `get_function_dependencies` | Retrieve dependencies and callers |
| `analyze_change_impact` | Estimate potentially affected functions |

Use NetworkX for graph representation and traversal.

**Limitation:** Static analysis cannot reliably resolve all dynamic calls, reflection, or runtime dispatch. Results must be labeled as potential impact, not guaranteed impact.

### 4.4 MCP Resources

Expose repository data as addressable resources.

Example resource URI designs:

```text
repo://metadata
repo://commit/{sha}
repo://file/{sha}/{path}
```

Resource templates allow clients to discover parameterized resource locations.

### 4.5 MCP Prompts

Provide reusable investigation workflows.

Planned prompts:

- `investigate_function_change`
- `explain_commit`
- `analyze_revert_impact`

Prompts provide reusable instructions and context. They do not automatically execute tools.

### 4.6 Natural-Language Investigation

Integrate DeepSeek with the custom MCP client.

Example:

```text
User:
Why was authenticate_user() modified?

Agent:
1. Discover available MCP tools.
2. Search the function's Git history.
3. Retrieve relevant commits.
4. Compare historical implementations.
5. Inspect related dependencies.
6. Generate an evidence-backed explanation.
```

The final answer should reference actual commit SHAs, file paths, and relevant source evidence.

## 5. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python 3.11+ |
| MCP server | FastMCP 4 |
| MCP client | Official Python MCP SDK v2 |
| LLM | DeepSeek API |
| Git analysis | GitPython / Git CLI |
| Code parsing | Python `ast` |
| Graph analysis | NetworkX |
| Caching | SQLite |
| Validation | Pydantic |
| Testing | pytest, pytest-asyncio |
| Package management | uv |
| Interface | CLI |
| Transport | stdio, Streamable HTTP |

Use pinned, compatible FastMCP and MCP SDK versions. Verify each library's current API before implementation; examples from different releases may not be interchangeable. The custom client still uses the official SDK until it is migrated separately.

## 6. Project Structure

```text
repo-time-machine/
|
|-- README.md
|-- pyproject.toml
|-- .env.example
|-- .gitignore
|
|-- src/
|   |-- repotime/
|       |-- server.py
|       |-- client.py
|       |-- agent.py
|       |-- config.py
|       |
|       |-- tools/
|       |   |-- git_tools.py
|       |   |-- function_tools.py
|       |   |-- impact_tools.py
|       |
|       |-- analysis/
|       |   |-- git_engine.py
|       |   |-- ast_engine.py
|       |   |-- dependency_graph.py
|       |   |-- diff_engine.py
|       |
|       |-- resources/
|       |   |-- repository.py
|       |
|       |-- prompts/
|       |   |-- investigation.py
|       |
|       |-- storage/
|           |-- cache.py
|
|-- tests/
|   |-- fixtures/
|   |-- test_git_engine.py
|   |-- test_mcp_tools.py
|   |-- test_resources.py
|   |-- test_security.py
|   |-- test_integration.py
|
|-- docs/
    |-- architecture.md
    |-- protocol-notes.md
```

Keep the analysis engine independent of the MCP layer.

## 7. Development Roadmap — 14 Days

### Phase 1: MCP Fundamentals (Days 1–4)

#### Day 1 — MCP Architecture and First Server

**Learn:**
- What MCP is and why it exists
- Host, client, and server responsibilities
- JSON-RPC fundamentals
- MCP tools
- stdio communication

**Build:**
- Initialize the Python project.
- Install FastMCP for the server and the MCP SDK for the custom client.
- Implement `get_repository_name`.
- Implement `get_repository_status`.
- Inspect the server using MCP Inspector.

**Deliverable:** A functioning MCP server exposing two tools.

**Test:** Discover and invoke both tools successfully.

#### Day 2 — Custom MCP Client

**Learn:**
- Client-server communication
- Capability discovery
- Protocol lifecycle and metadata
- Tool invocation and result handling

**Build:**
- Implement `client.py`.
- Launch and connect to the server.
- Discover available tools.
- Display tool schemas.
- Invoke tools and inspect responses.

**Deliverable:** A custom MCP client communicating with the server.

**Test:** Verify successful calls and unknown-tool failures.

#### Day 3 — Git History Engine

**Learn:**
- Git commits, trees, and revisions
- Tool input validation
- Structured outputs
- Deterministic tool execution

**Build:**
- Implement `list_commits`.
- Implement `get_commit_details`.
- Implement `get_file_history`.
- Create a test repository with known commits.

**Deliverable:** A working Git history analysis engine exposed through MCP.

**Test:** Compare tool outputs against Git CLI results.

#### Day 4 — Resources and Resource Templates

**Learn:**
- Tools versus resources
- Resource URIs
- Resource templates
- Resource discovery and reading

**Build:**
- Expose repository metadata.
- Expose commit metadata as a resource.
- Implement historical file snapshot resources.
- Add handling for missing commits and files.

**Deliverable:** An MCP server supporting tools and resources.

**Test:** Retrieve the same file at two different commits.

**Milestone 1:** Understand MCP fundamentals and build both sides of the protocol.

---

### Phase 2: Repository Intelligence (Days 5–9)

#### Day 5 — Function Evolution Engine

**Learn:**
- Abstract syntax trees
- Function extraction
- Source comparison
- Structured analysis results

**Build:**
- Parse Python source using `ast`.
- Implement `get_function_at_revision`.
- Implement `trace_function_evolution`.
- Detect signature and implementation changes.

**Deliverable:** Function-level history tracking.

**Test:** Detect known function changes across synthetic commits.

#### Day 6 — Dependency Graph and Impact Analysis

**Learn:**
- Static call graphs
- Directed graphs
- Graph traversal
- Static-analysis limitations

**Build:**
- Extract imports and resolvable function calls.
- Build a dependency graph.
- Implement `get_function_dependencies`.
- Implement `analyze_change_impact`.

**Deliverable:** A basic static impact analyzer.

**Test:** Verify dependencies using a known function call chain.

#### Day 7 — MCP Prompts and Integration

**Learn:**
- MCP prompt discovery
- Prompt arguments
- Reusable investigation workflows
- End-to-end MCP testing

**Build:**
- Add investigation prompts.
- Implement prompt discovery in the client.
- Combine Git history and function analysis.
- Test tools, resources, and prompts together.

**Deliverable:** Complete MCP server v1.

**Test:** Investigate a function without using DeepSeek.

#### Day 8 — DeepSeek Integration

**Learn:**
- LLM function calling
- Tool schema conversion
- Multi-turn tool execution
- Agent orchestration

**Build:**
- Connect DeepSeek.
- Convert MCP tools into DeepSeek tool definitions.
- Implement the model → tool → result loop.
- Add a maximum tool-call iteration limit.
- Implement a natural-language CLI.

**Deliverable:** An AI-powered repository investigator.

**Test:** Ask a question requiring multiple MCP calls.

#### Day 9 — Evidence-Grounded Answers

**Learn:**
- Evidence provenance
- Hallucination mitigation
- Structured results
- Context-window management

**Build:**
- Include commit SHAs in analysis results.
- Include file paths and source locations.
- Require evidence references in final answers.
- Implement output-size limits.
- Create five evaluation questions.

**Deliverable:** An evidence-grounded code archaeologist.

**Test:** Verify that referenced commits and files exist.

**Milestone 2:** Natural-language Git investigation using DeepSeek and MCP.

---

### Phase 3: Advanced MCP Engineering (Days 10–14)

#### Day 10 — Streamable HTTP

**Learn:**
- stdio versus HTTP
- Transport independence
- HTTP protocol metadata
- Concurrent client connections

**Build:**
- Expose the MCP server over Streamable HTTP.
- Connect using an HTTP MCP client.
- Compare stdio and HTTP behavior.
- Test multiple clients.

**Deliverable:** MCP server supporting two transports.

**Test:** Execute equivalent investigations through both transports.

#### Day 11 — Security and Error Handling

**Learn:**
- Trust boundaries
- Tool argument validation
- Filesystem security
- Error handling and timeouts

**Build:**
- Restrict operations to a configured repository.
- Reject path traversal and unsafe symlinks.
- Prevent arbitrary command execution.
- Add structured errors.
- Add timeouts and output limits.

**Deliverable:** A safer read-only MCP server.

**Test:** Attempt invalid paths, revisions, and oversized operations.

#### Day 12 — Caching and Observability

**Learn:**
- Performance measurement
- Structured logging
- Cache invalidation
- Request tracing

**Build:**
- Implement SQLite caching.
- Cache AST results by commit SHA and path.
- Log tool execution latency.
- Add request correlation identifiers.
- Benchmark cached and uncached operations.

**Deliverable:** Observable repository analysis.

**Test:** Verify equivalent cached results and measurable cache hits.

#### Day 13 — Testing and Reliability

**Learn:**
- Unit testing
- MCP integration testing
- Protocol contract testing
- Failure handling
- Evaluation methodology

**Build:**
- Write unit tests for Git and AST analysis.
- Test tool discovery and invocation.
- Test resources and prompts.
- Test malformed inputs and concurrent requests.
- Evaluate five natural-language investigations.

**Deliverable:** Automated test suite.

**Test:** Run all tests and document known failures.

#### Day 14 — Packaging and Documentation

**Learn:**
- Python packaging
- Reproducibility
- Architecture documentation
- Deployment considerations

**Build:**
- Create CLI entry points.
- Finalize README and installation instructions.
- Document architecture and limitations.
- Prepare three demonstration scenarios.
- Run a clean installation test.

**Deliverable:** Portfolio-ready RepoTime Machine.

**Test:** A new developer can install the project and reproduce the demonstration.

**Milestone 3:** A reusable, tested, and documented MCP application.

---

## 8. Installation and Development Setup

### Prerequisites

- Python 3.11+
- Git
- uv
- DeepSeek API access (required only for AI integration)

### Initialize the project

```bash
uv init repo-time-machine
cd repo-time-machine
```

### Install dependencies

```bash
uv add "fastmcp==4.1.4" "mcp==2.3.0" gitpython python-dotenv pydantic networkx
uv add --dev pytest pytest-asyncio
```

Additional dependencies will be introduced when their corresponding features are implemented.

### Configure DeepSeek

Create a local `.env` file or configure the environment:

```text
DEEPSEEK_API_KEY=your_api_key
REPOSITORY_PATH=/path/to/local/repository
```

Never commit API keys or `.env` files to Git.

The exact server and client run commands will be documented once the CLI entry points are implemented.

## 9. Testing Strategy

Testing should be performed at three independent levels.

### Level 1 — Repository Analysis

Test Git history, AST parsing, function evolution, and dependency graphs without MCP.

### Level 2 — MCP Protocol

Test tool discovery, invocation, resource reading, prompt retrieval, structured outputs, and error responses without DeepSeek.

### Level 3 — AI Integration

Test whether DeepSeek selects appropriate tools, uses returned evidence, and generates accurate explanations.

Evaluation questions should have known expected evidence.

Example:

```text
Question:
Which commit changed calculate_total()?

Expected:
- Correct commit SHA
- Correct file path
- Correct function change
- No fabricated references
```

Track:

- Tool-call correctness
- Commit retrieval accuracy
- Evidence validity
- Answer correctness
- End-to-end latency
- Failure rate

## 10. Security Requirements

The MCP server must:

1. Operate only on an explicitly configured local repository.
2. Use read-only Git operations.
3. Reject filesystem access outside the repository.
4. Validate file paths, commit references, and input sizes.
5. Avoid arbitrary shell execution.
6. Limit expensive queries.
7. Avoid exposing secrets in logs or tool responses.
8. Treat model-generated tool arguments as untrusted input.

The first version should not modify repository files or execute user-provided commands.

## 11. Scope and Limitations

To complete the project in two weeks, the initial implementation supports:

- Local Git repositories
- Python source files
- Git history and function evolution
- Basic static dependency analysis
- CLI-based interaction
- One MCP server
- One custom MCP client

Out of scope:

- Full multi-language support
- Web-based dashboards
- Production OAuth deployment
- Automatic code modification
- Full program analysis
- Distributed multi-agent architecture
- Large-scale semantic search

These can be considered future extensions.

## 12. Definition of Done

The project is complete when:

- [ ] The MCP server starts successfully.
- [ ] A custom MCP client connects successfully.
- [ ] Tools can be discovered and invoked.
- [ ] Historical repository data is accessible through resources.
- [ ] Investigation prompts can be retrieved.
- [ ] Git history analysis works correctly.
- [ ] Python function evolution can be tracked.
- [ ] Basic dependencies can be identified.
- [ ] DeepSeek can perform multi-step investigations.
- [ ] Answers contain verifiable evidence.
- [ ] Both stdio and Streamable HTTP work.
- [ ] Repository access restrictions are enforced.
- [ ] Automated tests pass.
- [ ] Installation and usage are documented.
- [ ] At least three end-to-end demonstrations are reproducible.

## 13. Learning Outcomes

After completing this project, you should be able to explain:

1. How MCP differs from a conventional REST API.
2. How MCP hosts, clients, and servers interact.
3. How JSON-RPC messages are exchanged.
4. How MCP tools are defined and discovered.
5. When to use resources instead of tools.
6. How resource templates work.
7. How MCP prompts are exposed and retrieved.
8. How stdio and Streamable HTTP differ.
9. How an LLM interacts with an MCP client.
10. How to implement a multi-step tool-calling loop.
11. How to secure MCP tool execution.
12. How to test an MCP server independently of an LLM.

## 14. Learning Resources

**MCP**
- [Official MCP Documentation](https://modelcontextprotocol.io/)
- [MCP Specification](https://modelcontextprotocol.io/specification/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)

**Git**
- [Pro Git Book](https://git-scm.com/book/en/v2)
- [GitPython Documentation](https://gitpython.readthedocs.io/)

**Python Analysis**
- [Python AST Documentation](https://docs.python.org/3/library/ast.html)
- [NetworkX Documentation](https://networkx.org/documentation/stable/)

**LLM Integration**
- [DeepSeek API Documentation](https://api-docs.deepseek.com/)

**Testing**
- [pytest Documentation](https://docs.pytest.org/)

## 15. Future Extensions

Once the core project is complete, possible improvements include:

- Support for JavaScript and TypeScript repositories
- Semantic code search
- Cross-repository dependency analysis
- GitHub pull-request investigation
- Multi-server MCP architecture
- Change-risk scoring
- Automated regression investigation
- Interactive dependency visualization

---

## Final Goal

**Build a reliable MCP-based application that can explain how a Python codebase evolved, using verifiable Git evidence and deterministic analysis.**

The project is successful not merely when DeepSeek can answer questions, but when the developer understands how MCP capabilities are exposed, discovered, invoked, secured, tested, and integrated into an AI application.

**Build the protocol foundation first. Add intelligence second. Improve reliability last.**

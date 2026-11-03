# What I learned building RepoTime Machine

I am keeping this as a story of what I tried, what broke, and why the fix made sense. When I change the project again, I should add the next lesson here in the same style.

## Part 1: Getting the server and client to agree

I learned that the server should read the configured repository path when a tool runs. I put path reading in `config.py` and Git inspection in `analysis/repository.py`. This keeps imports simple and lets me check Git behavior without starting MCP. When I briefly moved `repository.py` under `tools/`, the server import broke; that showed me the difference between analysis code and MCP wrappers.

I also learned that a console command needs a normal `main()` function. My FastMCP client uses async calls, so `main()` starts that async work. The client launches the server over stdio and must pass `REPOSITORY_PATH` to that child process; otherwise the server can use a different path from `.env`. Listing tool names and input schemas helped me see what a client is actually allowed to call.

## Part 2: Reading commits and historical files

I first tried to put GitPython `Commit` objects directly into my Pydantic `CommitList`. Validation failed because the model expects `CommitSummary` objects. I now convert each Git commit into a small summary with its SHA, subject, and timezone-aware date. I keep `CommitDetails` for one commit's author, message, parent SHAs, and changed files. This lets a history list stay compact while a separate call gives the full details.

I mistakenly used `.a_path` on entries from `commit.stats.files`. Those entries are already path strings, so I changed the code to use the dictionary keys directly. I also used `path=` with `repo.iter_commits`, which GitPython passed to Git as an invalid option. `paths=` works. I use Git's literal pathspec so a filename containing wildcard characters is treated as one path.

Loading every matching commit would make tool results grow without limit. I added `limit`, `offset`, and `has_more`; fetching one extra commit tells me whether another page exists. An empty repository returns an empty list because it has no valid `HEAD` yet. I made bad revisions and missing files produce clear errors, and historical file results use the resolved commit SHA even if I asked for `HEAD`. File paths are checked before use, and historical content is limited to UTF-8 text of at most 1 MB.

## Comparing two Git snapshots

I originally treated a diff as one changed file. A comparison can affect many files: GitPython returns a `DiffIndex` containing one `Diff` per file. I also learned that the order matters. Comparing old to new shows additions as additions; reversing the commits makes them appear as deletions. My public function now accepts any two revisions and returns a `RevisionDiff` containing separate `FileDiff` results.

I expected each `Diff` to have `added_lines` and `deleted_lines`, but those attributes do not exist. With `create_patch=True`, each file's `.diff` contains patch bytes with the changed lines; in that mode GitPython did not provide a useful `change_type` in my checks. I therefore obtain file statuses and patches separately, pair them by path, and count `+` and `-` lines in the patches. This also lets me preserve rename paths instead of calling every unfamiliar status a deletion.

I limit a comparison to 100 files and return at most 100,000 bytes of patch text. Binary files have no text patch or line counts in the result. GitPython still computes the full patch before I trim the returned text, so memory use on very large diffs remains a later hardening task. The test repository matched Git's file statuses and line counts; rename, binary, oversized patch, and invalid-revision checks passed too.

## Turning analysis functions into MCP tools

My first `git_tools.py` created another `FastMCP` server. The real `repotime-server` starts the instance in `server.py`, so the tools on the second instance were invisible there. I replaced that setup with `register_mcp_tools(mcp)`, and `server.py` now passes its own instance to it. A local tool listing shows the two original tools and all six new Git tools.

I first made every wrapper call `get_repository_status`, even though each wrapper needed a different analysis function. When I changed the calls but reused the analysis function names for the wrappers, each wrapper called itself. Giving wrappers distinct `_tool` names fixed that. I also removed registration of the raw `get_repository_status` analysis function: it would have let the client choose a repository path, while the server's existing wrapper uses the configured path.

I corrected the tool docstrings because FastMCP turns them into tool descriptions and parameter guidance for MCP clients. The remaining cleanup is to replace star imports with explicit imports and annotate `offset` as `int` in `get_commit_list_tool`; its current MCP schema has a description but no integer type.

## Calling the tools from my client

I confused tool discovery with tool execution. `client.list_tools()` told me which tools exist and showed their input schemas, but my next loop called every tool without arguments. That worked for repository status and failed as soon as a tool required SHAs. A schema tells me the names and types of arguments; it does not supply real commit SHAs or file paths.

I changed the client into a small investigation workflow. It first lists commits, uses their returned SHAs to inspect and compare commits, and takes a changed file path from the comparison to request file history and content. Each `call_tool` now receives the arguments that particular tool needs. An empty repository skips history calls, and expected invalid-revision and unknown-tool errors are checked separately. I verified this through a real stdio connection to the local test repository.

## Giving Git evidence a resource URI

I initially exposed historical files only through tools. That let a client ask the server to perform a lookup, but Part 2 also calls for MCP resources: data that a client can discover and read by URI. I added `repo://metadata` for the configured repository, plus templates for a commit and a file at a revision. I registered them on the same FastMCP server as the tools, because a separate instance would leave them invisible to `repotime-server`.

My first file URI shape could have treated a nested path as several URI segments. I used FastMCP's `{path*}` wildcard in the template so `src/shop/pricing.py` reaches one `path` argument. The resource then calls the existing Git analysis function. This means the tool and resource agree on file contents and share the same checks for invalid paths, missing files, binary text, and the 1 MB limit. For JSON resources, I convert the Pydantic models to dictionaries before FastMCP serializes them.

I added resource discovery and `read_resource` calls to the client. Reading `repo://metadata` and `repo://commit/{sha}` showed me that JSON resources arrive as text that the client must parse. Reading a file at two commit SHAs showed the same path can have different contents over time. I checked both snapshots against `git show`, and the client checks that the file resource agrees with the corresponding tool. Invalid revisions, missing files, traversal paths, and an oversized file were rejected at the resource boundary.

## Part 3: Finding a function at a commit

I first raised an error when a function was absent, which meant a comparison could not represent a function being added or removed. I then tried a broad `except Exception` around the AST search and returned `None` from it. That could hide a real search bug by treating it as “function not found.” I changed the lookup to return `None` only after searching every node, and declared its result as `FindFunction | None`. Errors while reading or parsing the file can now remain distinct from a missing function. I checked both a present function and a missing function against the test repository.

My first lookup returned the first function with a matching short name. That could pick `Cart.calculate` when I meant `Invoice.calculate`. I changed it to track class and function scopes, accept a qualified name, and reject an ambiguous short name. I also realized that a snapshot cannot list changes by itself: it describes one commit, while a comparison needs two snapshots. The finder now returns only the selected function's identity, location, and exact source, including trailing comments inside the function that the AST's ending line can miss.

I then put signature, docstring, parameter, decorator, and comment analysis inside the finder. That gave the finder the comparison's job and made its result too large. I moved that analysis into `get_function_comparison`. It compares two snapshots, reports which kinds of syntax changed, and provides a unified source diff with every changed line. Tokenizing there identifies comments without confusing `#` inside a string for a comment. I checked parameter, docstring, comment, and body edits, plus add/remove, comment-only, and formatting-only cases. The diff shows exact text; the AST categories describe syntax changes, not proof of runtime behavior.

I added `trace_function_evolution` after the finder and comparison. I first needed a way to avoid treating every file edit as a function edit, so the trace reads the file's commit history, compares each commit to its first parent, and keeps only comparisons where the selected function changed. The first commit has no parent; a function there is an addition. A file can also be absent on one side of a comparison, so the trace treats that specific missing-file case as an added or removed function while leaving parsing and other errors visible. I return the selected page in chronological order and keep `has_more` from file history so a long history can be requested in bounded pages. A temporary Git history confirmed that unrelated file edits are skipped and that function and file removals are recorded.

When I registered the AST lookup as an MCP tool, I annotated its wrapper as returning `FunctionComparison` even though it returns `FindFunction | None`. FastMCP used that annotation as the output schema, so a successful lookup failed response validation. I changed the annotation to match the real result and checked both a found function and a missing function through an MCP client.

I also described the lookup tool as a two-commit comparison and said the evolution tool returned Git log order. Those docstrings were misleading because FastMCP exposes them as tool descriptions. I corrected them to describe each tool's actual result and the evolution page's chronological order, then checked the descriptions through tool discovery.

## What I need to check next

I have verified the Git tools and resources through the stdio client. Part 2's historical and error checks pass. The three Part 3 tools are registered and passed stdio checks for lookup, comparison, evolution, missing functions, and syntax errors. An MCP Inspector check from Part 1 is still pending. Part 4 adds dependency impact and MCP prompts.

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

## What I need to check next

I have verified the new tools and their error behavior through the stdio client. I still need to add the Part 2 repository resources before treating Part 2 as complete and moving to Part 3. I also still need to inspect the server with MCP Inspector.

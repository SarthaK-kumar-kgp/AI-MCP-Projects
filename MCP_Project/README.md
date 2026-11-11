# MCP Projects

This folder collects projects I am building to learn and use the Model Context Protocol (MCP). Each application gets its own folder and README, so this page can serve as an index as more projects are added.

| Folder | What it contains |
| --- | --- |
| [repo-time-machine](repo-time-machine/) | **Project 1: RepoTime Machine**, an MCP application for exploring the history of a local Git repository. |

The local `test-repo/` folder, when present, is a Git history fixture for RepoTime Machine. It is not a second MCP application or part of this published project index.

## Project 1: RepoTime Machine

RepoTime Machine helps investigate how Python code changed over time. Its read-only MCP server exposes Git history, file and commit comparisons, function evolution, and possible function dependencies through tools, resources, and prompts. A separate DeepSeek host prototype can use those tools to answer questions with repository evidence. The server features are in place; the host and final end-to-end checks are still in progress.

Start with the [project README](repo-time-machine/README.md) for setup and available features. The [project brief](repo-time-machine/docs/project.md), [seven-part roadmap](repo-time-machine/docs/ROADMAP_6_PARTS.md), and [learning notes](repo-time-machine/learning.md) explain the plan and what I learned while building it.

When I add another MCP project, I can give it its own folder and add one row to the table above.

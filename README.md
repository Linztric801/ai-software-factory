# AI Software Factory

Turns labelled GitHub issues into reviewed pull requests with a team of AI
agents: intake → spec → build → gate → review → approve, one PR per issue.
Every step is checked by code, not by trust: a job moves to the next stage
only when the files that justify the move exist, the branch passes the
project's checks from its base branch, and no protected file was changed.

Status: **extraction in progress.** The platform (web dashboard, API,
sandboxed workers, optional Microsoft Entra ID login) is being built from the
design in `docs/`. What works today is **local mode**.

## Local mode

`local-mode/factory/` is the file-based factory, run from a Claude Code
session in the repository it builds:

- `bin/job`: the state machine and the only writer of `jobs/<id>/job.json`
- `bin/gate`: runs the project's checks in the job's worktree; protected paths
- `bin/route`: picks reviewers and models from intake's risk and surfaces
- `config.example.json`: copy to `factory/config.json` in your repo

Its behaviour is pinned by tests that run the real scripts against a
throwaway git repository and a fake `gh`:

```sh
cd local-mode/tests && python3 -m unittest -v
```

Needs Python 3.11+, git, and the GitHub CLI for real use.

## Configuration

`deploy/.env.example` lists every setting with placeholders. With nothing
configured the factory runs without login and listens on 127.0.0.1 only.

## License

MIT. See `LICENSE`.

# CloudFest After Party

**A CloudFest-style AI software factory for Claude Code.** Install it once as a
plugin, point it at any GitHub repository, and a crew of AI agents turns issues
labelled `factory` into reviewed pull requests:

```
intake → spec → build → gate → review → approve → merge
```

The look and feel is a technology festival in the spirit of CloudFest: agents
work at the main venue, learn in the masterclasses, prove their builds in the
build arena, wait for a human at the Beer Fest, and relax at the after party
when there's nothing to do. The festival is only the presentation. Underneath,
every step is checked by code, not trust: a job moves on only when the files
that justify the move exist, the branch passes the project's checks taken from
its base branch, and no protected file was touched.

> CloudFest After Party is an independent project, not an official CloudFest
> product. CloudFest logos and artwork are not part of this repository.

## Install

In Claude Code:

```
/plugin marketplace add Linztric801/ai-software-factory
/plugin install cloudfest@cloudfest-after-party
```

Then, in the repository you want built:

```
/cloudfest:after-party run          build every open issue labelled `factory`
/cloudfest:after-party run 12       build issue #12
/cloudfest:after-party <anything>   ask about jobs, give feedback, file a feature
```

Nothing of the factory lives in your project. Job state and the agents'
worktrees are kept in `~/.cloudfest-after-party/projects/<owner>-<repo>/`.

## Set up a project

A project needs one thing: a checks script the gate runs on every round.

```
.factory/
  checks.sh      required: exit 0 only when the branch is fit to review
  config.json    optional: overrides of the plugin defaults (concurrency, routing,
                 protected paths, merge method, …)
  profile.md     optional: what the project is, and its rules for each agent:
                 ## Project, ## Intake, ## Dev server, ## Security review,
                 ## UI review, ## UX review, ## Approver
```

`party-job where` shows which project, state folder, settings and checks the
factory found. Settings are layered: the plugin's `config.default.json`, then
`.factory/config.json`, then `~/.cloudfest-after-party/projects/<slug>/config.json`
for machine-local overrides. Protected paths can be added, never removed.

## Safety rules the code enforces

- Only issues with the `factory` label run, and issue text reaches agents only
  as quoted data.
- The gate runs the checks from the main checkout, never from the branch, and
  fails a branch that changes protected files or adds files under `.github/`,
  `.claude/` or `.factory/`.
- Approval and merge act only on the exact commit that passed the gate and the
  reviews; the merge pins that commit.
- A job gets at most `max_rounds` build rounds before a human decides.
- Commits carry no AI attribution trailers.

## Develop

```sh
cd plugin/tests && python3 -m unittest -v
```

The tests run the real scripts against a throwaway git repository and a fake
`gh`. Needs Python 3.11+, git and the GitHub CLI.

`deploy/.env.example` lists the settings of the coming server edition (web
dashboard, API, sandboxed workers, optional Microsoft Entra ID login).

## License

MIT. See `LICENSE`.

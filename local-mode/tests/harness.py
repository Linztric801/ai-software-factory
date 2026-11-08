"""A throwaway factory install for tests: a bare origin, a main checkout with
factory/ copied in, the fake gh on PATH, and an isolated git and Claude config."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "factory" / "bin"
FAKES = HERE / "fakes"

TEST_CONFIG = {
    "concurrency": 2,
    "max_rounds": 2,
    "base_branch": "main",
    "merge_method": "merge",
    "labels": {"queue": "factory", "needs_info": "factory:needs-info", "needs_human": "factory:needs-human"},
    "routing": {"low": {"code": "haiku"}, "medium": {"code": "sonnet"}, "high": {"code": "sonnet"}},
    "surface_reviewers": {"ui": {"ux": "sonnet", "ui": "haiku"}, "security": {"security": "opus"}},
    "protected_paths": ["factory/*", "protected.txt"],
    "ports": {"base": 5100, "step": 10},
    "prices_usd_per_mtok": {
        "claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_write_5m": 5.0, "cache_write_1h": 8.0, "cache_read": 0.20},
    },
}

INTAKE_ACCEPT = "DECISION: ACCEPT\nRESCOPED: no\nRISK: medium\nSURFACES: ui\n\n## Scope\nDark mode for the settings page.\n"


class Factory:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.origin = self.root / "origin.git"
        self.repo = self.root / "repo"
        self.claude = self.root / "claude"
        self.state = self.root / "gh.json"
        self.env = {
            **os.environ,
            "PATH": f"{FAKES}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_STATE": str(self.state),
            "CLAUDE_CONFIG_DIR": str(self.claude),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
        }
        self.env.pop("CHECKS_EXIT", None)
        self.env.pop("FAKE_GH_MERGE_FAILS", None)
        self.state.write_text(json.dumps({"user": "owner", "issues": {}, "prs": {}, "calls": []}))
        self.git(self.root, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.git(self.root, "clone", "-q", str(self.origin), str(self.repo))
        factory = self.repo / "factory"
        shutil.copytree(BIN, factory / "bin")
        (factory / "config.json").write_text(json.dumps(TEST_CONFIG, indent=2))
        (factory / "checks.sh").write_text('echo "checks ran in $PWD"\nexit "${CHECKS_EXIT:-0}"\n')
        (self.repo / ".gitignore").write_text("/factory/jobs/\n/.worktrees/\n")
        (self.repo / "protected.txt").write_text("do not touch\n")
        (self.repo / "app.txt").write_text("v1\n")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-q", "-m", "initial")
        self.git(self.repo, "push", "-q", "origin", "main")

    def close(self):
        self._tmp.cleanup()

    # ---- processes ----------------------------------------------------------

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def run(self, script, *args, stdin=None, env=None):
        return subprocess.run([str(self.repo / "factory" / "bin" / script), *args], cwd=self.repo,
                              env={**self.env, **(env or {})}, input=stdin, capture_output=True, text=True)

    def job(self, *args, **kw):
        return self.run("job", *args, **kw)

    def ok(self, script, *args, **kw):
        res = self.run(script, *args, **kw)
        assert res.returncode == 0, f"{script} {' '.join(args)} failed:\n{res.stdout}{res.stderr}"
        return res.stdout.strip()

    # ---- GitHub fake --------------------------------------------------------

    def gh(self):
        return json.loads(self.state.read_text())

    def set_gh(self, state):
        self.state.write_text(json.dumps(state, indent=2))

    def add_issue(self, n, title, labels=("factory",), state="OPEN", body="Please add it.", author="alice", comments=()):
        gh = self.gh()
        gh["issues"][str(n)] = {
            "number": n, "title": title, "body": body, "author": {"login": author},
            "labels": [{"name": l} for l in labels], "state": state,
            "url": f"https://github.test/o/r/issues/{n}", "comments": list(comments),
        }
        self.set_gh(gh)

    def add_pr(self, n, head, draft=True):
        gh = self.gh()
        gh["prs"][str(n)] = {"number": n, "url": f"https://github.test/o/r/pull/{n}", "head": head,
                             "state": "OPEN", "isDraft": draft, "comments": []}
        self.set_gh(gh)

    def labels(self, n):
        return [l["name"] for l in self.gh()["issues"][str(n)]["labels"]]

    def calls(self, *prefix):
        return [c for c in self.gh()["calls"] if c[:len(prefix)] == list(prefix)]

    # ---- job files ----------------------------------------------------------

    def dir(self, job_id):
        return self.repo / "factory" / "jobs" / job_id

    def write(self, job_id, name, text):
        path = self.dir(job_id) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def load(self, job_id):
        return json.loads((self.dir(job_id) / "job.json").read_text())

    # ---- driving a job like the agents would --------------------------------

    def new_job(self, n=1, title="Add dark mode"):
        self.add_issue(n, title)
        return self.ok("job", "create", str(n))

    def to_build(self, job_id, intake=INTAKE_ACCEPT):
        self.write(job_id, "intake.md", intake)
        self.ok("route", job_id)
        self.ok("job", "advance", job_id, "spec")
        self.write(job_id, "spec.md", "# Spec\n")
        self.ok("job", "advance", job_id, "build")

    def build(self, job_id, files=None, pr=10, status="STATUS: READY"):
        """Commit, push and open the PR as the builder would, then write build.md."""
        job = self.load(job_id)
        wt = Path(job["worktree"])
        for name, text in (files or {"app.txt": f"round {job['round']}\n"}).items():
            (wt / name).write_text(text)
        self.git(wt, "add", "-A")
        self.git(wt, "commit", "-q", "-m", f"round {job['round']}")
        self.git(wt, "push", "-q", "-u", "origin", job["branch"])
        if str(pr) not in self.gh()["prs"]:
            self.add_pr(pr, job["branch"])
        self.write(job_id, "build.md", f"{status}\n\n## Summary\n- built\n")

    def to_review(self, job_id, **kw):
        self.to_build(job_id)
        self.build(job_id, **kw)
        self.ok("job", "advance", job_id, "gate")
        self.ok("gate", job_id)
        self.ok("job", "advance", job_id, "review")

    def review(self, job_id, verdicts):
        n = self.load(job_id)["round"]
        for r, v in verdicts.items():
            self.write(job_id, f"round-{n}/review-{r}.md", f"VERDICT: {v}\n\n## Summary\n- ok\n")

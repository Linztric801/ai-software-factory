"""A throwaway project for tests: a bare origin, a main checkout with a
.factory/ folder, a temporary PARTY_HOME for the factory's state, the fake gh on
PATH, and an isolated git and Claude config. The scripts run from plugin/bin."""

import json
import os
import shutil
import pwd
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin"
ORIGIN_URL = "https://github.test/acme/widgets.git"
SLUG = "acme-widgets"
FAKES = HERE / "fakes"

# The project's .factory/config.json, layered over the plugin's defaults.
TEST_CONFIG = {
    "concurrency": 2,
    "max_rounds": 2,
    "merge_policy": "auto_after_approval",  # like ScanBadge; the HumanApproval tests switch it
    "protected_paths": ["protected.txt", "données.txt"],
}

INTAKE_ACCEPT = "DECISION: ACCEPT\nRESCOPED: no\nRISK: medium\nSURFACES: ui\n\n## Scope\nDark mode for the settings page.\n"


class Factory:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.origin = self.root / "origin.git"
        self.repo = self.root / "repo"
        self.claude = self.root / "claude"
        self.home = self.root / "home"
        self.state = self.root / "gh.json"
        self.env = {
            **os.environ,
            "PATH": f"{FAKES}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_STATE": str(self.state),
            "PARTY_HOME": str(self.home),
            "CLAUDE_CONFIG_DIR": str(self.claude),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
        }
        for var in ("PARTY_REPO", "PARTY_PROJECT"):
            self.env.pop(var, None)
        self.env.pop("CHECKS_EXIT", None)
        self.env.pop("FAKE_GH_MERGE_FAILS", None)
        self.state.write_text(json.dumps({"user": "owner", "issues": {}, "prs": {}, "calls": []}))
        self.git(self.root, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.git(self.root, "clone", "-q", str(self.origin), str(self.repo))
        # origin looks like a GitHub URL; git rewrites it to the local bare repo.
        self.git(self.repo, "remote", "set-url", "origin", ORIGIN_URL)
        self.git(self.repo, "config", f"url.{self.origin}.insteadOf", ORIGIN_URL)
        factory = self.repo / ".factory"
        factory.mkdir()
        (factory / "config.json").write_text(json.dumps(TEST_CONFIG, indent=2))
        (factory / "checks.sh").write_text('echo "checks ran in $PWD"\nexit "${CHECKS_EXIT:-0}"\n')
        (self.repo / "protected.txt").write_text("do not touch\n")
        (self.repo / "données.txt").write_text("protected too\n")
        (self.repo / "app.txt").write_text("v1\n")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-q", "-m", "initial")
        self.git(self.repo, "push", "-q", "origin", "main")

    # Approvals live in the account's real home, out of reach of variables; the
    # test project's folder there is removed after each test.
    approvals = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".cloudfest-after-party-approvals" / "acme-widgets"

    def close(self):
        shutil.rmtree(self.approvals, ignore_errors=True)
        self._tmp.cleanup()

    # ---- processes ----------------------------------------------------------

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def run(self, script, *args, stdin=None, env=None, cwd=None):
        # A new session has no controlling terminal: party-job approve must refuse, and
        # a test run in someone's terminal never prompts them.
        return subprocess.run([str(BIN / f"party-{script}"), *args], cwd=cwd or self.repo,
                              env={**self.env, **(env or {})}, input=stdin, capture_output=True, text=True,
                              start_new_session=True)

    def approve(self, job_id, answer):
        """Run party-job approve with a real terminal, typing `answer` at its prompt."""
        import os
        import pty
        import select
        path = str(BIN / "party-job")
        pid, master = pty.fork()  # the child gets the pty as its controlling terminal
        if pid == 0:
            os.chdir(self.repo)
            os.execve(path, [path, "approve", job_id], self.env)
        out, sent = b"", False
        while True:
            ready, _, _ = select.select([master], [], [], 60)
            if not ready:
                break
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
            if not sent and b"Type the PR number" in out:
                os.write(master, f"{answer}\n".encode())
                sent = True
        _, status = os.waitpid(pid, 0)
        os.close(master)
        return os.waitstatus_to_exitcode(status), out.decode(errors="replace")

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

    def add_pr(self, n, head, draft=True, fork=False, head_sha=None):
        gh = self.gh()
        gh["prs"][str(n)] = {"number": n, "url": f"https://github.test/o/r/pull/{n}", "head": head,
                             "state": "OPEN", "isDraft": draft, "comments": [], "isCrossRepository": fork}
        if head_sha:
            gh["prs"][str(n)]["headRefOid"] = head_sha
        self.set_gh(gh)

    def labels(self, n):
        return [l["name"] for l in self.gh()["issues"][str(n)]["labels"]]

    def calls(self, *prefix):
        return [c for c in self.gh()["calls"] if c[:len(prefix)] == list(prefix)]

    # ---- job files ----------------------------------------------------------

    @property
    def state_dir(self):
        return self.home / "projects" / SLUG

    def dir(self, job_id):
        return self.state_dir / "jobs" / job_id

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

"""Where a project's factory lives.

The plugin is installed once; projects only carry an optional `.factory/`
folder. For the git repository the commands run in, this module finds:

- the main checkout (also when run from inside one of its worktrees),
- the project's state folder, `$PARTY_HOME/projects/<owner>-<repo>/`, holding
  `jobs/`, `worktrees/` and an optional local `config.json`,
- the settings, layered: the plugin's `config.default.json`, then the
  project's `.factory/config.json`, then the local `config.json`. A layer
  overrides keys of the one before; tables merge one level deep, and
  `protected_paths` only ever grows,
- the checks script, `.factory/checks.sh` unless the settings say otherwise.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
DEFAULTS = PLUGIN / "config.default.json"


def die(msg, code=1):
    print(f"party: {msg}", file=sys.stderr)
    sys.exit(code)


def home():
    return Path(os.environ.get("PARTY_HOME") or Path.home() / ".cloudfest-after-party").expanduser()


def main_checkout(start=None):
    """The main checkout of the repository at `start` (default: the working directory)."""
    if os.environ.get("PARTY_REPO"):
        return Path(os.environ["PARTY_REPO"]).resolve()
    res = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         cwd=start or os.getcwd(), capture_output=True, text=True)
    if res.returncode != 0:
        die("not inside a git repository; run this from the project's checkout, or set PARTY_REPO")
    common = Path(res.stdout.strip())
    if common.name != ".git":
        die(f"{common} is a bare repository; run this from a checkout")
    return common.parent


def slug(repo):
    """`owner-repo` from the origin URL as configured, else the checkout's folder name."""
    if os.environ.get("PARTY_PROJECT"):
        return os.environ["PARTY_PROJECT"]
    res = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=repo, capture_output=True, text=True)
    m = re.search(r"([^/:]+)/([^/]+?)(?:\.git)?/?$", res.stdout.strip())
    name = f"{m.group(1)}-{m.group(2)}" if m else repo.name
    return re.sub(r"[^A-Za-z0-9._-]", "-", name)


def _read(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        die(f"{path} isn't valid JSON: {e}")


def merge(base, layer):
    merged = dict(base)
    for key, value in layer.items():
        if key == "protected_paths":
            merged[key] = merged.get(key, []) + [p for p in value if p not in merged.get(key, [])]
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


class Project:
    def __init__(self, start=None):
        self.repo = main_checkout(start)
        self.slug = slug(self.repo)
        self.dir = home() / "projects" / self.slug
        self.jobs = self.dir / "jobs"
        self.worktrees = self.dir / "worktrees"
        self.sources = [p for p in (DEFAULTS, self.repo / ".factory" / "config.json", self.dir / "config.json")
                        if p.exists()]
        config = {}
        for path in self.sources:
            config = merge(config, _read(path))
        self.config = config
        self.checks = self.repo / config.get("checks", ".factory/checks.sh")


def project_of_job_folder(job_folder):
    """The project a job folder belongs to, from the repo its job.json records."""
    job = _read(Path(job_folder) / "job.json")
    if not job.get("repo"):
        die(f"{job_folder}/job.json doesn't name its repo")
    return Project(job["repo"])

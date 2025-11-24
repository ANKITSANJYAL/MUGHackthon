import os
import logging
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PlannerAgent:
    """Planner that clones/pulls a repo, runs a build/test, and returns a JSON summary."""

    def __init__(self, work_dir: Optional[str] = None):
        self.work_dir = work_dir

    def _ensure_repo(self, repo_url: str, target_dir: str) -> Dict[str, Any]:
        out = {"repo_url": repo_url}
        if os.path.exists(os.path.join(target_dir, ".git")):
            p = subprocess.run(["git", "-C", target_dir, "pull"], capture_output=True, text=True)
            out["pulled"] = p.returncode == 0
            out["stdout"] = p.stdout
            out["stderr"] = p.stderr
            out["returncode"] = p.returncode
        else:
            p = subprocess.run(["git", "clone", repo_url, target_dir], capture_output=True, text=True)
            out["cloned"] = p.returncode == 0
            out["stdout"] = p.stdout
            out["stderr"] = p.stderr
            out["returncode"] = p.returncode
        return out

    def _run_build(self, target_dir: str, build_cmd: Optional[list]) -> Dict[str, Any]:
        out = {}
        if not build_cmd:
            out["skipped"] = True
            return out
        try:
            p = subprocess.run(build_cmd, cwd=target_dir, capture_output=True, text=True, timeout=900)
            out["returncode"] = p.returncode
            out["stdout"] = p.stdout
            out["stderr"] = p.stderr
        except Exception as e:
            out["error"] = str(e)
        return out

    def process_issue(self, issue_key: str, repo_url: Optional[str] = None, build_cmd: Optional[list] = None, dry_run: bool = True) -> Dict[str, Any]:
        """Main entry: clones/pulls repo, runs build command, and returns summary JSON."""
        repo_url = repo_url or os.getenv("REPO_URL")
        if not repo_url:
            return {"error": "No repo_url provided and REPO_URL not set"}

        cleanup = False
        if self.work_dir:
            target_dir = os.path.abspath(self.work_dir)
            os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = tempfile.mkdtemp(prefix="jiae_repo_")
            cleanup = True

        summary: Dict[str, Any] = {"issue_key": issue_key, "repo_url": repo_url, "dry_run": dry_run}

        try:
            summary["git"] = self._ensure_repo(repo_url, target_dir)
            if dry_run:
                summary["build"] = {"skipped": True, "note": "dry_run mode - not executing build"}
            else:
                summary["build"] = self._run_build(target_dir, build_cmd)
            return summary
        finally:
            if cleanup and os.path.exists(target_dir):
                try:
                    shutil.rmtree(target_dir)
                except Exception:
                    logger.exception("Failed to cleanup temp repo dir %s", target_dir)

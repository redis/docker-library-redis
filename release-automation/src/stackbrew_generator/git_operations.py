"""Git operations for stackbrew library generation."""

import re
import subprocess
from typing import Dict, List, Tuple

from rich.console import Console

from .exceptions import GitOperationError
from .models import RedisVersion

console = Console(stderr=True)


class GitClient:
    """Client for Git operations."""

    def __init__(self, remote: str = "origin"):
        """Initialize Git client.

        Args:
            remote: Git remote name to use
        """
        self.remote = remote

    def _run_command(self, cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a git command with error handling.

        Args:
            cmd: Command and arguments to run
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess result

        Raises:
            GitOperationError: If command fails
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            error_msg = f"Git command failed: {' '.join(cmd)}"
            if e.stderr:
                error_msg += f"\nError: {e.stderr.strip()}"
            raise GitOperationError(error_msg) from e
        except FileNotFoundError as e:
            raise GitOperationError("Git command not found. Is git installed?") from e

    def list_remote_tags(self, major_version: int) -> List[Tuple[str, str]]:
        """List remote tags for a specific major version.

        Args:
            major_version: Major version to filter tags for

        Returns:
            List of (commit, tag_ref) tuples

        Raises:
            GitOperationError: If no tags found or git operation fails
        """
        console.print(f"[dim]Listing remote tags for v{major_version}.*[/dim]")

        cmd = [
            "git", "ls-remote", "--tags",
            self.remote, f"refs/tags/v{major_version}.*"
        ]

        result = self._run_command(cmd)

        if not result.stdout.strip():
            raise GitOperationError(f"No tags found for major version {major_version}")

        tag_commits = {}

        # always use peeled commits for annotated tags
        # for annotated tags git ls-remote prints tag object hash, then actual commit hash with ^{} suffix
        # https://stackoverflow.com/a/25996877
        for line in result.stdout.strip().split('\n'):
            if line:
                commit, ref = line.split('\t', 1)
                if ref.endswith('^{}'):
                    # This is a peeled ref - extract the tag name
                    # always rewrite tag commits with peeled ref commits
                    tag_name = ref[:-3]  # Remove '^{}'
                    tag_commits[tag_name] = commit
                else:
                    # This is a regular tag
                    # rewrite only if not yet exists
                    if ref not in tag_commits:
                        tag_commits[ref] = commit

        tags = []
        for tag_ref, commit in tag_commits.items():
                tags.append((commit, tag_ref))

        console.print(f"[dim]Found {len(tags)} tags[/dim]")
        return tags

    def fetch_refs(self, refs: List[str]) -> None:
        """Fetch specific refs from remote.

        Args:
            refs: List of refs to fetch

        Raises:
            GitOperationError: If fetch operation fails
        """
        if not refs:
            return

        console.print(f"[dim]Fetching {len(refs)} refs[/dim]")

        # Use git fetch with unshallow to ensure we have full history
        cmd = ["git", "fetch", "--unshallow", self.remote] + refs

        try:
            self._run_command(cmd, capture_output=False)
        except GitOperationError:
            # If --unshallow fails (repo already unshallow), try without it
            cmd = ["git", "fetch", self.remote] + refs
            self._run_command(cmd, capture_output=False)

    def show_file(self, commit: str, file_path: str) -> str:
        """Show file content from a specific commit.

        Args:
            commit: Git commit hash
            file_path: Path to file in repository

        Returns:
            File content as string

        Raises:
            GitOperationError: If file cannot be retrieved
        """
        cmd = ["git", "show", f"{commit}:{file_path}"]

        try:
            result = self._run_command(cmd)
            return result.stdout
        except GitOperationError as e:
            raise GitOperationError(f"Failed to get {file_path} from {commit}: {e}") from e

    def extract_version_from_tag(self, tag_ref: str, major_version: int) -> RedisVersion:
        """Extract Redis version from tag reference.

        Args:
            tag_ref: Git tag reference (e.g., refs/tags/v8.2.1)
            major_version: Expected major version for validation

        Returns:
            Parsed RedisVersion

        Raises:
            GitOperationError: If tag format is invalid
        """
        # Extract version from tag reference
        match = re.search(rf"v{major_version}\.\d+(?:\.\d+)?.*", tag_ref)
        if not match:
            raise GitOperationError(f"Invalid tag format: {tag_ref}")

        version_str = match.group(0)

        try:
            return RedisVersion.parse(version_str)
        except ValueError as e:
            raise GitOperationError(f"Failed to parse version from {tag_ref}: {e}") from e

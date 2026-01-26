"""Version filtering and processing for Redis releases."""

from typing import Dict, List, Tuple

from collections import OrderedDict

from packaging.version import Version
from rich.console import Console

from .git_operations import GitClient
from .models import RedisVersion

console = Console(stderr=True)


class VersionFilter:
    """Filters and processes Redis versions."""

    def __init__(self, git_client: GitClient):
        """Initialize version filter.

        Args:
            git_client: Git client for operations
        """
        self.git_client = git_client

    def get_redis_versions_from_tags(self, major_version: int) -> List[Tuple[RedisVersion, str, str]]:
        """Get Redis versions from git tags.

        Args:
            major_version: Major version to filter for

        Returns:
            List of (RedisVersion, commit, tag_ref) tuples sorted by version (newest first)
        """
        console.print(f"[blue]Getting Redis versions for major version {major_version}[/blue]")

        # Get remote tags
        tags = self.git_client.list_remote_tags(major_version)

        # Parse versions from tags
        versions = []
        for commit, tag_ref in tags:
            try:
                version = self.git_client.extract_version_from_tag(tag_ref, major_version)
                versions.append((version, commit, tag_ref))
            except Exception as e:
                console.print(f"[yellow]Warning: Skipping invalid tag {tag_ref}: {e}[/yellow]")
                continue

        # Sort by version (newest first)
        versions.sort(key=lambda x: x[0].sort_key, reverse=True)

        console.print(f"[dim]Parsed {len(versions)} valid versions[/dim]")
        return versions


    def filter_eol_versions(self, versions: List[Tuple[RedisVersion, str, str]]) -> List[Tuple[RedisVersion, str, str]]:
        """Filter out end-of-life versions.

        Args:
            versions: List of (RedisVersion, commit, tag_ref) tuples

        Returns:
            Filtered list with EOL minor versions removed
        """
        console.print("[blue]Filtering out EOL versions[/blue]")

        # Group versions by minor version
        minor_versions: Dict[str, List[Tuple[RedisVersion, str, str]]] = {}
        for version, commit, tag_ref in versions:
            minor_key = version.mainline_version
            if minor_key not in minor_versions:
                minor_versions[minor_key] = []
            minor_versions[minor_key].append((version, commit, tag_ref))

        # Check each minor version for EOL marker
        filtered_versions = []
        for minor_key, minor_group in minor_versions.items():
            # Check if any version in this minor series is marked as EOL
            has_eol = any(version.is_eol for version, _, _ in minor_group)

            if has_eol:
                console.print(f"[yellow]Skipping minor version {minor_key}.* due to EOL[/yellow]")
            else:
                filtered_versions.extend(minor_group)

        # Sort again after filtering
        filtered_versions.sort(key=lambda x: x[0].sort_key, reverse=True)

        console.print(f"[dim]Kept {len(filtered_versions)} versions after EOL filtering[/dim]")
        return filtered_versions

    def filter_actual_versions(self, versions: List[Tuple[RedisVersion, str, str]]) -> List[Tuple[RedisVersion, str, str]]:
        """Filter to keep only the latest patch version for each minor version and milestone status.

        Args:
            versions: List of (RedisVersion, commit, tag_ref) tuples (should be sorted newest first)

        Returns:
            Filtered list with only the latest versions for each minor/milestone combination
        """
        console.print("[blue]Filtering to actual versions (latest patch per minor/milestone)[/blue]")

        patch_versions = OrderedDict()

        for version, commit, tag_ref in versions:
            patch_key = (version.major, version.minor, version.patch or 0)
            if patch_key not in patch_versions:
                patch_versions[patch_key] = (version, commit, tag_ref)
            elif patch_versions[patch_key][0].is_milestone and not version.is_milestone:
                # GA always takes precedence over milestone for the same major.minor.patch
                patch_versions[patch_key] = (version, commit, tag_ref)

        filtered_versions = []
        mainlines_with_ga = set()

        for version, commit, tag_ref in patch_versions.values():
            if version.mainline_version not in mainlines_with_ga:
                if not version.is_milestone:
                    mainlines_with_ga.add(version.mainline_version)
                filtered_versions.append((version, commit, tag_ref))
        return filtered_versions

    def get_actual_major_redis_versions(self, major_version: int) -> List[Tuple[RedisVersion, str, str]]:
        """Get the actual Redis versions to process for a major version.

        This is the main entry point that combines all filtering steps:
        1. Get versions from git tags
        2. Filter out EOL versions
        3. Filter to actual versions (latest patch per minor/milestone)

        Args:
            major_version: Major version to process

        Returns:
            List of (RedisVersion, commit, tag_ref) tuples for processing
        """
        console.print(f"[bold blue]Processing Redis {major_version}.x versions[/bold blue]")

        # Get all versions from tags
        versions = self.get_redis_versions_from_tags(major_version)

        if not versions:
            console.print(f"[red]No versions found for major version {major_version}[/red]")
            return []

        # Apply filters
        versions = self.filter_eol_versions(versions)
        versions = self.filter_actual_versions(versions)

        console.print(f"[green]Final selection: {len(versions)} versions to process[/green]")
        for version, commit, tag_ref in versions:
            console.print(f"[green]  [bold yellow]{version}[/bold yellow] - {commit[:8]}[/green]")

        return versions

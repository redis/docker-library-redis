"""Stackbrew library generation."""

import re
from pathlib import Path
from typing import List, Optional, Set

from rich.console import Console

from .models import Release, StackbrewEntry

console = Console(stderr=True)


class StackbrewGenerator:
    """Generates stackbrew library content."""

    def generate_tags_for_release(
        self,
        release: Release,
        is_latest_in_major: bool = False,
        is_global_latest_major: bool = False,
        latest_distro_tag_names: Optional[Set[str]] = None,
        bare_distro_tag_names: Optional[Set[str]] = None,
    ) -> List[str]:
        """Generate Docker tags for a release.

        Args:
            release: Release to generate tags for
            is_latest_in_major: Whether this is the latest active minor in its major
            is_global_latest_major: Whether this major is the highest active major overall
            latest_distro_tag_names: Distro tag names whose major aliases belong to
                this release
            bare_distro_tag_names: Bare distro aliases that belong to this release

        Returns:
            List of Docker tags
        """
        tags = []
        version = release.version
        distribution = release.distribution

        # Base version tags
        version_tags = [str(version)]

        # Add mainline version tag only for GA releases (no suffix)
        if not version.is_milestone:
            version_tags.append(version.mainline_version)

        # Keep the global major alias separate from the distro-qualified aliases.
        # This lets an older maintained distro release own (for example)
        # "8-bookworm" without also owning the unqualified "8" tag.
        default_version_tags = version_tags.copy()
        if is_latest_in_major:
            default_version_tags.append(str(version.major))

        # Preserve the direct-call behavior used by existing callers and tests:
        # a release that is globally latest owns all of its distro major aliases.
        if latest_distro_tag_names is None:
            latest_distro_tag_names = (
                set(distribution.tag_names) if is_latest_in_major else set()
            )
        if bare_distro_tag_names is None:
            bare_distro_tag_names = (
                set(distribution.tag_names) if is_global_latest_major else set()
            )

        # For default distribution (Debian), add version tags without distro suffix
        if distribution.is_default:
            tags.extend(default_version_tags)

        # Add distro-specific tags
        for distro_name in distribution.tag_names:
            distro_version_tags = version_tags.copy()
            if distro_name in latest_distro_tag_names:
                distro_version_tags.append(str(version.major))

            for version_tag in distro_version_tags:
                tags.append(f"{version_tag}-{distro_name}")

        # The global "latest" alias remains on the newest default image only.
        if is_global_latest_major and distribution.is_default:
            tags.append("latest")

        # Bare distro aliases belong to the newest release supporting each distro.
        tags.extend(
            distro_name
            for distro_name in distribution.tag_names
            if distro_name in bare_distro_tag_names
        )

        return tags

    def generate_stackbrew_library(
        self,
        releases: List[Release],
        enable_global_latest_tags: bool = True,
    ) -> List[StackbrewEntry]:
        """Generate stackbrew library entries from releases.

        Args:
            releases: List of releases to process
            enable_global_latest_tags: Whether to emit latest/bare distro tags

        Returns:
            List of StackbrewEntry objects
        """
        console.print("[blue]Generating stackbrew library content[/blue]")

        if not releases:
            console.print("[yellow]No releases to process[/yellow]")
            return []

        entries = []
        latest_minor = None
        latest_minor_unset = True
        seen_distro_tag_names: Set[str] = set()

        for release in releases:
            # Determine latest version following bash logic:
            # - Set latest_minor to the minor version of the first non-milestone version
            # - Clear latest_minor if subsequent versions have different minor versions
            if latest_minor_unset:
                if not release.version.is_milestone:
                    latest_minor = release.version.minor
                    latest_minor_unset = False
                    console.print(f"[dim]Latest minor version set to: {latest_minor}[/dim]")
            elif latest_minor != release.version.minor:
                latest_minor = None

            # Major tag like "7" still belongs to the latest active minor within the major.
            is_latest_in_major = latest_minor is not None
            # Global tags like "latest" or bare distro names should only be emitted
            # for the highest overall major version.
            is_global_latest_major = enable_global_latest_tags and is_latest_in_major

            # Distro aliases belong to the first GA release that supports each
            # distro name. Releases are ordered newest first, so older maintained
            # distros retain their aliases without taking global aliases such as
            # the unqualified major or "latest" from the newest release.
            latest_distro_tag_names = set()
            bare_distro_tag_names = set()
            if not release.version.is_milestone:
                for distro_name in release.distribution.tag_names:
                    if distro_name not in seen_distro_tag_names:
                        latest_distro_tag_names.add(distro_name)
                        if enable_global_latest_tags:
                            bare_distro_tag_names.add(distro_name)
                        seen_distro_tag_names.add(distro_name)

            # Generate tags for this release
            tags = self.generate_tags_for_release(
                release,
                is_latest_in_major=is_latest_in_major,
                is_global_latest_major=is_global_latest_major,
                latest_distro_tag_names=latest_distro_tag_names,
                bare_distro_tag_names=bare_distro_tag_names,
            )

            if tags:
                entry = StackbrewEntry(
                    tags=tags,
                    commit=release.commit,
                    version=release.version,
                    distribution=release.distribution,
                    git_fetch_ref=release.git_fetch_ref
                )
                entries.append(entry)

                console.print(f"[dim]{release.console_repr()} -> {len(tags)} tags[/dim]")
            else:
                console.print(f"[yellow]No tags generated for {release}[/yellow]")

        console.print(f"[green]Generated {len(entries)} stackbrew entries[/green]")
        console.print(f"[dim]{self.format_stackbrew_output(entries)}[/dim]")
        return entries

    def format_stackbrew_output(self, entries: List[StackbrewEntry]) -> str:
        """Format stackbrew entries as output string.

        Args:
            entries: List of stackbrew entries

        Returns:
            Formatted stackbrew library content
        """
        if not entries:
            return ""

        lines = []
        for i, entry in enumerate(entries):
            if i > 0:
                lines.append("")  # Add blank line between entries
            lines.append(str(entry))

        return "\n".join(lines)


class StackbrewUpdater:
    """Updates stackbrew library files by replacing entries for specific major versions."""

    def __init__(self):
        """Initialize the updater."""
        pass

    def update_stackbrew_content(self, input_file: Path, major_version: int, new_content: str, verbose: bool = False) -> str:
        """Update stackbrew file content by replacing entries for a specific major version.

        Args:
            input_file: Path to the input stackbrew file
            major_version: Major version to replace entries for
            new_content: New stackbrew content to insert
            verbose: Whether to print verbose output

        Returns:
            Updated stackbrew file content
        """
        content = input_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Find header (everything before the first Tags: line)
        header_lines = []
        content_start_idx = 0

        for i, line in enumerate(lines):
            if line.startswith('Tags:'):
                content_start_idx = i
                break
            header_lines.append(line)

        if content_start_idx == 0 and not any(line.startswith('Tags:') for line in lines):
            # No existing entries, just append new content
            if verbose:
                console.print("[dim]No existing entries found, appending new content[/dim]")
            return content.rstrip() + '\n\n' + new_content

        # Parse entries and find where target major version entries start and end
        entries = self._parse_stackbrew_entries(lines[content_start_idx:])
        target_entries = []
        other_entries_before = []
        other_entries_after = []
        target_start_found = False
        target_end_found = False
        removed_count = 0

        for entry in entries:
            if self._entry_belongs_to_major_version(entry, major_version):
                target_entries.append(entry)
                removed_count += 1
                if not target_start_found:
                    target_start_found = True
            elif not target_start_found:
                # Entries before target major version
                other_entries_before.append(entry)
            else:
                # Entries after target major version
                other_entries_after.append(entry)
                if not target_end_found:
                    target_end_found = True

        if verbose:
            if removed_count > 0:
                console.print(f"[dim]Removed {removed_count} existing entries for Redis {major_version}.x[/dim]")
            else:
                console.print(f"[dim]No existing entries found for Redis {major_version}.x, placing at end[/dim]")

        # Reconstruct the file
        result_lines = header_lines[:]

        # Add entries before target major version
        for entry in other_entries_before:
            if result_lines and result_lines[-1].strip():  # Add blank line if needed
                result_lines.append('')
            result_lines.extend(entry)

        # Add new content for the target major version
        if result_lines and result_lines[-1].strip():  # Add blank line if needed
            result_lines.append('')
        result_lines.extend(new_content.split('\n'))

        # Add entries after target major version
        for entry in other_entries_after:
            if result_lines and result_lines[-1].strip():  # Add blank line if needed
                result_lines.append('')
            result_lines.extend(entry)

        return '\n'.join(result_lines)

    def _parse_stackbrew_entries(self, lines: List[str]) -> List[List[str]]:
        """Parse stackbrew entries from lines, returning list of entry line groups.

        Args:
            lines: Lines to parse

        Returns:
            List of entry line groups
        """
        entries = []
        current_entry = []

        for line in lines:
            line = line.rstrip()

            if line.startswith('Tags:') and current_entry:
                # Start of new entry, save the previous one
                entries.append(current_entry)
                current_entry = [line]
            elif line.startswith('Tags:'):
                # First entry
                current_entry = [line]
            elif current_entry and (line.startswith(('Architectures:', 'GitCommit:', 'GitFetch:', 'Directory:')) or line.strip() == ''):
                # Part of current entry
                current_entry.append(line)
            elif not line.strip() and not current_entry:
                # Empty line before any entry starts, skip
                continue
            elif not line.strip() and current_entry:
                # Empty line after entry content - end of entry
                if current_entry:
                    entries.append(current_entry)
                    current_entry = []

        # Don't forget the last entry
        if current_entry:
            entries.append(current_entry)

        return entries

    def _entry_belongs_to_major_version(self, entry_lines: List[str], major_version: int) -> bool:
        """Check if a stackbrew entry belongs to the specified major version.

        Args:
            entry_lines: Lines of the stackbrew entry
            major_version: Major version to check for

        Returns:
            True if the entry belongs to the major version
        """
        for line in entry_lines:
            if line.startswith('Tags:'):
                tags_line = line[5:].strip()  # Remove 'Tags:' prefix
                tags = [tag.strip() for tag in tags_line.split(',')]

                # Check if any tag indicates this major version
                for tag in tags:
                    # Look for patterns like "8", "8.2", "8.2.1", "8-alpine", etc.
                    if re.match(rf'^{major_version}(?:\.|$|-)', tag):
                        return True
                    # Also check for "latest" tag which typically belongs to the highest major version
                    # But we'll be conservative and not assume latest belongs to our major version
                    # unless we have other evidence
                break

        return False

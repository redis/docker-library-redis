"""Stackbrew library generation."""

import re
from pathlib import Path
from typing import List

from rich.console import Console

from .models import Release, StackbrewEntry

console = Console(stderr=True)


class StackbrewGenerator:
    """Generates stackbrew library content."""

    def generate_tags_for_release(
        self,
        release: Release,
        is_latest: bool = False
    ) -> List[str]:
        """Generate Docker tags for a release.

        Args:
            release: Release to generate tags for
            is_latest: Whether this is the latest version

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

        # Add major version tag for latest versions
        if is_latest:
            version_tags.append(str(version.major))

        # For default distribution (Debian), add version tags without distro suffix
        if distribution.is_default:
            tags.extend(version_tags)

        # Add distro-specific tags
        for distro_name in distribution.tag_names:
            for version_tag in version_tags:
                tags.append(f"{version_tag}-{distro_name}")

        # Add special latest tags
        if is_latest:
            if distribution.is_default:
                tags.append("latest")
            # Add bare distro names as tags
            tags.extend(distribution.tag_names)

        return tags

    def generate_stackbrew_library(self, releases: List[Release]) -> List[StackbrewEntry]:
        """Generate stackbrew library entries from releases.

        Args:
            releases: List of releases to process

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

            # Check if this release should get latest tags
            is_latest = latest_minor is not None

            # Generate tags for this release
            tags = self.generate_tags_for_release(release, is_latest)

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

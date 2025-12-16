"""Tests for StackbrewUpdater class."""

import tempfile
from pathlib import Path

from stackbrew_generator.stackbrew import StackbrewUpdater

class TestStackbrewUpdater:
    """Tests for StackbrewUpdater class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.updater = StackbrewUpdater()

    def test_update_stackbrew_content_basic(self):
        """Test basic stackbrew content update functionality."""
        # Create a sample stackbrew file
        sample_content = """# This file was generated via https://github.com/redis/docker-library-redis/blob/abc123/generate-stackbrew-library.sh

Maintainers: David Maier <david.maier@redis.com> (@dmaier-redislabs),
             Yossi Gottlieb <yossi@redis.com> (@yossigo)
GitRepo: https://github.com/redis/docker-library-redis.git

Tags: 8.2.1, 8.2, 8, 8.2.1-bookworm, 8.2-bookworm, 8-bookworm, latest, bookworm
Architectures: amd64, arm32v5, arm32v7, arm64v8, i386, mips64le, ppc64le, s390x
GitCommit: old123commit
GitFetch: refs/tags/v8.2.1
Directory: debian

Tags: 8.2.1-alpine, 8.2-alpine, 8-alpine, 8.2.1-alpine3.22, 8.2-alpine3.22, 8-alpine3.22, alpine, alpine3.22
Architectures: amd64, arm32v6, arm32v7, arm64v8, i386, ppc64le, riscv64, s390x
GitCommit: old123commit
GitFetch: refs/tags/v8.2.1
Directory: alpine

Tags: 7.4.0, 7.4, 7, 7.4.0-bookworm, 7.4-bookworm, 7-bookworm
Architectures: amd64, arm32v5, arm32v7, arm64v8, i386, mips64le, ppc64le, s390x
GitCommit: old456commit
GitFetch: refs/tags/v7.4.0
Directory: debian
"""

        new_content = """Tags: 8.2.2, 8.2, 8, 8.2.2-bookworm, 8.2-bookworm, 8-bookworm, latest, bookworm
Architectures: amd64, arm32v5, arm32v7, arm64v8, i386, mips64le, ppc64le, s390x
GitCommit: new123commit
GitFetch: refs/tags/v8.2.2
Directory: debian

Tags: 8.2.2-alpine, 8.2-alpine, 8-alpine, 8.2.2-alpine3.22, 8.2-alpine3.22, 8-alpine3.22, alpine, alpine3.22
Architectures: amd64, arm32v6, arm32v7, arm64v8, i386, ppc64le, riscv64, s390x
GitCommit: new123commit
GitFetch: refs/tags/v8.2.2
Directory: alpine"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_content)
            input_file = Path(f.name)

        try:
            # Update the content
            updated_content = self.updater.update_stackbrew_content(
                input_file, 8, new_content, verbose=False
            )

            # Should still have the header
            assert "Maintainers: David Maier" in updated_content
            assert "GitRepo: https://github.com/redis/docker-library-redis.git" in updated_content

            # Should have new Redis 8.x content
            assert "new123commit" in updated_content
            assert "8.2.2" in updated_content

            # Should still have Redis 7.x content (unchanged)
            assert "7.4.0" in updated_content
            assert "old456commit" in updated_content

            # Should not have old Redis 8.x content
            assert "old123commit" not in updated_content
            assert "8.2.1" not in updated_content

        finally:
            input_file.unlink()

    def test_parse_stackbrew_entries(self):
        """Test parsing stackbrew entries."""
        lines = [
            "Tags: 8.2.1, 8.2, 8",
            "Architectures: amd64, arm64v8",
            "GitCommit: abc123",
            "Directory: debian",
            "",
            "Tags: 8.2.1-alpine, 8.2-alpine",
            "Architectures: amd64, arm64v8",
            "GitCommit: abc123",
            "Directory: alpine"
        ]

        entries = self.updater._parse_stackbrew_entries(lines)

        assert len(entries) == 2
        assert entries[0][0] == "Tags: 8.2.1, 8.2, 8"
        assert entries[1][0] == "Tags: 8.2.1-alpine, 8.2-alpine"

    def test_entry_belongs_to_major_version(self):
        """Test checking if entry belongs to major version."""
        entry_8x = [
            "Tags: 8.2.1, 8.2, 8, latest",
            "Architectures: amd64",
            "GitCommit: abc123",
            "Directory: debian"
        ]

        entry_7x = [
            "Tags: 7.4.0, 7.4, 7",
            "Architectures: amd64",
            "GitCommit: def456",
            "Directory: debian"
        ]

        assert self.updater._entry_belongs_to_major_version(entry_8x, 8) is True
        assert self.updater._entry_belongs_to_major_version(entry_8x, 7) is False
        assert self.updater._entry_belongs_to_major_version(entry_7x, 7) is True
        assert self.updater._entry_belongs_to_major_version(entry_7x, 8) is False

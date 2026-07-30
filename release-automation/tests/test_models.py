"""Tests for data models."""

import pytest

from stackbrew_generator.models import (
    ALPINE_ARCHITECTURES,
    DEBIAN_BOOKWORM_ARCHITECTURES,
    DEBIAN_TRIXIE_ARCHITECTURES,
    DebianRelease,
    Distribution,
    DistroType,
    RedisVersion,
    Release,
    StackbrewEntry,
    get_architectures_for_distribution,
)


class TestDistribution:
    """Tests for Distribution model."""

    def test_from_dockerfile_alpine(self):
        """Test parsing Alpine distribution from Dockerfile."""
        distro = Distribution.from_dockerfile_line("FROM alpine:3.22")
        assert distro.type == DistroType.ALPINE
        assert distro.name == "alpine3.22"

    def test_from_dockerfile_debian(self):
        """Test parsing Debian distribution from Dockerfile."""
        distro = Distribution.from_dockerfile_line("FROM debian:bookworm")
        assert distro.type == DistroType.DEBIAN
        assert distro.name == "bookworm"

    def test_from_dockerfile_debian_slim(self):
        """Test parsing Debian slim distribution from Dockerfile."""
        distro = Distribution.from_dockerfile_line("FROM debian:bookworm-slim")
        assert distro.type == DistroType.DEBIAN
        assert distro.name == "bookworm"

    def test_from_dockerfile_invalid(self):
        """Test parsing invalid Dockerfile lines."""
        with pytest.raises(ValueError):
            Distribution.from_dockerfile_line("INVALID LINE")

        with pytest.raises(ValueError):
            Distribution.from_dockerfile_line("FROM unsupported:latest")

    def test_is_default(self):
        """Test default distribution detection."""
        alpine = Distribution(type=DistroType.ALPINE, name="alpine3.22")
        debian = Distribution(type=DistroType.DEBIAN, name="bookworm")

        assert alpine.is_default is False
        assert debian.is_default is True

    def test_tag_names(self):
        """Test tag name generation."""
        alpine = Distribution(type=DistroType.ALPINE, name="alpine3.22")
        debian = Distribution(type=DistroType.DEBIAN, name="bookworm")

        assert alpine.tag_names == ["alpine", "alpine3.22"]
        assert debian.tag_names == ["bookworm"]


class TestRelease:
    """Tests for Release model."""

    def test_release_creation(self):
        """Test creating a Release instance."""
        version = RedisVersion.parse("8.2.1")
        distribution = Distribution(type=DistroType.DEBIAN, name="bookworm")

        release = Release(
            commit="abc123def456",
            version=version,
            distribution=distribution,
            git_fetch_ref="refs/tags/v8.2.1",
        )

        assert release.commit == "abc123def456"
        assert release.version == version
        assert release.distribution == distribution

    def test_release_string_representation(self):
        """Test Release string representation."""
        version = RedisVersion.parse("8.2.1")
        distribution = Distribution(type=DistroType.DEBIAN, name="bookworm")

        release = Release(
            commit="abc123def456",
            version=version,
            distribution=distribution,
            git_fetch_ref="refs/tags/v8.2.1",
        )

        expected = "abc123de 8.2.1 debian bookworm"
        assert str(release) == expected


class TestStackbrewEntry:
    """Tests for StackbrewEntry model."""

    def test_get_architectures_for_distribution_raises_for_unknown_distribution(self):
        """Test failing fast for unsupported distribution types."""
        unknown_distribution = Distribution.model_construct(
            type="unsupported", name="mystery"
        )

        with pytest.raises(
            ValueError, match="Unsupported distribution type: unsupported"
        ):
            get_architectures_for_distribution(unknown_distribution)

    def test_debian_trixie_architectures(self):
        """Test that Debian trixie gets riscv64 architecture (no mips64le)."""
        version = RedisVersion.parse("8.4.0")
        distribution = Distribution(type=DistroType.DEBIAN, name=DebianRelease.TRIXIE)

        entry = StackbrewEntry(
            tags=["8.4.0", "latest"],
            commit="abc123def456",
            version=version,
            distribution=distribution,
            git_fetch_ref="refs/tags/v8.4.0",
        )

        assert entry.architectures == list(DEBIAN_TRIXIE_ARCHITECTURES)
        assert "riscv64" in entry.architectures
        assert "mips64le" not in entry.architectures

    def test_debian_bookworm_architectures(self):
        """Test that Debian bookworm gets mips64le architecture (no riscv64)."""
        version = RedisVersion.parse("8.2.1")
        distribution = Distribution(type=DistroType.DEBIAN, name=DebianRelease.BOOKWORM)

        entry = StackbrewEntry(
            tags=["8.2.1", "latest"],
            commit="abc123def456",
            version=version,
            distribution=distribution,
            git_fetch_ref="refs/tags/v8.2.1",
        )

        assert entry.architectures == list(DEBIAN_BOOKWORM_ARCHITECTURES)
        assert "mips64le" in entry.architectures
        assert "riscv64" not in entry.architectures

    def test_alpine_architectures(self):
        """Test that Alpine distributions get the correct architectures."""
        version = RedisVersion.parse("8.2.1")
        distribution = Distribution(type=DistroType.ALPINE, name="alpine3.22")

        entry = StackbrewEntry(
            tags=["8.2.1-alpine", "alpine"],
            commit="abc123def456",
            version=version,
            distribution=distribution,
            git_fetch_ref="refs/tags/v8.2.1",
        )

        assert entry.architectures == list(ALPINE_ARCHITECTURES)

    def test_stackbrew_entry_string_format(self):
        """Test that StackbrewEntry formats correctly with architectures."""
        version = RedisVersion.parse("8.2.1")
        distribution = Distribution(type=DistroType.ALPINE, name="alpine3.22")

        entry = StackbrewEntry(
            tags=["8.2.1-alpine", "alpine"],
            commit="abc123def456",
            version=version,
            distribution=distribution,
            git_fetch_ref="refs/tags/v8.2.1",
        )

        output = str(entry)

        # Check that it contains the expected Alpine architectures
        assert ", ".join(ALPINE_ARCHITECTURES) in output
        assert "Tags: 8.2.1-alpine, alpine" in output
        assert "GitCommit: abc123def456" in output
        assert "GitFetch: refs/tags/v8.2.1" in output
        assert "Directory: alpine" in output

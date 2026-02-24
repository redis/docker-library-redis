"""Tests for generate-image-tags CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from stackbrew_generator.cli import app
from stackbrew_generator.models import (
    Distribution,
    DistroType,
    RedisVersion,
    StackbrewEntry,
)

runner = CliRunner()

GA_ENTRIES = [
    StackbrewEntry(
        tags=["8.6.0", "8.6", "8", "8.6.0-trixie", "8.6-trixie", "8-trixie", "latest", "trixie"],
        commit="abc123",
        version=RedisVersion(major=8, minor=6, patch=0),
        distribution=Distribution(type=DistroType.DEBIAN, name="trixie"),
        git_fetch_ref="refs/tags/v8.6.0",
    ),
    StackbrewEntry(
        tags=["8.6.0-alpine", "8.6-alpine", "8-alpine", "8.6.0-alpine3.23", "8.6-alpine3.23", "8-alpine3.23", "alpine", "alpine3.23"],
        commit="abc123",
        version=RedisVersion(major=8, minor=6, patch=0),
        distribution=Distribution(type=DistroType.ALPINE, name="alpine3.23"),
        git_fetch_ref="refs/tags/v8.6.0",
    ),
]

RC_ENTRIES = [
    StackbrewEntry(
        tags=["8.6.0-rc1", "8.6.0-rc1-trixie"],
        commit="def456",
        version=RedisVersion(major=8, minor=6, patch=0, suffix="-rc1"),
        distribution=Distribution(type=DistroType.DEBIAN, name="trixie"),
        git_fetch_ref="refs/tags/v8.6.0-rc1",
    ),
    StackbrewEntry(
        tags=["8.6.0-rc1-alpine", "8.6.0-rc1-alpine3.23"],
        commit="def456",
        version=RedisVersion(major=8, minor=6, patch=0, suffix="-rc1"),
        distribution=Distribution(type=DistroType.ALPINE, name="alpine3.23"),
        git_fetch_ref="refs/tags/v8.6.0-rc1",
    ),
]

MOCK_VERSIONS = [("v8.6.0", "abc123", "refs/tags/v8.6.0")]


def _patch_pipeline(entries):
    """Patch the stackbrew pipeline components to return given entries."""
    return [
        patch("stackbrew_generator.cli.GitClient"),
        patch("stackbrew_generator.cli.VersionFilter", return_value=MagicMock(
            get_actual_major_redis_versions=MagicMock(return_value=MOCK_VERSIONS)
        )),
        patch("stackbrew_generator.cli.DistributionDetector"),
        patch("stackbrew_generator.cli.StackbrewGenerator", return_value=MagicMock(
            generate_stackbrew_library=MagicMock(return_value=entries)
        )),
    ]


class TestGenerateImageTags:
    """Tests for the generate-image-tags command."""

    def test_debian_ga_latest(self):
        """Debian GA version that is latest gets full tags including 'latest'."""
        patches = _patch_pipeline(GA_ENTRIES)
        for p in patches:
            p.start()
        try:
            result = runner.invoke(app, ["generate-image-tags", "8.6.0", "debian"])
            assert result.exit_code == 0
            tags = [t.strip() for t in result.stdout.strip().split(",")]
            assert "8.6.0" in tags
            assert "8.6" in tags
            assert "8" in tags
            assert "latest" in tags
            distro_tags = [t for t in tags if "trixie" in t]
            assert len(distro_tags) > 0
        finally:
            for p in patches:
                p.stop()

    def test_alpine_ga_latest(self):
        """Alpine GA version that is latest gets alpine-prefixed tags."""
        patches = _patch_pipeline(GA_ENTRIES)
        for p in patches:
            p.start()
        try:
            result = runner.invoke(app, ["generate-image-tags", "8.6.0", "alpine"])
            assert result.exit_code == 0
            tags = [t.strip() for t in result.stdout.strip().split(",")]
            assert "8.6.0" not in tags
            assert "latest" not in tags
            assert "alpine" in tags
            alpine_version_tags = [t for t in tags if t.startswith("8.6.0-alpine")]
            assert len(alpine_version_tags) > 0
        finally:
            for p in patches:
                p.stop()

    def test_milestone_version(self):
        """Milestone version should not get mainline or major tags."""
        patches = _patch_pipeline(RC_ENTRIES)
        for p in patches:
            p.start()
        try:
            result = runner.invoke(app, ["generate-image-tags", "8.6.0-rc1", "debian"])
            assert result.exit_code == 0
            tags = [t.strip() for t in result.stdout.strip().split(",")]
            assert "8.6.0-rc1" in tags
            assert "8.6" not in tags
            assert "8" not in tags
        finally:
            for p in patches:
                p.stop()

    def test_invalid_version(self):
        """Invalid version exits with error."""
        result = runner.invoke(app, ["generate-image-tags", "invalid", "debian"])
        assert result.exit_code == 1

    def test_version_not_found(self):
        """Version that doesn't match any entry returns empty output."""
        patches = _patch_pipeline(GA_ENTRIES)
        for p in patches:
            p.start()
        try:
            result = runner.invoke(app, ["generate-image-tags", "8.6.0", "nonexistent"])
            assert result.exit_code == 0
            assert result.stdout.strip() == ""
        finally:
            for p in patches:
                p.stop()

    def test_no_versions_found(self):
        """No versions found for major version exits with error."""
        with patch("stackbrew_generator.cli.GitClient"), \
             patch("stackbrew_generator.cli.VersionFilter", return_value=MagicMock(
                 get_actual_major_redis_versions=MagicMock(return_value=[])
             )), \
             patch("stackbrew_generator.cli.DistributionDetector"), \
             patch("stackbrew_generator.cli.StackbrewGenerator"):
            result = runner.invoke(app, ["generate-image-tags", "9.0.0", "debian"])
            assert result.exit_code == 1

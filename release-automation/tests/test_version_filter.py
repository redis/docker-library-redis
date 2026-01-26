"""Tests for VersionFilter class."""

import pytest
from unittest.mock import Mock, patch

from stackbrew_generator.models import RedisVersion
from stackbrew_generator.version_filter import VersionFilter
from stackbrew_generator.git_operations import GitClient
from stackbrew_generator.exceptions import GitOperationError


class MockGitClient:
    """Mock GitClient for testing."""

    def __init__(self):
        """Initialize mock git client."""
        self.remote_tags = []
        self.version_extraction_results = {}

    def set_remote_tags(self, tags):
        """Set mock remote tags.

        Args:
            tags: List of (commit, tag_ref) tuples
        """
        self.remote_tags = tags

    def set_version_extraction_result(self, tag_ref, version_or_exception):
        """Set mock version extraction result.

        Args:
            tag_ref: Tag reference
            version_or_exception: RedisVersion instance or Exception to raise
        """
        self.version_extraction_results[tag_ref] = version_or_exception

    def list_remote_tags(self, major_version):
        """Mock list_remote_tags method."""
        return self.remote_tags

    def extract_version_from_tag(self, tag_ref, major_version):
        """Mock extract_version_from_tag method."""
        if tag_ref in self.version_extraction_results:
            result = self.version_extraction_results[tag_ref]
            if isinstance(result, Exception):
                raise result
            return result
        # Default behavior - try to parse from tag_ref
        return RedisVersion.parse(tag_ref.replace('refs/tags/', ''))


def create_version_tuples(version_strings):
    """Helper to create version tuples from version strings.

    Args:
        version_strings: List of version strings

    Returns:
        List of (RedisVersion, commit, tag_ref) tuples
    """
    tuples = []
    for i, version_str in enumerate(version_strings):
        version = RedisVersion.parse(version_str)
        commit = f"commit{i:03d}"
        tag_ref = f"refs/tags/{version_str}"
        tuples.append((version, commit, tag_ref))

    tuples.sort(key=lambda x: x[0].sort_key, reverse=True)
    return tuples


class TestVersionFilter:
    """Tests for VersionFilter class."""

    def test_init(self):
        """Test VersionFilter initialization."""
        git_client = GitClient()
        version_filter = VersionFilter(git_client)
        assert version_filter.git_client is git_client

    def test_get_redis_versions_from_tags_success(self):
        """Test successful version retrieval from tags."""
        mock_git_client = MockGitClient()
        mock_git_client.set_remote_tags([
            ("commit001", "refs/tags/v8.2.1"),
            ("commit002", "refs/tags/v8.2.0"),
            ("commit003", "refs/tags/v8.1.0"),
        ])

        version_filter = VersionFilter(mock_git_client)
        result = version_filter.get_redis_versions_from_tags(8)

        # Should be sorted by version (newest first)
        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.2.1", "8.2.0", "8.1.0"]
        assert version_strings == expected_versions

        # Check commits and tag refs
        commits = [v[1] for v in result]
        tag_refs = [v[2] for v in result]
        expected_commits = ["commit001", "commit002", "commit003"]
        expected_tag_refs = ["refs/tags/v8.2.1", "refs/tags/v8.2.0", "refs/tags/v8.1.0"]
        assert commits == expected_commits
        assert tag_refs == expected_tag_refs

    def test_get_redis_versions_from_tags_with_invalid_tags(self):
        """Test version retrieval with some invalid tags."""
        mock_git_client = MockGitClient()
        mock_git_client.set_remote_tags([
            ("commit001", "refs/tags/v8.2.1"),
            ("commit002", "refs/tags/invalid-tag"),
            ("commit003", "refs/tags/v8.1.0"),
        ])

        # Set up invalid tag to raise exception
        mock_git_client.set_version_extraction_result(
            "refs/tags/invalid-tag",
            ValueError("Invalid version format")
        )

        version_filter = VersionFilter(mock_git_client)
        result = version_filter.get_redis_versions_from_tags(8)

        # Should skip invalid tag and return only valid ones
        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.2.1", "8.1.0"]
        assert version_strings == expected_versions

    def test_get_redis_versions_from_tags_empty(self):
        """Test version retrieval with no tags."""
        mock_git_client = MockGitClient()
        mock_git_client.set_remote_tags([])

        version_filter = VersionFilter(mock_git_client)
        result = version_filter.get_redis_versions_from_tags(8)

        assert result == []

    def test_filter_eol_versions_basic(self):
        """Test basic EOL version filtering."""
        version_filter = VersionFilter(MockGitClient())

        # Create test versions with one EOL minor version
        versions = create_version_tuples([
            "v8.2.1",
            "v8.2.0",
            "v8.1.0-eol",
            "v8.1.0-zoo1",
            "v8.1.2",
            "v8.0.1",
            "v8.0.0"
        ])

        result = version_filter.filter_eol_versions(versions)

        # Should filter out all 8.1.* versions (because 8.1.0-eol exists)
        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.2.1", "8.2.0", "8.0.1", "8.0.0"]
        assert version_strings == expected_versions

    def test_filter_eol_versions_empty(self):
        """Test EOL filtering with empty input."""
        version_filter = VersionFilter(MockGitClient())
        result = version_filter.filter_eol_versions([])
        assert result == []

    def test_filter_actual_versions_basic(self):
        """Test basic actual version filtering (latest patch per minor/milestone)."""
        version_filter = VersionFilter(MockGitClient())

        # Create versions with multiple patches for same minor version
        versions = create_version_tuples([
            "v8.2.2",      # Latest patch for 8.2 GA
            "v8.2.1",      # Older patch for 8.2 GA
            "v8.2.0",      # Oldest patch for 8.2 GA
            "v8.1.1",      # Latest patch for 8.1 GA
            "v8.1.0",      # Older patch for 8.1 GA
        ])

        result = version_filter.filter_actual_versions(versions)

        # Should keep only latest patch for each minor version
        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.2.2", "8.1.1"]
        assert version_strings == expected_versions

    def test_filter_actual_versions_with_milestones_in_same_patch(self):
        """Test actual version filtering with milestone versions."""
        version_filter = VersionFilter(MockGitClient())

        # Create versions with both GA and milestone versions
        versions = create_version_tuples([
            "v8.2.1",      # GA version
            "v8.2.1-m02",  # Latest milestone for 8.2
            "v8.2.1-m01",  # Older milestone for 8.2
            "v8.1.0",      # GA version
            "v8.1.0-m01",  # Milestone for 8.1
        ])

        result = version_filter.filter_actual_versions(versions)

        # Should keep latest GA and latest milestone for each minor version
        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.2.1", "8.1.0"]
        assert version_strings == expected_versions

    def test_filter_actual_versions_with_milestones_in_mainline(self):
        """Test actual version filtering with milestone versions."""
        version_filter = VersionFilter(MockGitClient())

        # Create versions with both GA and milestone versions
        versions = create_version_tuples([
            "v8.2.1",      # GA version for 8.2 mainline
            "v8.2.2-m02",  # Latest milestone for 8.2.2
            "v8.2.2-m01",  # Older milestone for 8.2.2
            "v8.1.0",      # GA version
            "v8.1.1-m01",  # Milestone for 8.1
            "v8.2.0-m03",  # Older milestone for 8.2.0
        ])

        result = version_filter.filter_actual_versions(versions)

        # Should keep latest GA and latest milestone for each minor version
        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.2.2-m02", "8.2.1", "8.1.1-m01", "8.1.0"]
        assert version_strings == expected_versions

    def test_when_filter_actual_versions_with_milestones_rc_is_preferred(self):
        """Test actual version filtering with milestone versions."""
        version_filter = VersionFilter(MockGitClient())

        # Create versions with both GA and milestone versions
        versions = create_version_tuples([
            "v8.2.1",      # GA version for 8.2 mainline
            "v8.2.2-rc01",  # Latest milestone for 8.2.2
            "v8.2.2-m02",  # Latest milestone for 8.2.2
            "v8.2.2-m01",  # Older milestone for 8.2.2
            "v8.1.0",      # GA version
        ])

        result = version_filter.filter_actual_versions(versions)

        # Should keep latest GA and latest milestone for each minor version
        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.2.2-rc01", "8.2.1", "8.1.0"]
        assert version_strings == expected_versions

    def test_filter_actual_versions_milestone_only(self):
        """Test actual version filtering with only milestone versions."""
        version_filter = VersionFilter(MockGitClient())

        versions = create_version_tuples([
            "v8.2.1-m02",
            "v8.2.1-m01",
            "v8.1.0-m01",
        ])

        result = version_filter.filter_actual_versions(versions)

        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.2.1-m02", "8.1.0-m01"]
        assert version_strings == expected_versions

    def test_filter_actual_versions_with_short_rc(self):
        """Test actual version filtering with short (without patch) versions."""
        version_filter = VersionFilter(MockGitClient())

        versions = create_version_tuples([
            "v8.4.0",
            "v8.4-rc1",
            "v8.2.3",
        ])

        result = version_filter.filter_actual_versions(versions)

        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.4.0", "8.2.3"]
        assert version_strings == expected_versions

    def test_filter_actual_versions_with_short_ga(self):
        """Test actual version filtering with short (without patch) versions."""
        version_filter = VersionFilter(MockGitClient())

        versions = create_version_tuples([
            "v8.4",
            "v8.4.0-rc1",
            "v8.2.3",
        ])

        result = version_filter.filter_actual_versions(versions)

        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.4", "8.2.3"]
        assert version_strings == expected_versions

    def test_filter_actual_versions_with_short_both_ga_and_rc(self):
        """Test actual version filtering with short (without patch) versions."""
        version_filter = VersionFilter(MockGitClient())

        versions = create_version_tuples([
            "v8.4",
            "v8.4-rc1",
            "v8.2.3",
        ])

        result = version_filter.filter_actual_versions(versions)

        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.4", "8.2.3"]
        assert version_strings == expected_versions

    def test_filter_actual_versions_empty(self):
        """Test actual version filtering with empty input."""
        version_filter = VersionFilter(MockGitClient())
        result = version_filter.filter_actual_versions([])
        assert result == []

    def test_get_actual_major_redis_versions_success(self):
        """Test the main entry point method with successful flow."""
        mock_git_client = MockGitClient()
        mock_git_client.set_remote_tags([
            ("commit001", "refs/tags/v8.2.1"),
            ("commit002", "refs/tags/v8.2.0"),
            ("commit003", "refs/tags/v8.1.0-eol"),  # Should be filtered out
            ("commit004", "refs/tags/v8.0.1"),
            ("commit005", "refs/tags/v8.0.0"),
        ])

        version_filter = VersionFilter(mock_git_client)
        result = version_filter.get_actual_major_redis_versions(8)

        # Should apply all filters: get tags -> filter EOL -> filter actual
        version_strings = [str(v[0]) for v in result]
        expected_versions = ["8.2.1", "8.0.1"]  # Latest patches, no EOL
        assert version_strings == expected_versions

    def test_get_actual_major_redis_versions_no_versions(self):
        """Test main entry point with no versions found."""
        mock_git_client = MockGitClient()
        mock_git_client.set_remote_tags([])

        version_filter = VersionFilter(mock_git_client)
        result = version_filter.get_actual_major_redis_versions(8)

        assert result == []

class TestVersionFilterIntegration:
    """Integration tests using real GitClient (mocked at subprocess level)."""

    @patch('stackbrew_generator.git_operations.subprocess.run')
    def test_integration_with_real_git_client(self, mock_subprocess):
        """Test VersionFilter with real GitClient (mocked subprocess)."""
        # Mock git ls-remote output
        mock_subprocess.return_value.stdout = (
            "commit001\trefs/tags/v8.2.1\n"
            "commit002\trefs/tags/v8.2.0\n"
            "commit003\trefs/tags/v8.1.0-eol\n"
        )
        mock_subprocess.return_value.returncode = 0

        git_client = GitClient()
        version_filter = VersionFilter(git_client)

        result = version_filter.get_actual_major_redis_versions(8)

        # Should get filtered results
        version_strings = [str(v[0]) for v in result]
        commits = [v[1] for v in result]
        expected_versions = ["8.2.1"]  # Only 8.2.1 after all filtering
        expected_commits = ["commit001"]
        assert version_strings == expected_versions
        assert commits == expected_commits
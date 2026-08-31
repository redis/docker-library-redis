"""Tests for stackbrew library generation."""

from stackbrew_generator.models import RedisVersion, Distribution, DistroType, Release
from stackbrew_generator.stackbrew import StackbrewGenerator


class TestStackbrewGenerator:
    """Tests for StackbrewGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = StackbrewGenerator()

    def test_generate_tags_debian_ga_latest(self):
        """Test tag generation for Debian GA version (latest in major and global latest major)."""
        version = RedisVersion.parse("8.2.1")
        distribution = Distribution(type=DistroType.DEBIAN, name="bookworm")
        release = Release(commit="abc123", version=version, distribution=distribution, git_fetch_ref="refs/tags/v8.2.1")

        tags = self.generator.generate_tags_for_release(
            release,
            is_latest_minor=True,
            emit_global_latest=True,
        )

        expected_tags = [
            "8.2.1",      # Full version
            "8.2",        # Mainline version (GA only)
            "8",          # Major version (latest only)
            "8.2.1-bookworm",  # Version with distro
            "8.2-bookworm",    # Mainline with distro
            "8-bookworm",      # Major with distro
            "latest",     # Latest tag (default distro only)
            "bookworm"    # Bare distro name (latest only)
        ]

        assert set(tags) == set(expected_tags)

    def test_generate_tags_debian_ga_not_latest(self):
        """Test tag generation for Debian GA version (not latest in major or global latest major)."""
        version = RedisVersion.parse("8.1.5")
        distribution = Distribution(type=DistroType.DEBIAN, name="bookworm")
        release = Release(commit="abc123", version=version, distribution=distribution, git_fetch_ref="refs/tags/v8.1.5")

        tags = self.generator.generate_tags_for_release(
            release,
            is_latest_minor=False,
            emit_global_latest=False,
        )

        expected_tags = [
            "8.1.5",           # Full version
            "8.1",             # Mainline version (GA only)
            "8.1.5-bookworm",  # Version with distro
            "8.1-bookworm"     # Mainline with distro
        ]

        assert set(tags) == set(expected_tags)

    def test_generate_tags_alpine_ga_latest(self):
        """Test tag generation for Alpine GA version (latest in major and global latest major)."""
        version = RedisVersion.parse("8.2.1")
        distribution = Distribution(type=DistroType.ALPINE, name="alpine3.22")
        release = Release(commit="abc123", version=version, distribution=distribution, git_fetch_ref="refs/tags/v8.2.1")

        tags = self.generator.generate_tags_for_release(
            release,
            is_latest_minor=True,
            emit_global_latest=True,
        )

        expected_tags = [
            "8.2.1-alpine",      # Version with distro type
            "8.2.1-alpine3.22",  # Version with full distro name
            "8.2-alpine",        # Mainline with distro type
            "8.2-alpine3.22",    # Mainline with full distro name
            "8-alpine",          # Major with distro type
            "8-alpine3.22",      # Major with full distro name
            "alpine",            # Bare distro type (latest only)
            "alpine3.22"         # Bare distro name (latest only)
        ]

        assert set(tags) == set(expected_tags)

    def test_generate_tags_milestone_version(self):
        """Test tag generation for milestone version."""
        version = RedisVersion.parse("8.2.1-m01")
        distribution = Distribution(type=DistroType.DEBIAN, name="bookworm")
        release = Release(commit="abc123", version=version, distribution=distribution, git_fetch_ref="refs/tags/v8.2.1-m01")

        tags = self.generator.generate_tags_for_release(
            release,
            is_latest_minor=False,
            emit_global_latest=False,
        )

        # Milestone versions should not get mainline version tags or major version tags
        expected_tags = [
            "8.2.1-m01",           # Full version only
            "8.2.1-m01-bookworm",  # Version with distro
        ]

        assert set(tags) == set(expected_tags)



    def test_generate_stackbrew_library(self):
        """Test complete stackbrew library generation."""
        releases = [
            Release(
                commit="abc123",
                version=RedisVersion.parse("8.2.1"),
                distribution=Distribution(type=DistroType.DEBIAN, name="bookworm"),
                git_fetch_ref="refs/tags/v8.2.1"
            ),
            Release(
                commit="abc123",
                version=RedisVersion.parse("8.2.1"),
                distribution=Distribution(type=DistroType.ALPINE, name="alpine3.22"),
                git_fetch_ref="refs/tags/v8.2.1"
            ),
            Release(
                commit="def456",
                version=RedisVersion.parse("8.1.5"),
                distribution=Distribution(type=DistroType.DEBIAN, name="bookworm"),
                git_fetch_ref="refs/tags/v8.1.5"
            )
        ]

        entries = self.generator.generate_stackbrew_library(releases)

        assert len(entries) == 3

        # Check that the 8.2.1 versions are marked as latest
        debian_8_2_1 = next(e for e in entries if e.version.patch == 1 and e.distribution.type == DistroType.DEBIAN)
        assert "latest" in debian_8_2_1.tags
        assert "8" in debian_8_2_1.tags

        # Check that 8.1.5 is not marked as latest
        debian_8_1_5 = next(e for e in entries if e.version.minor == 1)
        assert "latest" not in debian_8_1_5.tags
        assert "8" not in debian_8_1_5.tags

    def test_generate_stackbrew_library_assigns_major_aliases_per_distro_tag(self):
        """Assign moving aliases to the newest release for each distro name."""
        releases = [
            Release(
                commit="trixie-debian",
                version=RedisVersion.parse("8.10.1"),
                distribution=Distribution(type=DistroType.DEBIAN, name="trixie"),
                git_fetch_ref="refs/tags/v8.10.1",
            ),
            Release(
                commit="alpine-3.23",
                version=RedisVersion.parse("8.10.1"),
                distribution=Distribution(type=DistroType.ALPINE, name="alpine3.23"),
                git_fetch_ref="refs/tags/v8.10.1",
            ),
            Release(
                commit="alpine-3.22-current",
                version=RedisVersion.parse("8.4.6"),
                distribution=Distribution(type=DistroType.ALPINE, name="alpine3.22"),
                git_fetch_ref="refs/tags/v8.4.6",
            ),
            Release(
                commit="bookworm-debian",
                version=RedisVersion.parse("8.2.9"),
                distribution=Distribution(type=DistroType.DEBIAN, name="bookworm"),
                git_fetch_ref="refs/tags/v8.2.9",
            ),
            Release(
                commit="alpine-3.22-older",
                version=RedisVersion.parse("8.2.9"),
                distribution=Distribution(type=DistroType.ALPINE, name="alpine3.22"),
                git_fetch_ref="refs/tags/v8.2.9",
            ),
        ]

        entries = self.generator.generate_stackbrew_library(releases)

        trixie = next(
            entry
            for entry in entries
            if entry.distribution.type == DistroType.DEBIAN
            and entry.distribution.name == "trixie"
        )
        bookworm = next(
            entry
            for entry in entries
            if entry.distribution.type == DistroType.DEBIAN
            and entry.distribution.name == "bookworm"
        )
        alpine_3_23 = next(
            entry
            for entry in entries
            if entry.version.minor == 10
            and entry.distribution.type == DistroType.ALPINE
        )
        alpine_3_22_current = next(
            entry
            for entry in entries
            if entry.version.minor == 4
            and entry.distribution.type == DistroType.ALPINE
        )
        alpine_3_22_older = next(
            entry
            for entry in entries
            if entry.version.minor == 2
            and entry.distribution.type == DistroType.ALPINE
        )
        assert trixie.tags == [
            "8.10.1",
            "8.10",
            "8",
            "8.10.1-trixie",
            "8.10-trixie",
            "8-trixie",
            "latest",
            "trixie",
        ]
        assert bookworm.tags == [
            "8.2.9",
            "8.2",
            "8.2.9-bookworm",
            "8.2-bookworm",
            "8-bookworm",
            "bookworm",
        ]
        assert alpine_3_23.tags == [
            "8.10.1-alpine",
            "8.10-alpine",
            "8-alpine",
            "8.10.1-alpine3.23",
            "8.10-alpine3.23",
            "8-alpine3.23",
            "alpine",
            "alpine3.23",
        ]
        assert alpine_3_22_current.tags == [
            "8.4.6-alpine",
            "8.4-alpine",
            "8.4.6-alpine3.22",
            "8.4-alpine3.22",
            "8-alpine3.22",
            "alpine3.22",
        ]
        assert alpine_3_22_older.tags == [
            "8.2.9-alpine",
            "8.2-alpine",
            "8.2.9-alpine3.22",
            "8.2-alpine3.22",
        ]

        shuffled_entries = self.generator.generate_stackbrew_library(
            [releases[index] for index in (4, 2, 0, 3, 1)]
        )
        assert self.generator.format_stackbrew_output(
            shuffled_entries
        ) == self.generator.format_stackbrew_output(entries)

        non_global_entries = self.generator.generate_stackbrew_library(
            releases,
            emit_global_latest=False,
            emit_bare_aliases=False,
        )
        assert all("latest" not in entry.tags for entry in non_global_entries)
        assert all(
            distro_name not in entry.tags
            for entry in non_global_entries
            for distro_name in entry.distribution.tag_names
        )
        assert any("8-bookworm" in entry.tags for entry in non_global_entries)
        assert any("8-alpine3.22" in entry.tags for entry in non_global_entries)

        bare_only_entries = self.generator.generate_stackbrew_library(
            releases,
            emit_global_latest=False,
            emit_bare_aliases=True,
        )
        assert all("latest" not in entry.tags for entry in bare_only_entries)
        assert any("bookworm" in entry.tags for entry in bare_only_entries)
        assert any("alpine3.22" in entry.tags for entry in bare_only_entries)

        latest_only_entries = self.generator.generate_stackbrew_library(
            releases,
            emit_global_latest=True,
            emit_bare_aliases=False,
        )
        assert any("latest" in entry.tags for entry in latest_only_entries)
        assert all(
            distro_name not in entry.tags
            for entry in latest_only_entries
            for distro_name in entry.distribution.tag_names
        )

    def test_format_stackbrew_output(self):
        """Test stackbrew output formatting."""
        entries = [
            Release(
                commit="abc123",
                version=RedisVersion.parse("8.2.1"),
                distribution=Distribution(type=DistroType.DEBIAN, name="bookworm"),
                git_fetch_ref="refs/tags/v8.2.1"
            )
        ]

        stackbrew_entries = self.generator.generate_stackbrew_library(entries)
        output = self.generator.format_stackbrew_output(stackbrew_entries)

        assert isinstance(output, str)
        assert len(output) > 0
        # Should contain comma-separated tags
        assert "," in output

    def test_generate_stackbrew_library_with_head_milestone(self):
        """Test stackbrew generation with milestone at head (matches bash test)."""
        # This matches the bash test case: test_generate_stackbrew_library_with_head_milestone
        releases = [
            Release(
                commit="8d4437bdd0443189f9b3ba5943fdf793f821e8e2",
                version=RedisVersion.parse("8.2.2-m01-int1"),
                distribution=Distribution.from_dockerfile_line("FROM debian:bookworm"),
                git_fetch_ref="refs/tags/v8.2.2-m01-int1"
            ),
            Release(
                commit="8d4437bdd0443189f9b3ba5943fdf793f821e8e2",
                version=RedisVersion.parse("8.2.2-m01-int1"),
                distribution=Distribution.from_dockerfile_line("FROM alpine:3.22"),
                git_fetch_ref="refs/tags/v8.2.2-m01-int1"
            ),
            Release(
                commit="a13b78815d980881e57f15b9cf13cd2f26f3fab6",
                version=RedisVersion.parse("8.2.1"),
                distribution=Distribution.from_dockerfile_line("FROM debian:bookworm"),
                git_fetch_ref="refs/tags/v8.2.1"
            ),
            Release(
                commit="a13b78815d980881e57f15b9cf13cd2f26f3fab6",
                version=RedisVersion.parse("8.2.1"),
                distribution=Distribution.from_dockerfile_line("FROM alpine:3.22"),
                git_fetch_ref="refs/tags/v8.2.1"
            ),
            Release(
                commit="101262a8cf05b98137d88bc17e77db90c24cc783",
                version=RedisVersion.parse("8.0.3"),
                distribution=Distribution.from_dockerfile_line("FROM debian:bookworm"),
                git_fetch_ref="refs/tags/v8.0.3"
            ),
            Release(
                commit="101262a8cf05b98137d88bc17e77db90c24cc783",
                version=RedisVersion.parse("8.0.3"),
                distribution=Distribution.from_dockerfile_line("FROM alpine:3.21"),
                git_fetch_ref="refs/tags/v8.0.3"
            )
        ]

        entries = self.generator.generate_stackbrew_library(releases)

        # Expected tags based on bash test
        expected_tags = [
            ["8.2.2-m01-int1", "8.2.2-m01-int1-bookworm"],  # milestone - no major/mainline tags
            ["8.2.2-m01-int1-alpine", "8.2.2-m01-int1-alpine3.22"],  # milestone - no major/mainline tags
            ["8.2.1", "8.2", "8", "8.2.1-bookworm", "8.2-bookworm", "8-bookworm", "latest", "bookworm"],  # GA - gets all tags
            ["8.2.1-alpine", "8.2-alpine", "8-alpine", "8.2.1-alpine3.22", "8.2-alpine3.22", "8-alpine3.22", "alpine", "alpine3.22"],  # GA - gets all tags
            ["8.0.3", "8.0", "8.0.3-bookworm", "8.0-bookworm"],  # different minor - no major tags
            ["8.0.3-alpine", "8.0-alpine", "8.0.3-alpine3.21", "8.0-alpine3.21", "8-alpine3.21", "alpine3.21"]  # newest release for Alpine 3.21
        ]

        assert len(entries) == 6
        for i, entry in enumerate(entries):
            assert set(entry.tags) == set(expected_tags[i]), f"Tags mismatch for entry {i}: {entry.tags} != {expected_tags[i]}"

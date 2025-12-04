"""Data models for stackbrew library generation."""

import functools
import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class DistroType(str, Enum):
    """Distribution type enumeration."""

    ALPINE = "alpine"
    DEBIAN = "debian"


@functools.total_ordering
class RedisVersion(BaseModel):
    """Represents a parsed Redis version.

    TODO: This class duplicates the code from redis-developer/redis-oss-release-automation
    """

    major: int = Field(..., ge=1, description="Major version number")
    minor: int = Field(..., ge=0, description="Minor version number")
    patch: Optional[int] = Field(None, ge=0, description="Patch version number")
    suffix: str = Field("", description="Version suffix (e.g., -m01, -rc1, -eol)")

    @classmethod
    def parse(cls, version_str: str) -> "RedisVersion":
        """Parse a version string into components.

        Args:
            version_str: Version string (e.g., "v8.2.1-m01", "8.2", "7.4.0-eol")

        Returns:
            RedisVersion instance

        Raises:
            ValueError: If version string format is invalid
        """
        # Remove 'v' prefix if present
        version = version_str.lstrip("v")

        # Extract numeric part and suffix
        match = re.match(r"^([1-9]\d*\.\d+(?:\.\d+)?)(.*)", version)
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")

        numeric_part, suffix = match.groups()

        # Parse numeric components
        parts = numeric_part.split(".")
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) > 2 else None

        return cls(major=major, minor=minor, patch=patch, suffix=suffix)

    @property
    def is_milestone(self) -> bool:
        """Check if this is a milestone version (has suffix)."""
        return bool(self.suffix)

    @property
    def is_eol(self) -> bool:
        """Check if this version is end-of-life."""
        return self.suffix.lower().endswith("-eol")

    @property
    def is_rc(self) -> bool:
        """Check if this version is a release candidate."""
        return self.suffix.lower().startswith("-rc")

    @property
    def is_ga(self) -> bool:
        """Check if this version is a general availability (GA) release."""
        return not self.is_milestone

    @property
    def is_internal(self) -> bool:
        """Check if this version is an internal release."""
        return bool(re.search(r"-int\d*$", self.suffix.lower()))

    @property
    def mainline_version(self) -> str:
        """Get the mainline version string (major.minor)."""
        return f"{self.major}.{self.minor}"

    @property
    def suffix_weight(self) -> str:
        # warning: using lexicographic order, letters doesn't have any meaning except for ordering
        suffix_weight = ""
        if self.is_ga:
            suffix_weight = "QQ"
        if self.is_rc:
            suffix_weight = "LL"
        elif self.suffix.startswith("-m"):
            suffix_weight = "II"

        # internal versions are always lower than their GA/rc/m counterparts
        if self.is_internal:
            suffix_weight = suffix_weight[:1] + "E"

        return suffix_weight

    @property
    def sort_key(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch or 0}.{self.suffix_weight}{self.suffix}"

    def __str__(self) -> str:
        """String representation of the version."""
        version = f"{self.major}.{self.minor}"
        if self.patch is not None:
            version += f".{self.patch}"
        return version + self.suffix

    def __lt__(self, other: "RedisVersion") -> bool:
        """Compare versions for sorting."""
        if not isinstance(other, RedisVersion):
            return NotImplemented

        return self.sort_key < other.sort_key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RedisVersion):
            return NotImplemented

        return self.sort_key == other.sort_key

    def __hash__(self) -> int:
        """Hash for use in sets and dicts."""
        return hash((self.major, self.minor, self.patch or 0, self.suffix))


class Distribution(BaseModel):
    """Represents a Linux distribution."""

    type: DistroType = Field(..., description="Distribution type")
    name: str = Field(..., description="Distribution name/version")

    @classmethod
    def from_dockerfile_line(cls, from_line: str) -> "Distribution":
        """Parse distribution from Dockerfile FROM line.

        Args:
            from_line: FROM line from Dockerfile (e.g., "FROM alpine:3.22")

        Returns:
            Distribution instance

        Raises:
            ValueError: If FROM line format is not supported
        """
        # Extract base image from FROM line
        parts = from_line.strip().split()
        if len(parts) < 2 or parts[0].upper() != "FROM":
            raise ValueError(f"Invalid FROM line: {from_line}")

        base_img = parts[1]

        if "alpine:" in base_img:
            # Extract alpine version (e.g., alpine:3.22 -> alpine3.22)
            version = base_img.split(":", 1)[1]
            return cls(type=DistroType.ALPINE, name=f"alpine{version}")
        elif "debian:" in base_img:
            # Extract debian version, remove -slim suffix
            version = base_img.split(":", 1)[1].replace("-slim", "")
            return cls(type=DistroType.DEBIAN, name=version)
        else:
            raise ValueError(f"Unsupported base image: {base_img}")

    @property
    def is_default(self) -> bool:
        """Check if this is the default distribution (Debian)."""
        return self.type == DistroType.DEBIAN

    @property
    def tag_names(self) -> List[str]:
        """Get tag name components for this distribution."""
        if self.type == DistroType.ALPINE:
            return [self.type.value, self.name]
        else:
            return [self.name]


class Release(BaseModel):
    """Represents a Redis release with distribution information."""

    commit: str = Field(..., description="Git commit hash")
    version: RedisVersion = Field(..., description="Redis version")
    distribution: Distribution = Field(..., description="Linux distribution")
    git_fetch_ref: str = Field(..., description="Git fetch reference (e.g., refs/tags/v8.2.1)")

    def __str__(self) -> str:
        """String representation of the release."""
        return f"{self.commit[:8]} {self.version} {self.distribution.type.value} {self.distribution.name}"

    def console_repr(self) -> str:
        """Rich console representation with markup."""
        return f"{self.commit[:8]} [bold yellow]{self.version}[/bold yellow] {self.distribution.type.value} [bold yellow]{self.distribution.name}[/bold yellow]"


class StackbrewEntry(BaseModel):
    """Represents a stackbrew library entry with tags."""

    tags: List[str] = Field(..., description="Docker tags for this entry")
    commit: str = Field(..., description="Git commit hash")
    version: RedisVersion = Field(..., description="Redis version")
    distribution: Distribution = Field(..., description="Linux distribution")
    git_fetch_ref: str = Field(..., description="Git fetch reference (e.g., refs/tags/v8.2.1)")

    @property
    def architectures(self) -> List[str]:
        """Get supported architectures based on distribution type."""
        if self.distribution.type == DistroType.DEBIAN:
            return ["amd64", "arm32v5", "arm32v7", "arm64v8", "i386", "mips64le", "ppc64le", "s390x"]
        elif self.distribution.type == DistroType.ALPINE:
            return ["amd64", "arm32v6", "arm32v7", "arm64v8", "i386", "ppc64le", "riscv64", "s390x"]
        else:
            # Fallback to debian architectures for unknown distributions
            return ["amd64", "arm32v5", "arm32v7", "arm64v8", "i386", "mips64le", "ppc64le", "s390x"]

    def __str__(self) -> str:
        """String representation in stackbrew format."""
        lines = []
        lines.append(f"Tags: {', '.join(self.tags)}")
        lines.append(f"Architectures: {', '.join(self.architectures)}")
        lines.append(f"GitCommit: {self.commit}")
        lines.append(f"GitFetch: {self.git_fetch_ref}")
        lines.append(f"Directory: {self.distribution.type.value}")
        return "\n".join(lines)

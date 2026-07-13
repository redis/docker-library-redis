"""Data models for stackbrew library generation."""

from enum import Enum
from typing import List, Tuple

from pydantic import BaseModel, Field
from redis_version import RedisVersion


class DistroType(str, Enum):
    """Distribution type enumeration."""

    ALPINE = "alpine"
    DEBIAN = "debian"


class DebianRelease:
    """Debian release names."""

    TRIXIE = "trixie"
    BOOKWORM = "bookworm"


DEBIAN_TRIXIE_ARCHITECTURES: Tuple[str, ...] = (
    "amd64",
    "arm32v5",
    "arm32v7",
    "arm64v8",
    "i386",
    "riscv64",
    "ppc64le",
    "s390x",
)
DEBIAN_BOOKWORM_ARCHITECTURES: Tuple[str, ...] = (
    "amd64",
    "arm32v5",
    "arm32v7",
    "arm64v8",
    "i386",
    "mips64le",
    "ppc64le",
    "s390x",
)
ALPINE_ARCHITECTURES: Tuple[str, ...] = (
    "amd64",
    "arm32v6",
    "arm32v7",
    "arm64v8",
    "i386",
    "ppc64le",
    "riscv64",
    "s390x",
)

DEBIAN_ARCHITECTURES: dict[str, Tuple[str, ...]] = {
    DebianRelease.TRIXIE: DEBIAN_TRIXIE_ARCHITECTURES,
    DebianRelease.BOOKWORM: DEBIAN_BOOKWORM_ARCHITECTURES,
}

STACKBREW_TO_DOCKER_PLATFORM: dict[str, str] = {
    "amd64": "linux/amd64",
    "arm32v5": "linux/arm/v5",
    "arm32v6": "linux/arm/v6",
    "arm32v7": "linux/arm/v7",
    "arm64v8": "linux/arm64",
    "i386": "linux/i386",
    "ppc64le": "linux/ppc64le",
    "riscv64": "linux/riscv64",
    "s390x": "linux/s390x",
}


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
    git_fetch_ref: str = Field(
        ..., description="Git fetch reference (e.g., refs/tags/v8.2.1)"
    )

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
    git_fetch_ref: str = Field(
        ..., description="Git fetch reference (e.g., refs/tags/v8.2.1)"
    )

    @property
    def architectures(self) -> List[str]:
        """Get supported architectures based on distribution type and version."""
        return get_architectures_for_distribution(self.distribution)

    def __str__(self) -> str:
        """String representation in stackbrew format."""
        lines = []
        lines.append(f"Tags: {', '.join(self.tags)}")
        lines.append(f"Architectures: {', '.join(self.architectures)}")
        lines.append(f"GitCommit: {self.commit}")
        lines.append(f"GitFetch: {self.git_fetch_ref}")
        lines.append(f"Directory: {self.distribution.type.value}")
        return "\n".join(lines)


def get_architectures_for_distribution(distribution: Distribution) -> List[str]:
    """Get supported stackbrew architectures for a distribution."""
    if distribution.type == DistroType.DEBIAN:
        archs = DEBIAN_ARCHITECTURES.get(distribution.name, DEBIAN_TRIXIE_ARCHITECTURES)
        return list(archs)
    if distribution.type == DistroType.ALPINE:
        return list(ALPINE_ARCHITECTURES)
    raise ValueError(f"Unsupported distribution type: {distribution.type}")


def get_docker_platforms_for_distribution(distribution: Distribution) -> List[str]:
    """Map supported stackbrew architectures to Docker platforms."""
    return [
        STACKBREW_TO_DOCKER_PLATFORM[arch]
        for arch in get_architectures_for_distribution(distribution)
        if arch in STACKBREW_TO_DOCKER_PLATFORM
    ]

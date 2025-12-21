"""Distribution detection from Dockerfiles."""

from typing import List, Tuple

from rich.console import Console

from .exceptions import DistributionError
from .git_operations import GitClient
from .models import Distribution, RedisVersion, Release

console = Console(stderr=True)


class DistributionDetector:
    """Detects distribution information from Dockerfiles."""

    def __init__(self, git_client: GitClient):
        """Initialize distribution detector.

        Args:
            git_client: Git client for operations
        """
        self.git_client = git_client

    def extract_distribution_from_dockerfile(self, dockerfile_content: str) -> Distribution:
        """Extract distribution information from Dockerfile content.

        Args:
            dockerfile_content: Content of the Dockerfile

        Returns:
            Distribution instance

        Raises:
            DistributionError: If distribution cannot be detected
        """
        # Find the FROM line
        from_line = None
        for line in dockerfile_content.split('\n'):
            line = line.strip()
            if line.upper().startswith('FROM '):
                from_line = line
                break

        if not from_line:
            raise DistributionError("No FROM line found in Dockerfile")

        try:
            return Distribution.from_dockerfile_line(from_line)
        except ValueError as e:
            raise DistributionError(f"Failed to parse distribution from FROM line: {e}") from e

    def get_distribution_for_commit(self, commit: str, distro_type: str) -> Distribution:
        """Get distribution information for a specific commit and distro type.

        Args:
            commit: Git commit hash
            distro_type: Distribution type ("debian" or "alpine")

        Returns:
            Distribution instance

        Raises:
            DistributionError: If distribution cannot be detected
        """
        dockerfile_path = f"{distro_type}/Dockerfile"

        try:
            dockerfile_content = self.git_client.show_file(commit, dockerfile_path)
            console.print(f"[dim]Retrieved {dockerfile_path} from {commit[:8]}[/dim]")

            distribution = self.extract_distribution_from_dockerfile(dockerfile_content)
            console.print(f"[dim]Detected distribution: {distribution.type.value} {distribution.name}[/dim]")

            return distribution

        except Exception as e:
            raise DistributionError(
                f"Failed to get distribution for {distro_type} from {commit}: {e}"
            ) from e

    def prepare_releases_list(self, versions: List[Tuple[RedisVersion, str, str]]) -> List[Release]:
        """Prepare list of releases with distribution information.

        Args:
            versions: List of (RedisVersion, commit, tag_ref) tuples

        Returns:
            List of Release objects with distribution information
        """
        console.print("[blue]Preparing releases list with distribution information[/blue]")

        releases = []
        distro_types = ["debian", "alpine"]

        for version, commit, tag_ref in versions:
            console.print(f"[dim]Processing [bold yellow]{version}[/bold yellow] - {commit[:8]}[/dim]")

            for distro_type in distro_types:
                try:
                    distribution = self.get_distribution_for_commit(commit, distro_type)

                    release = Release(
                        commit=commit,
                        version=version,
                        distribution=distribution,
                        git_fetch_ref=tag_ref
                    )

                    releases.append(release)
                    console.print(f"[dim]  Added: {release.console_repr()}[/dim]", highlight=False)

                except DistributionError as e:
                    console.print(f"[yellow]Warning: Failed to process {distro_type} for {version}: {e}[/yellow]")
                    continue

        console.print(f"[green]Prepared {len(releases)} releases[/green]")
        return releases

"""CLI interface for stackbrew library generator."""

import typer
from pathlib import Path
from rich.console import Console
from rich.traceback import install

from .distribution import DistributionDetector
from .exceptions import StackbrewGeneratorError
from .git_operations import GitClient
from .logging_config import setup_logging
from .models import RedisVersion
from .stackbrew import StackbrewGenerator, StackbrewUpdater
from .version_filter import VersionFilter

# Install rich traceback handler
install(show_locals=True)

app = typer.Typer(
    name="release-automation",
    help="Generate stackbrew library content for Redis Docker images",
    add_completion=False,
)

# Console for logging and user messages (stderr)
console = Console(stderr=True)


def _generate_stackbrew_content(major_version: int, remote: str, verbose: bool) -> str:
    """Generate stackbrew content for a major version.

    This helper function contains the common logic for generating stackbrew content
    that is used by both generate-stackbrew-content and update-stackbrew-file commands.

    Args:
        major_version: Redis major version to process
        remote: Git remote to use
        verbose: Whether to enable verbose output

    Returns:
        Generated stackbrew content as string

    Raises:
        typer.Exit: If no versions found or other errors occur
    """
    # Initialize components
    git_client = GitClient(remote=remote)
    version_filter = VersionFilter(git_client)
    distribution_detector = DistributionDetector(git_client)
    stackbrew_generator = StackbrewGenerator()

    # Get actual Redis versions to process
    versions = version_filter.get_actual_major_redis_versions(major_version)

    if not versions:
        console.print(f"[red]No versions found for Redis {major_version}.x[/red]")
        raise typer.Exit(1)

    # Fetch required refs
    refs_to_fetch = [commit for _, commit, _ in versions]
    git_client.fetch_refs(refs_to_fetch)

    # Prepare releases list with distribution information
    releases = distribution_detector.prepare_releases_list(versions)

    if not releases:
        console.print("[red]No releases prepared[/red]")
        raise typer.Exit(1)

    # Generate stackbrew library content
    entries = stackbrew_generator.generate_stackbrew_library(releases)
    output = stackbrew_generator.format_stackbrew_output(entries)

    if not output:
        console.print("[yellow]No stackbrew content generated[/yellow]")
        raise typer.Exit(1)

    if verbose:
        console.print(f"[green]Generated stackbrew library with {len(entries)} entries[/green]")

    return output


@app.command(name="generate-stackbrew-content")
def generate_stackbrew_content(
    major_version: int = typer.Argument(
        ...,
        help="Redis major version to process (e.g., 8 for Redis 8.x)"
    ),
    remote: str = typer.Option(
        "origin",
        "--remote",
        help="Git remote to use for fetching tags and branches"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output"
    ),
) -> None:
    """Generate stackbrew library content for Redis Docker images.

    This command:
    1. Fetches Redis version tags from the specified remote
    2. Filters versions to remove EOL and select latest patches
    3. Extracts distribution information from Dockerfiles
    4. Generates appropriate Docker tags for each version/distribution
    5. Outputs stackbrew library content
    """
    # Set up logging
    setup_logging(verbose=verbose, console=console)

    if verbose:
        console.print(f"[bold blue]Stackbrew Library Generator[/bold blue]")
        console.print(f"Major version: {major_version}")
        console.print(f"Remote: {remote}")

    try:
        # Generate stackbrew content using the helper function
        output = _generate_stackbrew_content(major_version, remote, verbose)

        # Output the stackbrew library content
        print(output)

    except StackbrewGeneratorError as e:
        if verbose and hasattr(e, 'get_detailed_message'):
            console.print(f"[red]{e.get_detailed_message()}[/red]")
        else:
            console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def update_stackbrew_file(
    major_version: int = typer.Argument(
        ...,
        help="Redis major version to update (e.g., 8 for Redis 8.x)"
    ),
    input_file: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Path to the stackbrew library file to update"
    ),
    output_file: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (defaults to stdout)"
    ),
    remote: str = typer.Option(
        "origin",
        "--remote",
        help="Git remote to use for fetching tags and branches"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output"
    ),
) -> None:
    """Update stackbrew library file by replacing entries for a specific major version.

    This command:
    1. Reads the existing stackbrew library file
    2. Generates new stackbrew content for the specified major version
    3. Replaces all entries related to that major version in their original position
    4. Preserves the header and entries for other major versions
    5. Outputs to stdout by default, or to specified output file
    """
    # Set up logging
    setup_logging(verbose=verbose, console=console)

    if not input_file.exists():
        console.print(f"[red]Input file does not exist: {input_file}[/red]")
        raise typer.Exit(1)

    if verbose:
        console.print(f"[bold blue]Stackbrew Library File Updater[/bold blue]")
        console.print(f"Input file: {input_file}")
        if output_file:
            console.print(f"Output file: {output_file}")
        else:
            console.print("Output: stdout")
        console.print(f"Major version: {major_version}")
        console.print(f"Remote: {remote}")

    try:
        # Generate new stackbrew content for the major version using helper function
        new_content = _generate_stackbrew_content(major_version, remote, verbose)

        # Update the stackbrew file content
        updater = StackbrewUpdater()
        updated_content = updater.update_stackbrew_content(
            input_file, major_version, new_content, verbose
        )

        # Write the updated content
        if output_file:
            output_file.write_text(updated_content, encoding='utf-8')
            if verbose:
                console.print(f"[green]Successfully updated {output_file} for Redis {major_version}.x[/green]")
            else:
                console.print(f"[green]Updated {output_file}[/green]")
        else:
            # Output to stdout
            print(updated_content)
            if verbose:
                console.print(f"[green]Generated updated stackbrew content for Redis {major_version}.x[/green]")

    except StackbrewGeneratorError as e:
        if verbose and hasattr(e, 'get_detailed_message'):
            console.print(f"[red]{e.get_detailed_message()}[/red]")
        else:
            console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Create a subcommand group for redis-version
redis_version_app = typer.Typer(
    name="redis-version",
    help="Parse and extract Redis version information",
    add_completion=False,
)
app.add_typer(redis_version_app, name="redis-version")


@redis_version_app.command(name="major")
def redis_version_major(
    version: str = typer.Argument(
        ...,
        help="Redis version to parse (e.g., '8.2.1', 'v8.2.1-rc1', '7.4.0-eol')"
    ),
) -> None:
    """Print the major version number.

    Examples:
        redis-version major 8.2.1          # Prints: 8
        redis-version major v7.4.0-rc1     # Prints: 7
    """
    try:
        redis_version = RedisVersion.parse(version)
        print(redis_version.major)
    except (ValueError, Exception) as e:
        console.print(f"[red]Failed to parse version '{version}': {e}[/red]")
        raise typer.Exit(2)


@redis_version_app.command(name="minor")
def redis_version_minor(
    version: str = typer.Argument(
        ...,
        help="Redis version to parse (e.g., '8.2.1', 'v8.2.1-rc1', '7.4.0-eol')"
    ),
) -> None:
    """Print the minor version number.

    Examples:
        redis-version minor 8.2.1          # Prints: 2
        redis-version minor v7.4.0-rc1     # Prints: 4
    """
    try:
        redis_version = RedisVersion.parse(version)
        print(redis_version.minor)
    except (ValueError, Exception) as e:
        console.print(f"[red]Failed to parse version '{version}': {e}[/red]")
        raise typer.Exit(2)


@redis_version_app.command(name="patch")
def redis_version_patch(
    version: str = typer.Argument(
        ...,
        help="Redis version to parse (e.g., '8.2.1', 'v8.2.1-rc1', '7.4.0-eol')"
    ),
) -> None:
    """Print the patch version number.

    Examples:
        redis-version patch 8.2.1          # Prints: 1
        redis-version patch v7.4.0-rc1     # Prints: 0
        redis-version patch 8.2            # Prints: (empty, no patch)
    """
    try:
        redis_version = RedisVersion.parse(version)
        if redis_version.patch is not None:
            print(redis_version.patch)
    except (ValueError, Exception) as e:
        console.print(f"[red]Failed to parse version '{version}': {e}[/red]")
        raise typer.Exit(2)


@redis_version_app.command(name="parts")
def redis_version_parts(
    version: str = typer.Argument(
        ...,
        help="Redis version to parse (e.g., '8.2.1', 'v8.2.1-rc1', '7.4.0-eol')"
    ),
) -> None:
    """Print all version parts as space-separated values: major minor patch suffix.

    Examples:
        redis-version parts 8.2.1          # Prints: 8 2 1
        redis-version parts v7.4.0-rc1     # Prints: 7 4 0 -rc1
        redis-version parts 8.2            # Prints: 8 2
    """
    try:
        redis_version = RedisVersion.parse(version)
        parts = [str(redis_version.major), str(redis_version.minor)]
        parts.append(str(redis_version.patch) if redis_version.patch is not None else "0")
        parts.append(redis_version.suffix if redis_version.suffix else "")
        print(" ".join(parts))
    except (ValueError, Exception) as e:
        console.print(f"[red]Failed to parse version '{version}': {e}[/red]")
        raise typer.Exit(2)


@redis_version_app.command(name="check")
def redis_version_check(
    version: str = typer.Argument(
        ...,
        help="Redis version to check (e.g., '8.2.1', 'v8.2.1-rc1', '7.4.0-eol')"
    ),
    check: str = typer.Argument(
        ...,
        help="Property to check: is-internal, is-ga, is-eol, is-rc, is-milestone"
    ),
) -> None:
    """Check Redis version properties.

    Returns exit code:
    - 0 if the property is True
    - 1 if the property is False
    - 2 if the version could not be parsed

    Examples:
        redis-version check 8.2.1 is-ga          # Returns 0 (True)
        redis-version check 8.2.1-rc1 is-rc      # Returns 0 (True)
        redis-version check 8.2.1-rc1 is-ga      # Returns 1 (False)
        redis-version check invalid is-ga        # Returns 2 (Parse error)
    """
    # Validate check argument
    valid_checks = {"is-internal", "is-ga", "is-eol", "is-rc", "is-milestone"}
    if check not in valid_checks:
        console.print(f"[red]Invalid check: {check}[/red]")
        console.print(f"[yellow]Valid checks: {', '.join(sorted(valid_checks))}[/yellow]")
        raise typer.Exit(2)

    # Try to parse the version
    try:
        redis_version = RedisVersion.parse(version)
    except (ValueError, Exception) as e:
        console.print(f"[red]Failed to parse version '{version}': {e}[/red]")
        raise typer.Exit(2)

    # Map check string to property
    property_map = {
        "is-internal": redis_version.is_internal,
        "is-ga": redis_version.is_ga,
        "is-eol": redis_version.is_eol,
        "is-rc": redis_version.is_rc,
        "is-milestone": redis_version.is_milestone,
    }

    # Get the property value
    result = property_map[check]

    # Exit with appropriate code
    if result:
        raise typer.Exit(0)
    else:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

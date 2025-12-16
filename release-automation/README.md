# Docker release process and release automation description

This readme covers relase process for versions 8 and above.

In version 8 the docker-library structure has changed. Static Dockerfiles are used instead of templating. Versions live in a different mainline branches and are marked with tags.

The docker release process goal is to create a PR in official-docker library for library/redis file.

library/redis stackbrew file should reflect the tags in redis/docker-library-redis repository.

## Branches and tags

Mainline branches are named `release/Major.Minor` (e.g. `release/8.2`)

Each version release is tagged with `vMajor.Minor.Patch` (e.g. `v8.2.1`)

Milestone releases are tagged with `vMajor.Minor.Patch-Milestone` (e.g. `v8.2.1-m01`). Any suffix after patch version is considered a milestone.

Suffixes starting with `rc` are considered release candidates and are preferred over suffixes starting with `m` which in turn are preferred over any other suffix.

Tags without suffix are considered GA (General Availability) releases (e.g. `v8.2.1`).

Internal releases are milestone releases containing `-int` in their name (e.g. `v8.2.1-m01-int1` or `8.4.0-int3`). They are not released to the public.

Milestone releases never get latest or any other default tags, like `8`, `8.2`, `8.2.1`, `latest`, `bookworm`, etc.

For each mainline only one GA release and optionally any number of milestone releases with higher versions than this GA may be published in official-library.

Each patch version may have only one GA or milestone release, GA release is preferred over milestone release.

For example for this list of tags the following rules will be applied

* `v8.2.3-m01` - included because there is neither GA nor any higher milestone versions for 8.2.3
* `v8.2.2-rc2` - included because it higher version among 8.2.2
* `v8.2.2-rc1` - excluded because 8.2.2-rc2 is higher version
* `v8.2.2-m01` - excluded because 8.2.2-rc2 is higher version
* `v8.2.1-rc2` - excluded because there is 8.2.1 GA version
* `v8.2.1`     - included because it is highest GA for 8.2
* `v8.2.0`     - exluded because 8.2.1 is higher version

End of life versions are marked with `-eol` suffix (e.g. `v8.0.3-eol`). When there is a at least one minor version tagged with eol all versions in this minor series are considered EOL and are not included in the release file.

## Creating a release manually

This process is automated using github workflows. However, it's useful to understand the manual process.

Determine a mainline branch, e.g `release/8.2` for version `8.2.2`.

Optionally create a release branch from the mainline branch, e.g. `8.2.2`.

Modify dockerfiles.

Test dockerfiles.

If release branch was created, merge it back to mainline branch.

Tag commit with `vMajor.Minor.Patch` (e.g. `v8.2.1`) in the mainline branch.

Push your changes to redis/docker-library-redis repository.

Create a PR to official-library refering the tag and commit you created.


# Release automation tool

Release automation tool is used to generate library/redis file for official-library. It uses origin repository as a source of truth and follows the process described above.

## Installation

### From Source

```bash
cd release-automation
pip install -e .
```

### Development Installation

```bash
cd release-automation
pip install -e ".[dev]"
```

## Usage

```bash
release-automation --help
```

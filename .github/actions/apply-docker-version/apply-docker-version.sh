#!/bin/bash
set -e

# This script updates Redis version in Dockerfiles using environment variables
# REDIS_ARCHIVE_URL and REDIS_ARCHIVE_SHA, then commits changes if any were made.

# shellcheck disable=SC2034
last_cmd_stdout=""
# shellcheck disable=SC2034
last_cmd_stderr=""
# shellcheck disable=SC2034
last_cmd_result=0
# shellcheck disable=SC2034
VERBOSITY=1



SCRIPT_DIR="$(dirname -- "$( readlink -f -- "$0"; )")"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/../common/func.sh"

source_helper_file helpers.sh

# Input TAG is expected in $1
TAG="$1"

if [ -z "$TAG" ]; then
    echo "Error: TAG is required as first argument"
    exit 1
fi

# Check if required environment variables are set
if [ -z "$REDIS_ARCHIVE_URL" ]; then
    echo "Error: REDIS_ARCHIVE_URL environment variable is not set"
    exit 1
fi

if [ -z "$REDIS_ARCHIVE_SHA" ]; then
    echo "Error: REDIS_ARCHIVE_SHA environment variable is not set"
    exit 1
fi

echo "TAG: $TAG"
echo "REDIS_ARCHIVE_URL: $REDIS_ARCHIVE_URL"
echo "REDIS_ARCHIVE_SHA: $REDIS_ARCHIVE_SHA"

# Function to update Dockerfile
update_dockerfile() {
    local dockerfile="$1"
    local updated=false

    if [ ! -f "$dockerfile" ]; then
        echo "Warning: $dockerfile not found, skipping"
        return 1
    fi

    echo "Updating $dockerfile..."

    # Update REDIS_DOWNLOAD_URL
    if grep -q "^ENV REDIS_DOWNLOAD_URL=" "$dockerfile"; then
        sed -i "s|^ENV REDIS_DOWNLOAD_URL=.*|ENV REDIS_DOWNLOAD_URL=$REDIS_ARCHIVE_URL|" "$dockerfile"
    else
        echo "Cannot update $dockerfile, ENV REDIS_DOWNLOAD_URL not found"
        return 1
    fi


    # Update REDIS_DOWNLOAD_SHA
    if grep -q "^ENV REDIS_DOWNLOAD_SHA=" "$dockerfile"; then
        sed -i "s|^ENV REDIS_DOWNLOAD_SHA=.*|ENV REDIS_DOWNLOAD_SHA=$REDIS_ARCHIVE_SHA|" "$dockerfile"
    else
        echo "Cannot update $dockerfile, ENV REDIS_DOWNLOAD_SHA not found"
        return 1
    fi
}

docker_files=("debian/Dockerfile" "alpine/Dockerfile")
# Track which files were modified
changed_files=()

for dockerfile in "${docker_files[@]}"; do
    update_dockerfile "$dockerfile"
done

changed_files=($(git diff --name-only "${docker_files[@]}"))

# Output the list of changed files for GitHub Actions
if [ ${#changed_files[@]} -gt 0 ]; then
    echo "Files were modified:"
    printf '%s\n' "${changed_files[@]}"

    # Set GitHub Actions output
    changed_files_output=$(printf '%s\n' "${changed_files[@]}")
    {
        echo "changed_files<<EOF"
        echo "$changed_files_output"
        echo "EOF"
    } >> "$GITHUB_OUTPUT"

    echo "Changed files output set for next step"
else
    echo "No files were modified"
    echo "changed_files=" >> "$GITHUB_OUTPUT"
fi
#!/bin/bash
set -e

# This script updates .redis.version.json and regenerates Dockerfiles from templates
# using environment variables REDIS_ARCHIVE_URL and REDIS_ARCHIVE_SHA.

# Input TAG is expected in first argument
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

# Update .redis.version.json
echo "Updating .redis.version.json..."
cat > .redis.version.json <<EOF
{
	"release_tag": "$TAG",
	"redis_download_url": "$REDIS_ARCHIVE_URL",
	"redis_download_sha": "$REDIS_ARCHIVE_SHA"
}
EOF

# Render Dockerfiles from templates
./bin/render-all-dockerfiles.sh

# Detect changed files
changed_files=($(git diff --name-only .redis.version.json alpine/Dockerfile debian/Dockerfile))

# Output the list of changed files for GitHub Actions
if [ ${#changed_files[@]} -gt 0 ]; then
    echo "Files were modified:"
    printf '%s\n' "${changed_files[@]}"

    # Set GitHub Actions output
    if [ -n "$GITHUB_OUTPUT" ]; then
        changed_files_output=$(printf '%s\n' "${changed_files[@]}")
        {
            echo "changed_files<<EOF"
            echo "$changed_files_output"
            echo "EOF"
        } >> "$GITHUB_OUTPUT"
    fi

    echo "Changed files output set for next step"
else
    echo "No files were modified"
    echo "changed_files=" >> "$GITHUB_OUTPUT"
fi

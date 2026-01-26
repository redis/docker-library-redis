#!/bin/bash

# Without arguments will render Dockerfiles for official build, e.g.: with
# custom_build=false
# Any argument would disable this behavior and pass all arguments as-is to
# render-dockerfile for each distro.

set -e

if [ -z "$*" ]; then
    args=(-s custom_build false)
else
    args=("$@")
fi

for distro in alpine debian; do
    echo "Rendering $distro/Dockerfile..."
    uv run --directory release-automation release-automation render-dockerfile \
        -t ../$distro/Dockerfile.j2 \
        -j ../.redis.version.json \
        -o ../$distro/Dockerfile \
        "${args[@]}"
done
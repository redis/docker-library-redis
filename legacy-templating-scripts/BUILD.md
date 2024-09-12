# How the official Redis images are built

## Prepare the Docker files and metadata

The general process seems to involve the following steps:

0. Install command-line tools that are reported as being `not found`. I had to install `wget`, `jq`, and `bashbrew`.
1. Regenerate the `versions.json` file with the help of the `versions.sh`. This should fetch the latest Redis version from https://raw.githubusercontent.com/redis/redis-hashes/master/README and add it to the `version.json` file. If the version isn't picked up, you can also manually edit the `versions.json` file.
2. Apply the template on the versions via `apply-templates.sh`. This should create you a new version folder that's named by the `major.minor` Redis version number. This folder contains the `Dockerfile`.
3. Execute `generate-stackbrew-library.sh`. The script automates the generation of metadata for Redis Docker images, including tags, architectures, git commit hashes, and directories based on the versions.json file. It ensures that the metadata is up-to-date with the latest commits and correctly reflects the supported architectures and versions.

## Test the build locally

1. Change the directory to the recently added version and the target base image flavor, e.g., `cd ./7.4/debian`.
2. Build the image via `docker build`, e.g., `docker build -t redis-test:7.4-rc1 .`.
3. Run the image the same way as the official docker image: `docker run --name test-7-4-rc1 -d redis-test:7.4-rc1`.
4. Open a `redis-cli` on the container `docker exec -it test-7-4-rc1 redis-cli`.
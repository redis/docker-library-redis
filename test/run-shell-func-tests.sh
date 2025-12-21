#!/bin/bash
set -e -o pipefail
SCRIPT_DIR="$(dirname -- "$( readlink -f -- "$0"; )")"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/../.github/actions/common/func.sh"

source_helper_file "helpers.sh"

set -u

init_console_output

test_redis_version_split() {
    local major minor patch suffix
    local version

    version="8.2.1"
    IFS=: read -r major minor patch suffix < <(redis_version_split "$version")
    assertEquals "return code for $version" "0" "$?"
    assertEquals "major of $version" "8" "$major"
    assertEquals "minor of $version" "2" "$minor"
    assertEquals "patch of $version" "1" "$patch"
    assertEquals "suffix of $version" "" "$suffix"

    version="v8.2.1"
    IFS=: read -r major minor patch suffix < <(redis_version_split "$version")
    assertEquals "return code for $version" "0" "$?"
    assertEquals "major of $version" "8" "$major"
    assertEquals "minor of $version" "2" "$minor"
    assertEquals "patch of $version" "1" "$patch"
    assertEquals "suffix of $version" "" "$suffix"

    version="8.0-m01"
    IFS=: read -r major minor patch suffix < <(redis_version_split "$version")
    assertEquals "return code for $version" "0" "$?"
    assertEquals "major of $version" "8" "$major"
    assertEquals "minor of $version" "0" "$minor"
    assertEquals "patch of $version" "" "$patch"
    assertEquals "suffix of $version" "-m01" "$suffix"

    version="v8.0-m01"
    IFS=: read -r major minor patch suffix < <(redis_version_split "$version")
    assertEquals "return code for $version" "0" "$?"
    assertEquals "major of $version" "8" "$major"
    assertEquals "minor of $version" "0" "$minor"
    assertEquals "patch of $version" "" "$patch"
    assertEquals "suffix of $version" "-m01" "$suffix"

    version="8.0.3-m03-int"
    IFS=: read -r major minor patch suffix < <(redis_version_split "$version")
    assertEquals "return code for $version" "0" "$?"
    assertEquals "major of $version" "8" "$major"
    assertEquals "minor of $version" "0" "$minor"
    assertEquals "patch of $version" "3" "$patch"
    assertEquals "suffix of $version" "-m03-int" "$suffix"

    version="v8.0.3-m03-int"
    IFS=: read -r major minor patch suffix < <(redis_version_split "$version")
    assertEquals "return code for $version" "0" "$?"
    assertEquals "major of $version" "8" "$major"
    assertEquals "minor of $version" "0" "$minor"
    assertEquals "patch of $version" "3" "$patch"
    assertEquals "suffix of $version" "-m03-int" "$suffix"
}

test_redis_version_split_fail() {
    IFS=: read -r major minor patch suffix < <(redis_version_split 8.x.x)
    assertNotEquals "return code" "0" "$?"
}


# shellcheck disable=SC1091
. "$SCRIPT_DIR/shunit2"
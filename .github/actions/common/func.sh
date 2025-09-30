#!/bin/bash

# Sources a helper file from multiple possible locations (GITHUB_WORKSPACE, RELEASE_AUTOMATION_DIR, or relative path)
source_helper_file() {
    local helper_file="$1"
    local helper_errors=""
    for dir in "GITHUB_WORKSPACE:$GITHUB_WORKSPACE/redis-oss-release-automation" "RELEASE_AUTOMATION_DIR:$RELEASE_AUTOMATION_DIR" ":../redis-oss-release-automation"; do
        local var_name="${dir%%:*}"
        local dir="${dir#*:}"
        if [ -n "$var_name" ]; then
            var_name="\$$var_name"
        fi
        local helper_path="$dir/.github/actions/common/$helper_file"
        if [ -f "$helper_path" ]; then
            helper_errors=""
            # shellcheck disable=SC1090
            . "$helper_path"
            break
        else
            helper_errors=$(printf "%s\n  %s: %s" "$helper_errors" "$var_name" "$helper_path")
        fi
    done
    if [ -n "$helper_errors" ]; then
        echo "Error: $helper_file not found in any of the following locations: $helper_errors" >&2
        exit 1
    fi
}

# Splits a Redis version string into major:minor:patch:suffix components
redis_version_split() {
    local version
    local numerics
    # shellcheck disable=SC2001
    version=$(echo "$1" | sed 's/^v//')

    numerics=$(echo "$version" | grep -Po '^[1-9][0-9]*\.[0-9]+(\.[0-9]+|)' || :)
    if [ -z "$numerics" ]; then
        console_output 2 red "Cannot split version '$version', incorrect version format"
        return 1
    fi
    local major minor patch suffix
    IFS=. read -r major minor patch < <(echo "$numerics")
    suffix=${version:${#numerics}}
    printf "%s:%s:%s:%s\n" "$major" "$minor" "$patch" "$suffix"
}

slack_format_docker_image_urls_message() {
    # Parse the image URLs from JSON array
    jq --arg release_tag "$1" --arg footer "$2" '
        map(
            capture("(?<url>(?<prefix>[^:]+:)(?<version>[1-9][0-9]*[.][0-9]+[.][0-9]+(-[a-z0-9]+)*)-(?<commit>[a-f0-9]{40,})-(?<distro>[^-]+)-(?<arch>[^-]+))$")
        )
        as $items
        | {
            icon_emoji: ":redis-circle:",
            text: ("🐳 Docker Images Published for Redis: " + $release_tag),
            blocks: [
                {
                "type": "header",
                "text": { "type": "plain_text", "text": ("🐳 Docker Images Published for Release " + $release_tag) }
                },
                {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                    "The following Docker images have been published to Github Container Registry:\n\n" +
                    (
                        $items
                        | map(
                            "Distribution: *" + .distro + "* "
                            + "Architecture: *" + .arch + "*"
                            + "\n```\n" + .url + "\n```"
                        )
                        | join("\n\n")
                    )
                    )
                }
                },
                {
                "type": "context",
                "elements": [
                    { "type": "mrkdwn", "text": $footer }
                ]
                }
            ]
            }
        '
}

slack_format_docker_PR_message() {
    release_tag=$1
    url=$2
    footer=$3

# Create Slack message payload
    cat << EOF
{
"icon_emoji": ":redis-circle:",
"text": "🐳 Docker Library PR created for Redis: $release_tag",
"blocks": [
    {
    "type": "header",
    "text": {
        "type": "plain_text",
        "text": "🐳 Docker Library PR created for Redis: $release_tag"
    }
    },
    {
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": "$url"
    }
    },
    {
    "type": "context",
    "elements": [
        {
        "type": "mrkdwn",
        "text": "$footer"
        }
    ]
    }
]
}
EOF
}

slack_format_failure_message() {
    header=$1
    workflow_url=$2
    footer=$3
    if [ -z "$header" ]; then
        header=" "
    fi
    if [ -z "$footer" ]; then
        footer=" "
    fi

# Create Slack message payload
    cat << EOF
{
"icon_emoji": ":redis-circle:",
"text": "$header",
"blocks": [
    {
    "type": "header",
    "text": {
        "type": "plain_text",
        "text": "❌  $header"
    }
    },
    {
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": "Workflow run: $workflow_url"
    }
    },
    {
    "type": "context",
    "elements": [
        {
        "type": "mrkdwn",
        "text": "$footer"
        }
    ]
    }
]
}
EOF
}
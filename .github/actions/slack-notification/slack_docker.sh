#!/bin/bash

SCRIPT_DIR="$(dirname -- "$( readlink -f -- "$0"; )")"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/../common/func.sh"

source_helper_file slack.sh

slack_format_docker_images_metadata_message() {
    # Format the structured images metadata into a Slack message
    jq --arg channel "$1" --arg release_tag "$2" --arg footer "$3" '
        {
            channel: $channel,
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
                        .
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
    channel=$1
    release_tag=$2
    url=$3
    footer=$4

# Create Slack message payload
    cat << EOF
{
"channel": "$channel",
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
    channel=$1
    header=$2
    workflow_url=$3
    footer=$4
    if [ -z "$header" ]; then
        header=" "
    fi
    if [ -z "$footer" ]; then
        footer=" "
    fi

# Create Slack message payload
    cat << EOF
{
"channel": "$channel",
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
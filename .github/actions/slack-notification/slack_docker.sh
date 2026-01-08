#!/bin/bash

if [ -z "$GITHUB_ACTION_PATH" ]; then
    SCRIPT_DIR="$(dirname -- "$( readlink -f -- "$0"; )")"
    # shellcheck disable=SC1091
    . "$SCRIPT_DIR/../common/func.sh"
else
    . "$GITHUB_ACTION_PATH/../common/func.sh"
fi


source_helper_file slack.sh

slack_format_docker_images_metadata_message() {
    # Format the structured images metadata into a Slack message
    # Parameters: channel, release_tag, footer, slack_thread_ts (optional)
    local channel="$1"
    local release_tag="$2"
    local footer="$3"
    local slack_thread_ts="$4"

    jq --arg channel "$channel" --arg release_tag "$release_tag" --arg footer "$footer" --arg slack_thread_ts "$slack_thread_ts" '
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
        } | if $slack_thread_ts != "" then . + {thread_ts: $slack_thread_ts} else . end
        '
}

slack_format_docker_PR_message() {
    local channel=$1
    local release_tag=$2
    local url=$3
    local footer=$4
    local slack_thread_ts=$5

# Create Slack message payload
    local payload
    payload=$(cat << EOF
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
)

    # Add slack_thread_ts if provided
    if [ -n "$slack_thread_ts" ]; then
        echo "$payload" | jq --arg slack_thread_ts "$slack_thread_ts" '. + {thread_ts: $slack_thread_ts}'
    else
        echo "$payload"
    fi
}

slack_format_failure_message() {
    local channel=$1
    local header=$2
    local workflow_url=$3
    local footer=$4
    local slack_thread_ts=$5

    if [ -z "$header" ]; then
        header=" "
    fi
    if [ -z "$footer" ]; then
        footer=" "
    fi

# Create Slack message payload
    local payload
    payload=$(cat << EOF
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
)

    # Add slack_thread_ts if provided
    if [ -n "$slack_thread_ts" ]; then
        echo "$payload" | jq --arg slack_thread_ts "$slack_thread_ts" '. + {thread_ts: $slack_thread_ts}'
    else
        echo "$payload"
    fi
}
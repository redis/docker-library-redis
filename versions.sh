#!/usr/bin/env bash
set -Eeuo pipefail

alpine="$(
	bashbrew cat --format '{{ .TagEntry.Tags | join "\n" }}' https://github.com/docker-library/official-images/raw/HEAD/library/alpine:latest \
		| grep -E '^[0-9]+[.][0-9]+$'
)"
[ "$(wc -l <<<"$alpine")" = 1 ]
export alpine

debian="$(
	bashbrew cat --format '{{ .TagEntry.Tags | join "\n" }}' https://github.com/docker-library/official-images/raw/HEAD/library/debian:latest \
		| grep -vE '^latest$|[0-9.-]' \
		| head -1
)"
[ "$(wc -l <<<"$debian")" = 1 ]
export debian

cd "$(dirname "$(readlink -f "$BASH_SOURCE")")"

versions=( "$@" )
if [ ${#versions[@]} -eq 0 ]; then
	versions=( */ )
	json='{}'
else
	json="$(< versions.json)"
fi
versions=( "${versions[@]%/}" )

packages="$(
	wget -qO- 'https://github.com/redis/redis-hashes/raw/master/README' \
		| jq -csR '
			rtrimstr("\n")
			| split("\n")
			| map(
				# this capture will naturally ignore comments and blank lines
				capture(
					[
						"^hash[[:space:]]+",
						"(?<file>redis-",
						"(?<version>([0-9.]+)(-rc[0-9]+)?)",
						"[.][^[:space:]]+)[[:space:]]+",
						"(?<type>sha256|sha1)[[:space:]]+", # this filters us down to just the checksum types we are prepared to handle right now
						"(?<sum>[0-9a-f]{64}|[0-9a-f]{40})[[:space:]]+",
						"(?<url>[^[:space:]]+)",
						"$"
					] | join("")
				)
				| {
					version: .version,
					url: .url,
					(.type): .sum,
				}
			)
		'
)"

for version in "${versions[@]}"; do
	export version rcVersion="${version%-rc}"

	doc="$(
		jq <<<"$packages" -c '
			map(
				select(
					.version
					| (
						startswith(env.rcVersion + ".")
						or startswith(env.rcVersion + "-")
					) and (
						index("-")
						| if env.version == env.rcVersion then not else . end
					)
				)
			)[-1]
		'
	)"

	fullVersion="$(jq <<<"$doc" -r '.version')"
	echo "$version: $fullVersion"

	json="$(jq <<<"$json" -c --argjson doc "$doc" '
		.[env.version] = ($doc + {
			debian: { version: env.debian },
			alpine: { version: env.alpine },
		})
	')"
done

jq <<<"$json" . > versions.json

#!/usr/bin/env bash
set -Eeuo pipefail

declare -A aliases=(
	[7.4]='7 latest'
	[6.2]='6'
)

self="$(basename "$BASH_SOURCE")"
cd "$(dirname "$(readlink -f "$BASH_SOURCE")")"

if [ "$#" -eq 0 ]; then
	versions="$(jq -r 'keys | map(@sh) | join(" ")' versions.json)"
	eval "set -- $versions"
fi

# sort version numbers with highest first
IFS=$'\n'; set -- $(sort -rV <<<"$*"); unset IFS

# get the most recent commit which modified any of "$@"
fileCommit() {
	git log -1 --format='format:%H' HEAD -- "$@"
}

# get the most recent commit which modified "$1/Dockerfile" or any file COPY'd from "$1/Dockerfile"
dirCommit() {
	local dir="$1"; shift
	(
		cd "$dir"
		fileCommit \
			Dockerfile \
			$(git show HEAD:./Dockerfile | awk '
				toupper($1) == "COPY" {
					for (i = 2; i < NF; i++) {
						print $i
					}
				}
			')
	)
}

getArches() {
	local repo="$1"; shift
	local officialImagesUrl='https://github.com/docker-library/official-images/raw/master/library/'

	eval "declare -g -A parentRepoToArches=( $(
		find -name 'Dockerfile' -exec awk '
				toupper($1) == "FROM" && $2 !~ /^('"$repo"'|scratch|.*\/.*)(:|$)/ {
					print "'"$officialImagesUrl"'" $2
				}
			' '{}' + \
			| sort -u \
			| xargs bashbrew cat --format '[{{ .RepoName }}:{{ .TagName }}]="{{ join " " .TagEntry.Architectures }}"'
	) )"
}
getArches 'redis'

cat <<-EOH
# This file was generated via https://github.com/redis/docker-library-redis/blob/$(fileCommit "$self")/$self

Maintainers: David Maier <david.maier@redis.com> (@dmaier-redislabs),
             Yossi Gottlieb <yossi@redis.com> (@yossigo)
GitRepo: https://github.com/redis/docker-library-redis.git
EOH

# prints "$2$1$3$1...$N"
join() {
	local sep="$1"; shift
	local out; printf -v out "${sep//%/%%}%s" "$@"
	echo "${out#$sep}"
}

for version; do
	export version

	fullVersion="$(jq -r '.[env.version].version' versions.json)"

	versionAliases=()
	while [ "$fullVersion" != "$version" ] && [ "${fullVersion%.*}" != "$fullVersion" ]; do
		versionAliases+=( $fullVersion )
		fullVersion="${fullVersion%.*}"
	done
	versionAliases+=(
		$version
		${aliases[$version]:-}
	)

	for variant in debian alpine; do
		export variant
		dir="$version/$variant"

		commit="$(dirCommit "$dir")"

		if [ "$variant" = 'debian' ]; then
			variantAliases=( "${versionAliases[@]}" )
		else
			variantAliases=( "${versionAliases[@]/%/-$variant}" )
			variantAliases=( "${variantAliases[@]//latest-/}" )
		fi

		parent="$(awk 'toupper($1) == "FROM" { print $2 }' "$dir/Dockerfile")"
		arches="${parentRepoToArches[$parent]}"

		suite="${parent#*:}" # "bookworm-slim", "bookworm"
		suite="${suite%-slim}" # "bookworm"
		if [ "$variant" = 'alpine' ]; then
			suite="alpine$suite" # "alpine3.18"
		fi
		suiteAliases=( "${versionAliases[@]/%/-$suite}" )
		suiteAliases=( "${suiteAliases[@]//latest-/}" )
		variantAliases+=( "${suiteAliases[@]}" )

		# calculate the intersection of parent image arches and gosu arches
		arches="$(jq -r --arg arches "$arches" '
			(
				$arches
				| gsub("^[[:space:]]+|[[:space:]]+$"; "")
				| split("[[:space:]]+"; "")
			) as $parentArches
			| .[env.version]
			| $parentArches - ($parentArches - (.gosu.arches | keys))
			| join(", ")
		' versions.json)"

		echo
		cat <<-EOE
			Tags: $(join ', ' "${variantAliases[@]}")
			Architectures: $arches
			GitCommit: $commit
			Directory: $dir
		EOE
	done
done

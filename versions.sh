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

gosus="$(
	git ls-remote --tags https://github.com/tianon/gosu.git \
		| cut -d/ -f3- \
		| cut -d^ -f1 \
		| grep -E '^[0-9]+' \
		| sort -urV
)"
gosu=
for possible in $gosus; do
	urlBase="https://github.com/tianon/gosu/releases/download/$possible"
	if shas="$(wget -qO- "$urlBase/SHA256SUMS")" && [ -n "$shas" ]; then
		gosu="$(jq <<<"$shas" -csR --arg version "$possible" --arg urlBase "$urlBase" '{
			version: $version,
			arches: (
				rtrimstr("\n")
				| split("\n")
				| map(
					# this capture will naturally ignore the ".asc" file checksums
					capture(
						[
							"^(?<sha256>[0-9a-f]{64})",
							"(  | [*])",
							"(?<file>",
								"gosu-",
								"(?<dpkgArch>[^_. -]+)",
							")$"
						] | join("")
					)
					| {
						(
							# convert dpkg arch into bashbrew arch
							{
								# https://salsa.debian.org/dpkg-team/dpkg/-/blob/main/data/cputable
								# https://wiki.debian.org/ArchitectureSpecificsMemo#Architecture_baselines
								# http://deb.debian.org/debian/dists/unstable/main/
								# http://deb.debian.org/debian/dists/stable/main/
								# https://deb.debian.org/debian-ports/dists/unstable/main/
								amd64: "amd64",
								armel: "arm32v5",
								armhf: "arm32v6", # https://github.com/tianon/gosu/blob/2dada3bb5dfbc1e7162a29907691b6f45995d54e/Dockerfile#L52-L53
								arm64: "arm64v8",
								i386: "i386",
								mips64el: "mips64le",
								ppc64el: "ppc64le",
								riscv64: "riscv64",
								s390x: "s390x",
							}[.dpkgArch] // empty
						): {
							url: ($urlBase + "/" + .file),
							sha256: .sha256,
						},
					}
				)
				| add
				| if has("arm32v6") and (has("arm32v7") | not) then
					.arm32v7 = .arm32v6
				else . end
			),
		}')"
		break
	fi
done
[ -n "$gosu" ]
export gosu

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
			gosu: (env.gosu | fromjson),
		})
	')"
done

jq <<<"$json" . > versions.json

# BUILD redisfab/redis:${REDIS_VER}-${ARCH}-${OSNICK}

ARG REDIS_VER=6.0.10

# OS=debian:buster-slim|debian:stretch-slim|ubuntu:bionic
ARG OS=debian:buster-slim

# OSNICK=stretch|bionic|buster
ARG OSNICK=buster

# ARCH=x64|arm64v8|arm32v7
ARG ARCH=x64

ARG UID=999

#----------------------------------------------------------------------------------------------
FROM ${OS} as builder

ARG REDIS_VER
ARG OS
ARG OSNICK
ARG ARCH
RUN echo "Building Redis v${REDIS_VER} on ${OSNICK} (${OS}) for ${ARCH}"
RUN uname -a; cat /etc/os-release

WORKDIR /build

ADD deps/ /build/deps/
ADD 6.0/system-setup.py /build/
ADD 6.0/*.patch /build/
ADD 6.0/build-fix-* /build/

# ENV REDIS_DEPENDS "ca-certificates dirmngr gnupg wget gcc libc6-dev make"
RUN /build/deps/readies/bin/getpy3
RUN /build/system-setup.py
RUN gcc --version

ENV GOSU_VERSION 1.12
RUN set -ex ;\
	/build/deps/readies/bin/getgosu ;\
	gosu --version; \
	gosu nobody true

ENV REDIS_VERSION ${REDIS_VER}
ENV REDIS_DOWNLOAD_URL https://github.com/redis/redis/archive/${REDIS_VER}.tar.gz
# ENV REDIS_DOWNLOAD_URL http://download.redis.io/releases/redis-${REDIS_VER}.tar.gz
ENV REDIS_DOWNLOAD_SHA dc2bdcf81c620e9f09cfd12e85d3bc631c897b2db7a55218fd8a65eaa37f86dd

# for redis-sentinel see: http://redis.io/topics/sentinel
RUN set -ex; \
	wget -q -O redis.tar.gz "$REDIS_DOWNLOAD_URL"; \
	mkdir -p /usr/src/redis; \
	tar -xzf redis.tar.gz -C /usr/src/redis --strip-components=1

RUN ./build-fix-1
RUN ./build-fix-2

# note: ARCH may break build if non-empty
RUN set -ex; \
	if [ -e /opt/rh/devtoolset-9/enable ]; then \
		source /opt/rh/devtoolset-9/enable ;\
	fi ;\
	export BUILD_TLS=yes; \
	ARCH= make V=1 -C /usr/src/redis -j $(nproc) all; \
	make -C /usr/src/redis install

#----------------------------------------------------------------------------------------------
FROM ${OS}

ARG REDIS_VER
ARG ARCH
ARG OSNICK
ARG UID

RUN echo "Building redisfab/redis-${ARCH}-${OSNICK}:${REDIS_VER} UID=${UID}"
RUN uname -a; cat /etc/os-release

# Add our user and group first to make sure their IDs get assigned consistently, 
# regardless of whatever dependencies get added
RUN groupadd -r -g ${UID} redis && useradd -r -g redis -u ${UID} redis

COPY 6.0/platforms/setup.${OSNICK} /usr/local/bin/docker-setup
RUN set -xe ;\
    chmod +x /usr/local/bin/docker-setup ;\
    /usr/local/bin/docker-setup ;\
    rm /usr/local/bin/docker-setup

COPY --from=builder /usr/local/ /usr/local/

RUN mkdir /data && chown redis:redis /data
VOLUME /data
WORKDIR /data

COPY 6.0/docker-entrypoint.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
EXPOSE 6379
CMD ["redis-server"]

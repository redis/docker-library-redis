# BUILD redisfab/redis:${REDIS_VER}-${ARCH}-${OSNICK}

ARG REDIS_VER=unstable
ARG REDIS_MAJOR=unstable
ARG OS=debian:bullseye-slim
ARG OSNICK=bullseye

# ARCH=x64|arm64v8|arm32v7
ARG ARCH=x64

ARG UID=999

ARG JEMALLOC=yes

#----------------------------------------------------------------------------------------------
FROM ${OS} as builder

ARG REDIS_VER
ARG REDIS_MAJOR
ARG OS
ARG OSNICK
ARG ARCH
ARG JEMALLOC

RUN echo "Building Redis v${REDIS_VER} on ${OSNICK} (${OS}) for ${ARCH}"
RUN uname -a; cat /etc/os-release

RUN if [ -f /root/.profile ]; then sed -ie 's/mesg n/tty -s \&\& mesg -n/g' /root/.profile; fi
SHELL ["/bin/bash", "-l", "-c"]

WORKDIR /build

ADD deps/ /build/deps/
ADD ${REDIS_MAJOR}/system-setup.py /build/
ADD ${REDIS_MAJOR}/*.patch /build/
ADD ${REDIS_MAJOR}/build-fix-* /build/

# ENV REDIS_DEPENDS "ca-certificates dirmngr gnupg wget gcc libc6-dev make"

# WORKAROUND for glibc 2.33 and old Docker
# See https://github.com/actions/virtual-environments/issues/2658
# Thanks to https://github.com/lxqt/lxqt-panel/pull/1562
#RUN patched_glibc=glibc-linux4-2.33-4-x86_64.pkg.tar.zst && \
#    curl -LO "https://repo.archlinuxcn.org/x86_64/$patched_glibc" && \
#    bsdtar -C / -xvf "$patched_glibc"

RUN /build/deps/readies/bin/getbash
RUN /build/deps/readies/bin/getupdates
RUN /build/deps/readies/bin/getpy3
RUN	/build/system-setup.py

RUN gcc --version

ENV GOSU_VERSION 1.16
RUN set -ex ;\
	/build/deps/readies/bin/getgosu ;\
	gosu --version; \
	gosu nobody true

ENV REDIS_VERSION ${REDIS_VER}
ENV REDIS_DOWNLOAD_URL https://github.com/redis/redis/archive/${REDIS_VER}.tar.gz
# ENV REDIS_DOWNLOAD_URL http://download.redis.io/releases/redis-${REDIS_VER}.tar.gz
ENV REDIS_DOWNLOAD_SHA dc2bdcf81c620e9f09cfd12e85d3bc631c897b2db7a55218fd8a65eaa37f86dd
ENV JEMALLOC ${JEMALLOC}

# for redis-sentinel see: http://redis.io/topics/sentinel
RUN set -ex; \
	wget -q -O redis.tar.gz "$REDIS_DOWNLOAD_URL"; \
	mkdir -p /usr/src/redis; \
	tar -xzf redis.tar.gz -C /usr/src/redis --strip-components=1

RUN ./build-fix-1
RUN ./build-fix-2

# note: ARCH may break build if non-empty
RUN set -ex; \
	export BUILD_TLS=yes; \
	/build/deps/readies/bin/runn ARCH= make REDIS_CFLAGS=-DUSE_JEMALLOC=${JEMALLOC} V=1 -C /usr/src/redis all; \
	/build/deps/readies/bin/runn make -C /usr/src/redis install

#----------------------------------------------------------------------------------------------
FROM ${OS}

ARG REDIS_VER
ARG REDIS_MAJOR
ARG ARCH
ARG OSNICK
ARG UID

RUN echo "Building redisfab/redis-${ARCH}-${OSNICK}:${REDIS_VER} UID=${UID}"

COPY platforms/setup.${OSNICK} /usr/local/bin/docker-setup
RUN chmod +x /usr/local/bin/docker-setup
RUN /usr/local/bin/docker-setup
RUN rm /usr/local/bin/docker-setup

# Add our user and group first to make sure their IDs get assigned consistently,
# regardless of whatever dependencies get added
RUN set -xe; \
    if [ -f /sbin/groupadd ] || [ -f /usr/sbin/groupadd ]; then \
        groupadd -r -g ${UID} redis && useradd -r -g redis -u ${UID} redis ;\
    else \
        addgroup --gid ${UID} redis && adduser --system --uid ${UID} redis ;\
    fi

COPY --from=builder /usr/local/ /usr/local/

RUN mkdir /data && chown redis:redis /data
VOLUME /data
WORKDIR /data

COPY ${REDIS_MAJOR}/docker-entrypoint.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
EXPOSE 6379
CMD ["redis-server"]

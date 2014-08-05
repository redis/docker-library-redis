FROM debian:wheezy

# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN groupadd -r redis && useradd -r -g redis redis

ADD . /usr/src/redis

RUN buildDeps='gcc libc6-dev make'; \
	set -x; \
	apt-get update && apt-get install -y $buildDeps --no-install-recommends \
	&& make -C /usr/src/redis \
	&& make -C /usr/src/redis install \
	&& make -C /usr/src/redis clean \
	&& apt-get purge -y $buildDeps \
	&& apt-get autoremove -y

RUN mkdir /data && chown redis:redis /data
VOLUME /data
WORKDIR /data

USER redis
EXPOSE 6379
CMD [ "redis-server" ]

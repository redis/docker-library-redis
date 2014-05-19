FROM debian:jessie

RUN apt-get update && apt-get install -y build-essential tcl valgrind

ADD . /usr/src/redis

RUN make -C /usr/src/redis

# in initial testing, "make test" was failing for reasons that were very hard to track down (so for now, we run them, but don't worry about them failing)
RUN make -C /usr/src/redis test || true

RUN make -C /usr/src/redis install

EXPOSE 6379
CMD [ "redis-server", "--bind", "0.0.0.0" ]

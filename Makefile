.NOTPARALLEL:

MAKEFLAGS += --no-builtin-rules  --no-print-directory

ifeq ($(NOP),1)
override NOP:=echo
endif

ifeq ($(filter help,$(MAKECMDGOALS)),help)
_HELP:=1

help:
	$(file >/tmp/help,$(HELPTEXT))
	@cat /tmp/help
	@rm -f /tmp/help
endif

#----------------------------------------------------------------------------------------------

STD_MAJORS=7 7.0 6.2 6.0 5.0

ifeq ($(VERSION),)
ifeq ($(VERSIONS),)
ifeq ($(STD_VERSIONS),)
STD_VERSIONS=1
endif
endif
endif

ifneq ($(_HELP),1)
ifeq ($(STD_VERSIONS),1)
override VERSIONS:=$(foreach V,$(STD_MAJORS),$(shell ./deps/readies/bin/github-lastver -r redis/redis -v $(V)))
override VERSIONS+=unstable
# $(info VERSIONS=$(VERSIONS))
endif
endif

ifneq ($(VERSIONS),)

ifeq ($(word 2,$(VERSIONS)),)
override VERSION:=$(VERSIONS)
override VERSIONS:=
else
VERSIONS += $(VERSION)
override VERSION:=
endif

else # ! VERSIONS

ifeq ($(patsubst 4%,4,$(VERSION)),4)
MAJOR=6.0
else ifeq ($(patsubst 5%,5,$(VERSION)),5)
MAJOR=5.0
else ifeq ($(patsubst 6.0%,6.0,$(VERSION)),6.0)
MAJOR=6.0
else ifeq ($(patsubst 6.2%,6.2,$(VERSION)),6.2)
MAJOR=6.2
else ifeq ($(patsubst 7.0%,7.0,$(VERSION)),7.0)
MAJOR=7.0
else ifeq ($(patsubst 7%,7,$(VERSION)),7)
MAJOR=7.2
else ifeq ($(VERSION),unstable)
MAJOR=unstable
else
ifneq ($(_HELP),1)
$(info Strange Redis version: $(VERSION))
endif
endif

endif

# LATEST=1
# MASTER=1

#----------------------------------------------------------------------------------------------

ARCH:=$(shell ./deps/readies/bin/platform --arch)
OSNICK ?= buster

#----------------------------------------------------------------------------------------------

include deps/readies/mk/osnick.defs

#----------------------------------------------------------------------------------------------

UID.centos7=997
UID.centos8.4=996
UID.centos8=996
UID.centos9=999
UID.ol7=995
UID.ol8=995
UID.alma8=996
UID.rocky8=994
UID.fedora=989
UID.rhel7.4=800
UID.alpine3=800
UID.alpine=800

ifeq ($(UID.$(OSNICK)),)
UID=999
else
UID=$(UID.$(OSNICK))
endif

#----------------------------------------------------------------------------------------------

REPO=redisfab
STEM=$(REPO)/redis

DOCKER ?= docker

BUILD_OPT=--rm --load --progress=plain
# --squash

ifeq ($(ARCH),arm64v8)
BUILD_OPT += --allow security.insecure
endif

ifeq ($(CACHE),0)
CACHE_ARG=--no-cache
endif

#----------------------------------------------------------------------------------------------

.PHONY: build publish

ifneq ($(VERSIONS),)

GOALS:=$(filter $(MAKECMDGOALS),build publish)

versions: $(foreach V,$(VERSIONS),version_$(V))

build: versions

publish: build

define make_version
version_$(1):
	@$(MAKE) VERSION=$(1) STD_VERSIONS="" VERSIONS="" $(GOALS)
.PHONY: version_$(1)
endef

$(foreach V,$(VERSIONS),$(eval $(call make_version,$(V))))

else # ! VERSIONS

ifneq ($(_HELP),1)
ifeq ($(VERSION),)
$(error VERSION not specified)
endif
endif

endif

#----------------------------------------------------------------------------------------------

ifneq ($(VERSION),)

#----------------------------------------------------------------------------------------------

build:
	@./deps/readies/bin/sep1
ifeq ($(ARCH),arm64v8)
	@$(NOP) $(DOCKER) buildx create --use --name insecure-builder --buildkitd-flags '--allow-insecure-entitlement security.insecure' || true
endif
	@echo "Building $(STEM):$(VERSION)-$(ARCH)-$(OSNICK) ..."
	@$(NOP) $(DOCKER) pull $(OS)
	@$(NOP) $(DOCKER) buildx build $(BUILD_OPT) -t $(STEM):$(VERSION)-$(ARCH)-$(OSNICK) -f $(MAJOR)/Dockerfile \
		$(CACHE_ARG) \
		--build-arg ARCH=$(ARCH) \
		--build-arg OS=$(OS) \
		--build-arg OSNICK=$(OSNICK) \
		--build-arg UID=$(UID) \
		--build-arg REDIS_VER=$(VERSION) \
		--build-arg REDIS_MAJOR=$(MAJOR) \
		.
ifneq ($(VERSION),unstable)
	@$(NOP) $(DOCKER) tag $(STEM):$(VERSION)-$(ARCH)-$(OSNICK) $(STEM):$(MAJOR)-latest-$(ARCH)-$(OSNICK)
endif

#----------------------------------------------------------------------------------------------

publish:
	@./deps/readies/bin/sep1
	@$(NOP) $(DOCKER) push $(STEM):$(VERSION)-$(ARCH)-$(OSNICK)
ifneq ($(VERSION),unstable)
	@$(NOP) $(DOCKER) push $(STEM):$(MAJOR)-latest-$(ARCH)-$(OSNICK)
endif

#----------------------------------------------------------------------------------------------

endif # VERSION

#----------------------------------------------------------------------------------------------

define HELPTEXT
make [build|publish] [OSNICK=<nick> | OS=<os>]
     [VERSION=<ver> | VERSIONS="<ver>..."]
     [STD_VERSIONS=1]

build    Build image(s)
publish  Push image(s) to Docker Hub

Arguments:
OSNICK=nick         nick=jammy|focal|bionic|xenial|bullseye|buster|rocky8|centos7|amzn2|fedora|alpine
OS=os               (optional) OS Docker image name (e.g., debian:buster-slim)
VERSION=ver         Redis version
VERSIONS="vers..."  Multiple Redis versions
STD_VERSIONS=1      Build latest versions of 6.0 and 6.2 branches
MASTER=1            Build sources from master branch ("edge" version)
LATEST=1            Build the latest version of branch given by VERSION
TEST=1              Run tests after build
CACHE=0             Build without cache

endef

#----------------------------------------------------------------------------------------------

.PHONY: all build publish help insecure-build

.NOTPARALLEL:

MAKEFLAGS += --no-builtin-rules  --no-print-directory

ifeq ($(NOP),1)
override NOP:=echo
endif

ifeq ($(filter help,$(MAKECMDGOALS)),help)
_HELP:=1

help:
	$(file >/tmp/help,$(HELP))
	@cat /tmp/help
	@rm -f /tmp/help
endif

#----------------------------------------------------------------------------------------------

STD_MAJORS=7.0 6.2 6.0 5.0

ifeq ($(VERSION),)
ifeq ($(VERSIONS),)
ifeq ($(STD_VERSIONS),)
STD_VERSIONS=1
endif
endif
endif

ifneq ($(filter help,$(MAKECMDGOALS)),help)
ifeq ($(STD_VERSIONS),1)
override VERSIONS:=$(foreach V,$(STD_MAJORS),$(shell ./deps/readies/bin/github-lastver -r redis/redis -v $(V)))
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
else ifeq ($(patsubst 7%,7,$(VERSION)),7)
MAJOR=7.0
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

ifeq ($(ARCH),x64)
#
else ifeq ($(CROSS),1)
$(error Cannot cross-build on ARM)
endif

#----------------------------------------------------------------------------------------------

OS ?= debian:buster-slim

# OSNICK=buster|stretch|trusty|xenial|bionic|centos6|centos7|centos8|fedora30
OSNICK ?= buster

OS.trusty=ubuntu:trusty
OS.xenial=ubuntu:xenial
OS.bionic=ubuntu:bionic
OS.jammy=ubuntu:jammy
OS.focal=ubuntu:focal
OS.hirsute=ubuntu:hirsute
OS.stretch=debian:stretch-slim
OS.buster=debian:buster-slim
OS.bullseye=debian:bullseye-slim
OS.centos6=centos:6
OS.centos7=centos:7
OS.centos8.4=centos:8.4
OS.centos8=quay.io/centos/centos:stream8
OS.centos9=quay.io/centos/centos:stream9
OS.ol7=oraclelinux:7
OS.ol8=oraclelinux:8
OS.alma8=almalinux:8
OS.rocky8=rockylinux:8
OS.fedora=fedora:latest
OS.fedora33=fedora:33
OS.fedora34=fedora:34
OS.fedora35=fedora:35
OS.alpine3=alpine:3
OS.alpineedge=alpine:edge
#OS.rawhide=fedora:latest
OS.rhel7.4=rhel:7.4
OS.alpine3=alpine:3
OS.alpineedge=alpine:edge
OS.jammy=ubuntu:jammy
OS=$(OS.$(OSNICK))

ifeq ($(OS),)
$(error Probably wrong OSNICK specified ($(OSNICK)))
endif

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
UID.fedora33=989
UID.fedora34=989
UID.fedora35=989
UID.rhel7.4=800
UID.alpine3=800
UID.alpineedge=800
ifeq ($(UID.$(OSNICK)),)
UID=999
else
UID=$(UID.$(OSNICK))
endif

#----------------------------------------------------------------------------------------------

REPO=redisfab
STEM=$(REPO)/redis

DOCKER ?= docker

BUILD_OPT=--rm
# --squash

ifeq ($(CACHE),0)
CACHE_ARG=--no-cache
endif

#----------------------------------------------------------------------------------------------

ifneq ($(CROSS),1)

define targets # (1=OP, 2=op)
$(1)_TARGETS :=
$(1)_TARGETS += $(2)_native
endef

else # cross

define targets # (1=OP, 2=op)
$(1)_TARGETS :=
$(1)_TARGETS += $(if $(findstring $(X64),1),$(2)_native)
$(1)_TARGETS += $(if $(findstring $(ARM7),1),$(2)_arm32v7)
$(1)_TARGETS += $(if $(findstring $(ARM8),1),$(2)_arm64v8)

$(1)_TARGETS += $$(if $$(strip $$($(1)_TARGETS)),,$(2)_arm32v7 $(2)_arm64v8)
endef

endif # cross

#----------------------------------------------------------------------------------------------

ifneq ($(VERSIONS),)

GOALS:=$(filter $(MAKECMDGOALS),build publish)

versions: $(foreach V,$(VERSIONS),version_$(V))

build: versions

publish: build

.PHONY: build publish

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

$(eval $(call targets,BUILD,build))
$(eval $(call targets,PUBLISH,publish))

endif

#----------------------------------------------------------------------------------------------

define build_native
build_native:
	@echo "Building $(STEM):$(VERSION)-$(ARCH)-$(OSNICK) ..."
	@$(NOP) $(DOCKER) pull $(OS)
	@$(NOP) $(DOCKER) build $(BUILD_OPT) -t $(STEM):$(VERSION)-$(ARCH)-$(OSNICK) -f $(MAJOR)/Dockerfile \
		$(CACHE_ARG) \
		--build-arg ARCH=$(ARCH) \
		--build-arg OS=$(OS) \
		--build-arg OSNICK=$(OSNICK) \
		--build-arg UID=$(UID) \
		--build-arg REDIS_VER=$(VERSION) \
		--build-arg REDIS_MAJOR=$(MAJOR) \
		.
	@$(NOP) $(DOCKER) tag $(STEM):$(VERSION)-$(ARCH)-$(OSNICK) $(STEM):$(MAJOR)-latest-$(ARCH)-$(OSNICK)

.PHONY: build_native
endef

define build_arm # (1=arch)
build_$(1):
	@echo "Building $(STEM):$(VERSION)-$(ARCH)-$(OSNICK) ..."
	@$(NOP) $(DOCKER) build $(BUILD_OPT) -t $(STEM)-xbuild:$(VERSION)-$(1)-$(OSNICK) -f $(MAJOR)/Dockerfile.arm \
		--build-arg ARCH=$(1) \
		--build-arg OSNICK=$(OSNICK) \
		--build-arg UID=$(UID) \
		--build-arg REDIS_VER=$(VERSION) \
		--build-arg REDIS_MAJOR=$(MAJOR) \
		.
	@$(NOP) $(DOCKER) tag $(STEM)-xbuild:$(VERSION)-$(1)-$(OSNICK) $(STEM)-xbuild:$(MAJOR)-latest-$(1)-$(OSNICK)

.PHONY: build_$(1)
endef

#----------------------------------------------------------------------------------------------

define publish_native
publish_native:
	@$(NOP) $(DOCKER) push $(STEM):$(VERSION)-$(ARCH)-$(OSNICK)
	@$(NOP) $(DOCKER) push $(STEM):$(MAJOR)-latest-$(ARCH)-$(OSNICK)

.PHONY: publish_native
endef

define publish_arm # (1=arch)
publish_$(1):
	@$(NOP) $(DOCKER) push $(STEM)-xbuild:$(VERSION)-$(1)-$(OSNICK)
	@$(NOP) $(DOCKER) push $(STEM)-xbuild:$(MAJOR)-latest-$(1)-$(OSNICK)

.PHONY: publish_$(1)
endef

#----------------------------------------------------------------------------------------------

build: $(BUILD_TARGETS)

$(eval $(call build_native))
ifeq ($(CROSS),1)
$(eval $(call build_arm,arm64v8))
$(eval $(call build_arm,arm32v7))
endif

publish: $(PUBLISH_TARGETS)

$(eval $(call publish_native))
ifeq ($(CROSS),1)
$(eval $(call publish_arm,arm64v8))
$(eval $(call publish_arm,arm32v7))
endif

#----------------------------------------------------------------------------------------------

define HELP
make [build|publish] [X64=1|ARM8=1|ARM7=1] [OSNICK=<nick> | OS=<os>]
     [VERSION=<ver> | VERSIONS="<ver>..."]
     [STD_VERSIONS=1]
     [CROSS=1]

build    Build image(s)
publish  Push image(s) to Docker Hub

Arguments:
OSNICK=nick         nick=buster|stretch|xenial|bionic|centos6|centos7|centos8|fedora30
OS=os               (optional) OS Docker image name (e.g., debian:buster-slim)
VERSION=ver         Redis version
VERSIONS="vers..."  Multiple Redis versions
STD_VERSIONS=1      Build latest versions of 6.0 and 6.2 branches
MASTER=1            Build sources from master branch ("edge" version)
LATEST=1            Build the latest version of branch given by VERSION
TEST=1              Run tests after build
CACHE=0             Build without cache
CROSS=1             Perform cross-platform builds (typically, ARM7/8 on x64)


endef

#----------------------------------------------------------------------------------------------

.PHONY: all build publish help

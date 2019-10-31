.NOTPARALLEL:

VERSION ?= 5.0.5

OS ?= debian:buster-slim

# OSNICK=buster|stretch|xenial|bionic|centos6|centos7|centos8|fedora30
OSNICK ?= buster

#----------------------------------------------------------------------------------------------

OS.xenial=ubuntu:xenial # 16
OS.bionic=ubuntu:bionic # 18
OS.stretch=debian:stretch-slim # 9
OS.buster=debian:buster-slim # 10
OS.centos6=centos:centos6
OS.centos7=centos:centos7
OS.centos8=centos:centos8
OS.fedora30=fedora:30
OS=$(OS.$(OSNICK))

REPO=redisfab
STEM=$(REPO)/redis

BUILD_OPT=--rm
# --squash

#----------------------------------------------------------------------------------------------

define targets # (1=OP, 2=op)
$(1)_TARGETS :=
$(1)_TARGETS += $(if $(findstring $(X64),1),$(2)_x64)
$(1)_TARGETS += $(if $(findstring $(ARM7),1),$(2)_arm32v7)
$(1)_TARGETS += $(if $(findstring $(ARM8),1),$(2)_arm64v8)

$(1)_TARGETS += $$(if $$(strip $$($(1)_TARGETS)),,$(2)_arm32v7 $(2)_arm64v8)
endef

$(eval $(call targets,BUILD,build))
$(eval $(call targets,PUBLISH,publish))

#----------------------------------------------------------------------------------------------

define build_x64
build_x64:
	@docker build $(BUILD_OPT) -t $(STEM)-x64-$(OSNICK):$(VERSION) -f 5.0/Dockerfile \
		--build-arg ARCH=x64 --build-arg OS=$(OS) --build-arg OSNICK=$(OSNICK) .
		
	@docker tag $(STEM)-x64-$(OSNICK):$(VERSION) $(STEM)-x64-$(OSNICK):latest

.PHONY: build_x64
endef

define build_arm # (1=arch)
build_$(1): 
	@docker build $(BUILD_OPT) -t $(STEM)-$(1)-$(OSNICK)-xbuild:$(VERSION) -f 5.0/Dockerfile.arm \
		--build-arg ARCH=$(1) --build-arg OSNICK=$(OSNICK) .
	@docker tag $(STEM)-$(1)-$(OSNICK)-xbuild:$(VERSION) $(STEM)-$(1)-$(OSNICK)-xbuild:latest

.PHONY: build_$(1)
endef

#----------------------------------------------------------------------------------------------

define publish_x64
publish_x64:
	@docker push $(STEM)-x64-$(OSNICK):$(VERSION)
	@docker push $(STEM)-x64-$(OSNICK):latest

.PHONY: publish_x64
endef

define publish_arm # (1=arch)
publish_$(1):
	@docker push $(STEM)-$(1)-$(OSNICK)-xbuild:$(VERSION)
	@docker push $(STEM)-$(1)-$(OSNICK)-xbuild:latest

.PHONY: publish_$(1)
endef

#----------------------------------------------------------------------------------------------

all: build publish

build: $(BUILD_TARGETS)

$(eval $(call build_x64))
$(eval $(call build_arm,arm64v8))
$(eval $(call build_arm,arm32v7))

publish: $(PUBLISH_TARGETS)

$(eval $(call publish_x64))
$(eval $(call publish_arm,arm64v8))
$(eval $(call publish_arm,arm32v7))

#----------------------------------------------------------------------------------------------

define HELP
make [X64=1|ARM8=1|ARM7=1] [OS=<os>] [OSNICK=<nick>] [VERSION=<ver>] [build|publish]

OS       OS Docker image name (e.g., debian:buster-slim)
OSNICK   buster|stretch|xenial|bionic|centos6|centos7|centos8|fedora30
VERSION  Redis version (e.g. 5.0.5)

build    Build image(s)
publish  Push image(s) to Docker Hub


endef

help:
	$(file >/tmp/help,$(HELP))
	@cat /tmp/help
	@rm -f /tmp/help

#----------------------------------------------------------------------------------------------

.PHONY: all build publish help

#	docker manifest create -a $(STEM)-$(OSNICK):$(VERSION) \
#		-a $(STEM)-x64-$(OSNICK):$(VERSION) \
#		-a $(STEM)-arm32v7-$(OSNICK)-xbuild:$(VERSION) \
#		-a $(STEM)-arm64v8-$(OSNICK)-xbuild:$(VERSION)
#	docker manifest annotate $(STEM)-$(OSNICK):$(VERSION) $(STEM)-arm32v7-$(OSNICK):$(VERSION) --os linux --arch arm
#	docker manifest annotate $(STEM)-$(OSNICK):$(VERSION) $(STEM)-arm64v8-$(OSNICK):$(VERSION) --os linux --arch arm64 --variant armv8
#	docker manifest push -p $(STEM)-$(OSNICK):$(VERSION)

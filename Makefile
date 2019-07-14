.NOTPARALLEL:

VERSION ?= 5.0.5
OSNICK ?= buster
REPO=redisfab
STEM=$(REPO)/redis

BUILD_OPT=--rm --squash

_X64=1
_ARM7=1
_ARM8=1
ifeq ($(X64),1)
_ARM7=
_ARM8=
endif
ifeq ($(ARM7),1)
_X64=
_ARM8=
endif
ifeq ($(ARM8),1)
_X64=
_ARM7=
endif

define build_x64
docker build $(BUILD_OPT) -t $(STEM)-x64-$(OSNICK):$(VERSION) -f 5.0/Dockerfile 5.0
docker tag $(STEM)-x64-$(OSNICK):$(VERSION) $(STEM)-x64-$(OSNICK):latest
endef

define build_arm # (1=arch)
docker build $(BUILD_OPT) -t $(STEM)-$(1)-$(OSNICK)-xbuild:$(VERSION) -f 5.0/Dockerfile.arm --build-arg ARCH=$(1) 5.0
docker tag $(STEM)-$(1)-$(OSNICK)-xbuild:$(VERSION) $(STEM)-$(1)-$(OSNICK)-xbuild:latest
endef

define push_x64
docker push $(STEM)-x64-$(OSNICK):$(VERSION)
docker push $(STEM)-x64-$(OSNICK):latest
endef

define push_arm
docker push $(STEM)-$(1)-$(OSNICK)-xbuild:$(VERSION)
docker push $(STEM)-$(1)-$(OSNICK)-xbuild:latest
endef

.PHONY: all build public

all: build

build:
ifeq ($(_X64),1)
	$(call build_x64)
endif
ifeq ($(_ARM7),1)
	$(call build_arm,arm32v7)
endif
ifeq ($(_ARM8),1)
	$(call build_arm,arm64v8)
endif

publish:
ifeq ($(_X64),1)
	$(call push_x64)
endif
ifeq ($(_ARM7),1)
	$(call push_arm,arm32v7)
endif
ifeq ($(_ARM8),1)
	$(call push_arm,arm64v8)
endif
#	docker manifest create -a $(STEM)-$(OSNICK):$(VERSION) \
#		-a $(STEM)-x64-$(OSNICK):$(VERSION) \
#		-a $(STEM)-arm32v7-$(OSNICK)-xbuild:$(VERSION) \
#		-a $(STEM)-arm64v8-$(OSNICK)-xbuild:$(VERSION)
#	docker manifest annotate $(STEM)-$(OSNICK):$(VERSION) $(STEM)-arm32v7-$(OSNICK):$(VERSION) --os linux --arch arm
#	docker manifest annotate $(STEM)-$(OSNICK):$(VERSION) $(STEM)-arm64v8-$(OSNICK):$(VERSION) --os linux --arch arm64 --variant armv8
#	docker manifest push -p $(STEM)-$(OSNICK):$(VERSION)

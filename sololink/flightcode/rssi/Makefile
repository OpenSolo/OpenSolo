# To cross compile:
#
# Set up as usual for bitbake:
# $ . setup-environment build
#
# In the build directory:
# $ bitbake meta-ide-support
# $ . tmp/environment-setup-cortexa9hf-vfp-neon-poky-linux-gnueabi
#
# Now a make in this directory should work.

VPATH = ../util

INCROOT = $(OECORE_TARGET_SYSROOT)/usr/include

INCS = -I../util

CXXFLAGS += -Wall -I$(INCROOT)/libnl3 $(INCS)

LDLIBS += -lnl-3 -lnl-genl-3

BIN = rssi_send

all: $(BIN)

$(BIN): rssi_send.o util.o
	$(LINK.cpp) -o $(BIN) rssi_send.o util.o $(LDLIBS)

clean:
	$(RM) *.o *~ $(BIN)

BASE := ../..

fmt:
	@python $(BASE)/tools/build/clang-format-run.py --apply

fmt-diff:
	@python $(BASE)/tools/build/clang-format-run.py

.PHONY: all clean fmt fmt-diff

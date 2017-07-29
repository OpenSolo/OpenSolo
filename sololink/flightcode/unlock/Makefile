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

INCS = -I../util

CFLAGS += -Wall $(INCS)
CXXFLAGS += -Wall $(INCS)

BIN = unlock

all: $(BIN)

$(BIN): unlock.o ButtonEventMessage.o RcLock.o file_util.o
	$(LINK.cpp) -o $(BIN) unlock.o ButtonEventMessage.o RcLock.o file_util.o

clean:
	$(RM) *.o *~ $(BIN)

BASE := ../..

fmt:
	@python $(BASE)/tools/build/clang-format-run.py --apply

fmt-diff:
	@python $(BASE)/tools/build/clang-format-run.py

.PHONY: all clean fmt fmt-diff

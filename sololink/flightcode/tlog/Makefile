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

VPATH = ../log ../util

INCS = -I../log -I../util

CFLAGS += -Wall $(INCS)
CXXFLAGS += -Wall $(INCS)

SRCS_CPP = tlog.cpp
SRCS_CPP += Log.cpp
SRCS_C += util.c

OBJS = $(SRCS_CPP:.cpp=.o) $(SRCS_C:.c=.o)

MAIN = tlog

all: $(MAIN)

$(MAIN): $(OBJS)
	$(LINK.cpp) -o $(MAIN) $(OBJS) 

clean:
	$(RM) *.o *~ $(MAIN)
	$(RM) ../log/*.o
	$(RM) ../util/*.o

BASE := ../..

fmt:
	@python $(BASE)/tools/build/clang-format-run.py --apply

fmt-diff:
	@python $(BASE)/tools/build/clang-format-run.py

.PHONY: all clean fmt fmt-diff

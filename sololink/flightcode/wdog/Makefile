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

CFLAGS += -Wall $(INCS)

SRCS_C = wdog.c

OBJS = $(SRCS_C:.c=.o)

MAIN = wdog

all: $(MAIN)

$(MAIN): $(OBJS)
	$(LINK.c) -o $(MAIN) $(OBJS)

clean:
	$(RM) *.o *~ $(MAIN)

BASE := ../..

fmt:
	@python $(BASE)/tools/build/clang-format-run.py --apply

fmt-diff:
	@python $(BASE)/tools/build/clang-format-run.py

.PHONY: all clean fmt fmt-diff

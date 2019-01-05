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

LIBS += -lpthread

SRCS_CPP = baudcheck.cpp
SRCS_C += util.c

OBJS = $(SRCS_CPP:.cpp=.o) $(SRCS_C:.c=.o)

MAIN = baudcheck

all: $(MAIN)

$(MAIN): $(OBJS)
	$(LINK.cpp) -o $(MAIN) $(OBJS) $(LIBS)

clean:
	$(RM) *.o *~ $(MAIN)
	$(RM) ../util/*.o

.PHONY: clean

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

CFLAGS += -Wall -g
CXXFLAGS += -Wall -g

LIBS = -lpthread

SRCS_CPP = Commander.cpp
#SRCS_CPP += ../ini/cpp/INIReader.cpp ../log/Log.cpp
#SRCS_C = ../ini/ini.c

OBJS = $(SRCS_CPP:.cpp=.o) $(SRCS_C:.c=.o)

MAIN = Commander

all: $(MAIN)

Commander.o: Commander.cpp Commander.h

$(MAIN): $(OBJS)
	$(LINK.cpp) -o $(MAIN) $(OBJS) $(LIBS)

clean:
	$(RM) *.o *~ $(MAIN)
	#$(RM) ../ini/*.o
	#$(RM) ../ini/cpp/*.o
	#$(RM) ../log/*.o

.PHONY: clean

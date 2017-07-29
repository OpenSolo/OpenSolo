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

VPATH = ../util ../ini ../ini/cpp

INCS = -I../util -I../ini -I../ini/cpp

CFLAGS += -Wall $(INCS)
CXXFLAGS += -Wall $(INCS) -std=c++11

SRCS_CPP = dataflash_logger.cpp
SRCS_CPP += common_tool.cpp
SRCS_CPP += format_reader.cpp
SRCS_CPP += telem_forwarder_client.cpp
SRCS_CPP += mavlink_reader.cpp
SRCS_CPP += analyzer_util.cpp
SRCS_CPP += dataflash_logger_program.cpp
SRCS_CPP += INIReader.cpp
SRCS_CPP += mavlink_message_handler.cpp
SRCS_CPP += mavlink_writer.cpp
SRCS_CPP += telem_client.cpp
SRCS_CPP += telem_serial.cpp
SRCS_CPP += la-log.cpp
SRCS_CPP += heart.cpp
SRCS_C = util.c ini.c

OBJS = $(SRCS_CPP:.cpp=.o) $(SRCS_C:.c=.o)
LIBS=-pthread

MAIN = dataflash_logger # actually, the main is in mavlink_reader...

all: $(MAIN)

$(MAIN): $(OBJS)
	$(LINK.cpp) -o $(MAIN) $(OBJS) $(LIBS)

clean:
	$(RM) *.o *~ $(MAIN)

BASE := ../..

fmt:
	@python $(BASE)/tools/build/clang-format-run.py --apply

fmt-diff:
	@python $(BASE)/tools/build/clang-format-run.py

.PHONY: clean

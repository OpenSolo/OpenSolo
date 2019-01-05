
CFLAGS += -Wall

syslog_test.o : CFLAGS += -Wno-format-security

syslog_test.o syslog.o : CFLAGS += -D SYSLOG_SOCK_NAME=\"/tmp/syslog_test\"
syslog_test.o syslog.o : CFLAGS += -D SYSLOG_MSG_MAX=64

CFLAGS += $(INCS)

SRCS_C = main.c \
util.c util_test.c \
syslog.c syslog_test.c

OBJS = $(SRCS_C:.c=.o)

MAIN = util_test

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

.PHONY: all clean fmt fmt-diff

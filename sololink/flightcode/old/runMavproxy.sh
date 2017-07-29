#!/bin/sh

# The goal is to use netcat to run MAVProxy as a server so we can connect to
# its console on a tcp port. This does not quite work; one can connect to the
# port from a remote host, but the input and/or output is getting buffered
# somewhere such that output does not show up until the connection is being
# closed, then it all comes at once.

# In any case, we don't want MAVProxy on the console tty when running from
# init, so this at least serves that purpose.

# mavproxy not starting up when run by netcat...
#nc -l -p 5020 -e 

mavproxy.py \
	--master=/dev/ttymxc1,57600 --rtscts \
	--out=10.1.1.1:14550

# XXX bogs down the telemetry stream
#	--load-module=solo \

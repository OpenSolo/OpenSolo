
import os
import subprocess

# udhcpc is normally started from busybox's ifup, with compiled-in parameters:
#     udhcpc -R -n -p /var/run/udhcpc.wlan0.pid -i wlan0
# If wlan0 does not associate on boot, udhcpc tries to get a lease, fails, and
# exits (because of the -n parameter).
#
# Busybox udhcpc:
#
# udhcpc [-Cfbnqtvo] [-c CID] [-V VCLS] [-H HOSTNAME] [-i INTERFACE]
#        [-p pidfile] [-r IP] [-s script] [-O dhcp-option] ...
#
# -V,--vendorclass=CLASSID    Vendor class identifier
# -i,--interface=INTERFACE    Interface to use (default eth0)
# -H,-h,--hostname=HOSTNAME   Client hostname
# -c,--clientid=CLIENTID      Client identifier
# -C,--clientid-none          Suppress default client identifier
# -p,--pidfile=file           Create pidfile
# -r,--request=IP             IP address to request
# -s,--script=file            Run file at DHCP events
#                             (default /usr/share/udhcpc/default.script)
# -t,--retries=N              Send up to N request packets
# -T,--timeout=N              Try to get a lease for N seconds (default 3)
# -A,--tryagain=N             Wait N seconds (default 20) after failure
# -O,--request-option=OPT     Request DHCP option OPT (cumulative)
# -o,--no-default-options     Do not request any options
#                             (unless -O is also given)
# -f,--foreground             Run in foreground
# -b,--background             Background if lease is not immediately obtained
# -S,--syslog                 Log to syslog too
# -n,--now                    Exit with failure if lease is not immediately
#                             obtained
# -q,--quit                   Quit after obtaining lease
# -R,--release                Release IP on quit
# -a,--arping                 Use arping to validate offered address


def start(ifname, hostname=None, retries=3):
    cmd = ["udhcpc", "-R", "-n",
           "-p", "/var/run/udhcpc." + ifname + ".pid",
           "-i", ifname]
    if hostname is not None:
        cmd.extend(["-x", "hostname:%s" % hostname])
    cmd.extend(["-T", "1",
                "-t", str(retries)])
    try:
        subprocess.check_output(cmd)
    except:
        pass


def stop():
    try:
        # stderr is redirected for this one to avoid error messages when
        # there is no udhcpc process running
        subprocess.check_output(["killall", "udhcpc"],
                                stderr=subprocess.STDOUT)
    except:
        pass


def pid(ifname):
    try:
        f = open("/var/run/udhcpc." + ifname + ".pid")
        pid = int(f.read())
        f.close()
        return pid
    except:
        return None


def get_lease(pid):
    try:
        subprocess.check_output(["kill", "-USR1", pid])
        return True
    except:
        return False


import re
import subprocess


def ip_mask(ifname):
    """get IP address and netmask for an interface if it has them

    The return is a tuple containing the address and netmask as strings. If
    either cannot be determined, None is returned in its place. If there is an
    error running the ifconfig command, None is returned instead of the tuple.

    Example:
      get_ip_mask("wlan0")
    normally returns something like:
      ("10.1.1.100", "255.255.255.0")
    but could return something like:
      ("10.1.1.100", None)
    """

    try:
        out = subprocess.check_output(["ifconfig", ifname])
    except:
        return None

    m = re.search("inet addr:([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", out)
    if not m:
        return None
    ip = m.group(1)

    m = re.search("Mask:([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", out)
    if not m:
        return None
    mask = m.group(1)

    return (ip, mask)


import os
import re


dhcp_lease_file = "/var/lib/misc/dnsmasq.leases"


def get_ip_mac(ip):
    """get MAC from IP

    ARP table is in /proc/net/arp:
    IP address  HW type  Flags  HW address         Mask  Device
    10.1.1.101  0x1      0x2    e8:2a:ea:50:5f:c8  *     wlan0-ap
    10.1.1.100  0x1      0x2    00:02:60:02:70:28  *     wlan0-ap

    Returns None if IP is not in arp table.
    """
    fn = "/proc/net/arp"
    try:
        f = open(fn)
    except:
        return None
    for line in f:
        m = re.match("([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).*?(\
[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F]:\
[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F])", line)
        if m:
            if m.group(1) == ip:
                return m.group(2)
    return None


def clear_dhcp_lease(client_mac):
    new_lease_file = dhcp_lease_file + ".new"
    os.system("grep -i -v %s %s > %s" % \
              (str(client_mac), dhcp_lease_file, new_lease_file))
    os.rename(new_lease_file, dhcp_lease_file)
    os.system("/etc/init.d/dnsmasq restart")

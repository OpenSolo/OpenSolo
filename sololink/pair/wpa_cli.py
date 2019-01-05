
import clock
import re
import subprocess

def run_cmd(ifname, cmd):
    """run a wpa_cli command, return the output"""
    cmd.insert(0, "wpa_cli")
    cmd.insert(1, "-i" + ifname)
    return subprocess.check_output(cmd)

def run_cmd_ok(ifname, cmd):
    """run a wpa_cli command that should return OK"""
    cmd.insert(0, "wpa_cli")
    cmd.insert(1, "-i" + ifname)
    out = subprocess.check_output(cmd)
    m = re.match("OK", out)
    if not m:
        raise RuntimeError

def run_cmd_int(ifname, cmd):
    """run a wpa_cli command that should return an integer"""
    cmd.insert(0, "wpa_cli")
    cmd.insert(1, "-i" + ifname)
    out = subprocess.check_output(cmd)
    m = re.match("([0-9]+)", out)
    if not m:
        raise RuntimeError
    # m.group(1) is still a string, e.g "2"
    return m.group(1)

def get_status(ifname):
    """get status from wpa_cli"""
    cmd = ["wpa_cli", "-i" + ifname, "status"]
    out = subprocess.check_output(cmd)
    out = out.splitlines()
    status = {}
    for line in out:
        m = re.match("(.+?)=(.+)", line)
        if not m:
            raise RuntimeError
        status[m.group(1)] = m.group(2)
    return status

# wpa_status polling, observed states:
# (times shown are one particular connection and may vary quite a bit)
#
# Initially:
#   wpa_state=DISCONNECTED
#   address=00:02:60:02:70:28
#
# After ~25 msec:
#   wpa_state=SCANNING
#   address=00:02:60:02:70:28
#
# After ~700 msec:
#   wpa_state=ASSOCIATING    
#   address=00:02:60:02:70:28
#
# After ~750 msec:
#   bssid=02:02:60:02:70:25  
#   ssid=SoloLink_090909     
#   id=0                     
#   mode=station             
#   pairwise_cipher=NONE     
#   group_cipher=NONE        
#   key_mgmt=NONE            
#   wpa_state=COMPLETED      
#   address=00:02:60:02:70:28
def poll_status(ifname, final_state, timeout=None, verbose=False):
    """poll status until it reaches a given state or timeout"""
    if timeout is not None:
        end_us = clock.gettime_us(clock.CLOCK_MONOTONIC) + (timeout * 1000000)
    else:
        end_us = None
    last_stat = {}
    while True:
        now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        stat = get_status(ifname)
        if verbose and stat != last_stat:
            print stat
            last_stat = stat
        if "wpa_state" in stat:
            new_state = stat["wpa_state"]
        else:
            new_state = ""
        if new_state == final_state:
            return True
        if end_us is not None and now_us > end_us:
            return False

def network_add(ifname, ssid):
    net_num = run_cmd_int(ifname, ["add_network"])
    run_cmd_ok(ifname, ["select_network", net_num])
    run_cmd_ok(ifname, ["enable_network", net_num])
    run_cmd_ok(ifname, ["set_network", net_num, "ssid", "\"" + ssid + "\""])
    run_cmd_ok(ifname, ["set_network", net_num, "key_mgmt", "NONE"])
    return net_num

def network_connect(ifname, timeout):
    run_cmd_ok(ifname, ["reassociate"])
    return poll_status(ifname, "COMPLETED", timeout)

def network_disconnect(ifname):
    run_cmd_ok(ifname, ["disconnect"])

def network_remove(ifname, net_num):
    run_cmd_ok(ifname, ["remove_network", net_num])

def network_remove_all(ifname):
    for net_num in range(10):
        run_cmd(ifname, ["remove_network", str(net_num)])

def save(ifname):
    run_cmd_ok(ifname, ["save_config"])

def set(ifname, variable, value):
    run_cmd_ok(ifname, ["set", variable, value])

def pin_pair(ifname, pin):
    return run_cmd(ifname, ["wps_pin", "any", str(pin)])

def reconfigure(ifname):
    return run_cmd(ifname, ["reconfigure"])

import datetime

def wps_logged():
    log = open("/log/wps.log", "a")
    pin_pair("wlan0", 74015887)
    last_stat = {}
    while True:  
        stat = get_status("wlan0")
        if stat != last_stat:
            log.write(str(datetime.datetime.now()))
            log.write(": ")
            log.write(str(stat))
            log.write("\n")
            last_stat = stat

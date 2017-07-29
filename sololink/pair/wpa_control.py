
import clock
import os
import socket
import time


class WpaControl:

    def __init__(self, ifname, verbose=False):
        # Arbitrary local socket name we bind to; this is needed because when
        # we send a command to the wpa_supplicant control socket, it sends the
        # reply back whence the request came.
        self.sockaddr_local = "/tmp/wpa_ctrl.%d" % (os.getpid(), )
        try:
            os.unlink(self.sockaddr_local)
        except:
            pass # it wasn't there, okay
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(self.sockaddr_local)
        # wpa_supplicant control socket. Connect to this to send commands to
        # and get responses from wpa_supplicant. If the network interface used
        # by wpa_supplicant changes, this must change. (It may be better to
        # just pick the first socket in the directory.)
        self.sockaddr_remote = "/var/run/wpa_supplicant/%s" % (ifname, )
        self.verbose = verbose

    def run_cmd(self, cmd):
        """run a command and return the output"""
        if self.verbose:
            start_us = clock.gettime_us(CLOCK_MONOTONIC)
        try:
            self.sock.sendto(cmd, self.sockaddr_remote)
        except:
            # control socket probably gone
            rsp = ""
        else:
            rsp = self.sock.recv(1024)
        if self.verbose:
            end_us = clock.gettime_us(CLOCK_MONOTONIC)
            print "command \"%s\", response \"%s\" in %0.3f sec" % \
                  (cmd, rsp, (end_us - start_us) / 1000000.0)
        return rsp

    def run_cmd_ok(self, cmd):
        """run a command that should return OK or FAIL"""
        rsp = self.run_cmd(cmd)
        rsp = rsp.strip()
        if rsp == "OK":
            return True
        if rsp == "FAIL":
            return False
        print "run_cmd_ok: rsp=\"%s\"" % (rsp, )
        raise RuntimeError

    def run_cmd_int(self, cmd):
        """run a command that should return an integer"""
        rsp = self.run_cmd(cmd)
        rsp = rsp.strip()
        # will either convert okay or raise exception
        return int(rsp)

    def get_status(self):
        """get status"""
        rsp = self.run_cmd("STATUS")
        rsp = rsp.splitlines()
        status = {}
        for line in rsp:
            line = line.strip()
            m = line.split("=", 1)
            if len(m) != 2:
                raise RuntimeError
            status[m[0]] = m[1]
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
    def poll_status(self, final_state, timeout=None, poll_delay=0.001):
        """poll status until it reaches a given state or timeout"""
        if timeout is not None:
            end_us = clock.gettime_us(clock.CLOCK_MONOTONIC) + (timeout * 1000000)
        else:
            end_us = None
        last_status = None
        verbose_orig = self.verbose
        self.verbose = False
        while True:
            status = self.get_status()
            now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
            if verbose_orig and status != last_status:
                print status
                last_status = status
            if "wpa_state" in status and status["wpa_state"] == final_state:
                self.verbose = verbose_orig
                return True
            if end_us is not None and now_us > end_us:
                self.verbose = verbose_orig
                return False
            # To get accurate timings (with verbose=True), this timeout should
            # be small (or zero). That leads to high CPU usage, so the default
            time.sleep(poll_delay)

    def network_add(self, ssid):
        net_num = self.run_cmd_int("ADD_NETWORK")
        self.run_cmd_ok("SELECT_NETWORK %d" % (net_num, ))
        self.run_cmd_ok("ENABLE_NETWORK %d" % (net_num, ))
        self.run_cmd_ok("SET_NETWORK %d ssid \"%s\"" % (net_num, ssid))
        self.run_cmd_ok("SET_NETWORK %d key_mgmt NONE" % (net_num, ))
        return net_num

    def network_connect(self, timeout):
        self.run_cmd_ok("REASSOCIATE")
        return self.poll_status("COMPLETED", timeout, poll_delay=0.1)

    def network_disconnect(self):
        self.run_cmd_ok("DISCONNECT")

    def network_remove(self, net_num):
        self.run_cmd_ok("REMOVE_NETWORK %d" % (net_num, ))

    def network_remove_all(self):
        for net_num in range(10):
            self.network_remove(net_num)

    def save(self):
        self.run_cmd_ok("SAVE_CONFIG")

    def set(self, variable, value):
        self.run_cmd_ok("SET %s %s" % (variable, str(value)))

    def pin_pair(self, pin):
        return self.run_cmd("WPS_PIN any %s" % (str(pin), ))

    def reconfigure(self):
        return self.run_cmd("RECONFIGURE")

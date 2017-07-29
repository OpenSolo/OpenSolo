
import subprocess

STANDBY = 3
READY = 4
MAINTENANCE = 5

def set(level):
    subprocess.check_output(["init", str(level)])

def get():
    r = subprocess.check_output(["runlevel"])
    r = r.split()
    return int(r[1])

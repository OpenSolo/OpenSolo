import os


def export(gpio):
    # is GPIO already exported?
    if os.path.isdir("/sys/class/gpio/gpio" + str(gpio)):
        return
    # no, export it
    f = open("/sys/class/gpio/export", "w")
    f.write(str(gpio))
    f.close()


def unexport(gpio):
    f = open("/sys/class/gpio/unexport", "w")
    f.write(str(gpio))
    f.close()


# set direction
# gpio is a string or integer (e.g. "21" or 21)
# direction is "in" or "out"
def set_dir(gpio, direction):
    filename = "/sys/class/gpio/gpio%s/direction" % str(gpio)
    try:
        f = open(filename, "w")
    except:
        print "error opening %s (need to export first?)" % filename
        return
    f.write(direction)
    f.close()


# set output value
# gpio is a string or integer (e.g. "21" or 21)
# value is a string or integer ("0", "1", 0, 1)
def set(gpio, value):
    filename = "/sys/class/gpio/gpio%s/value" % str(gpio)
    try:
        f = open(filename, "w")
    except:
        print "error opening %s (need to export first?)" % filename
        return
    try:
        f.write(str(value))
        f.close()
    except:
        print "error setting %s (is it an output?)" % filename

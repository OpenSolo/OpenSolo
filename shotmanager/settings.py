#
# This file handles reading/writing settings from shotmanager.conf
#
import os
import threading
import shotLogger
import ConfigParser
logger = shotLogger.logger

settingsLock = threading.Lock()

if 'SOLOLINK_SANDBOX' in os.environ:
    CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'sim/shotmanager.sandbox.conf')
    CONFIG_FILE_BACKUP = os.path.join(os.path.dirname(__file__), 'sim/shotmanager.back')
else:
    CONFIG_FILE = "/etc/shotmanager.conf"
    CONFIG_FILE_BACKUP = "/etc/shotmanager.back"


def writeSettingsThread(name, value):
    settingsLock.acquire()

    # write to the config file
    config = ConfigParser.SafeConfigParser()
    config.optionxform=str

    config.read(CONFIG_FILE)
    try:
        config.set("shotManager", name, value)
    except:
        logger.log("Failed to write setting")

    # back up the file
    os.system("cp %s %s" % (CONFIG_FILE, CONFIG_FILE_BACKUP))
    os.system("md5sum %s > %s.md5" % (CONFIG_FILE_BACKUP, CONFIG_FILE_BACKUP))
    os.system("sync")
    # modify config file and set md5
    with open(CONFIG_FILE, 'wb') as configfile:
        config.write(configfile)
    os.system("md5sum %s > %s.md5" % (CONFIG_FILE, CONFIG_FILE))
    os.system("sync")
    os.system("rm %s %s.md5" % (CONFIG_FILE_BACKUP, CONFIG_FILE_BACKUP))
    os.system("sync")

    logger.log("wrote setting: %s: %s"%(name, value))

    settingsLock.release()


# reads and returns setting of the given name
# perhaps we shouldn't read the file for each setting, but that's something we can address
# when we have more settings
def readSetting(name):
    # get our saved button mappings
    config = ConfigParser.SafeConfigParser()

    settingsLock.acquire()
    # if the config file is not found, an empty list is returned and the "get"
    # operations below fail
    config.read(CONFIG_FILE)
    settingsLock.release()

    try:
        return config.get("shotManager", name)
    except:
        logger.log("error reading %s"%(CONFIG_FILE,))
        raise
        return 0

# starts our thread which writes out our setting
# note both name and value should be strings
def writeSetting(name, value):
    thread = threading.Thread(name = "writeSettingsThread", target = writeSettingsThread, args = (name, value))
    thread.daemon = True
    thread.start()


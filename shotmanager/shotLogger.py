#!/usr/bin/env python

import os
import logging
import logging.config

class Logger():
    def __init__(self):
        if 'SOLOLINK_SANDBOX' in os.environ:
            logging.config.fileConfig(os.path.join(os.path.dirname(__file__), 'sim/shotmanager.sandbox.conf'))
        else:
            logging.config.fileConfig("/etc/shotmanager.conf")
        self.xlog = logging.getLogger("shot")

    def log(self, data):
        self.xlog.info(str(data).replace("\0", ""))

logger = Logger()

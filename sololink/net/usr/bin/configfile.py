#!/usr/bin/env python

# Get and set parameters in a configuration file (e.g. /etc/hostapd.conf)

import re
import os

# Assumptions (all derived from looking at a sample hostapd.conf file):
#
# A valid parameter name is [a-zA-Z0-9_]+
#
# A valid parameter value is everything after the '=' to the end of the line,
# whitespace trimmed on the ends. Can contain whitespace, ., :, etc. Can't
# handle a comment at the end of a setting; it will be taken as part of the
# setting.
#
# A "parameter setting" is:
# - optional [\t ]*
# - valid parameter name
# - optional [\t ]*
# - '='
# - valid parameter value
#
# A "commented out parameter setting" is:
# - optional [\t ]*
# - '#'
# - "parameter setting"

def paramGet(configFileName, paramName):
    '''
    Read parameter setting from config file
    '''
    configFile = open(configFileName) # IOError

    # process line-by-line
    for line in configFile:
        # re.match only works at beginning of line (we want that)
        m = re.match('[\t ]*' + paramName + '[\t ]*=[\t ]*(.*?)[\t ]*\n', line)
        if m:
            return m.group(1)

    # not found
    return None


def paramSet(configFileName, paramName, paramValue):
    '''
    Set parameter in config file
    '''

    configFileNameNew = configFileName + '.new'

    # We generally make two passes through the file:
    #
    # Pass 1:
    #     If we find the parameter getting set (uncommented), we delete that
    #     line and replace it with a new line with the new setting. Copy the
    #     rest of the file then return (do not do pass 2).
    #
    # Pass 2:
    #     Otherwise, find the first line with a setting for the parameter
    #     commented out. Insert a new line with the parameter setting, but
    #     leave the commented out setting. Copy the rest of the file then
    #     return. If the parameter is not found (commented out), append the
    #     setting at the end of the file.

    paramSet = False

    # pass 1: process line-by-line
    configFile = open(configFileName) # IOError
    configFileNew = open(configFileNameNew, 'w') # IOError
    for line in configFile:
        if not paramSet:
            # .match only works at beginning of line (we want that)
            # optional tabs/spaces, 'param=', setting
            m = re.match('[\t ]*' + paramName + '[\t ]*=[\t ]*(.*?)[\t ]*\n', line)
            if m:
                # found an uncommented setting for the parameter
                # replace  with the new setting
                line = paramName + '=' + str(paramValue) + '\n'
                paramSet = True
        configFileNew.write(line)
    configFileNew.close()
    configFile.close()

    # pass 1 done: if we set the parameter, then we are done.
    # If we did not set the parameter, do pass #2.
    if not paramSet:
        configFile = open(configFileName) # IOError
        configFileNew = open(configFileNameNew, 'w') # IOError
        for line in configFile:
            if not paramSet:
                # .match only works at beginning of line (we want that)
                # '#', optional tabs/spaces, 'param=', setting
                m = re.match('[\t ]*#[\t ]*' + paramName + '[\t ]*=[\t ]*(.*?)[\t ]*\n', line)
                if m:
                    # found a commented setting for the parameter
                    # insert a line with the new setting
                    configFileNew.write(paramName + '=' + str(paramValue) + '\n')
                    paramSet = True
            configFileNew.write(line)
        # append setting to end of file if not yet set
        if not paramSet:
            configFileNew.write(paramName + '=' + str(paramValue) + '\n')
            paramSet = True
        configFileNew.close()
        configFile.close()

    # replace old file with updated one
    os.rename(configFileNameNew, configFileName)

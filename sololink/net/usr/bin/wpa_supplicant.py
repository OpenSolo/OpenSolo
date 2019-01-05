#!/usr/bin/env python

# Provide read/write access to wpa_supplicant.conf as a python dictionary

# Comments are not preserved.
# A line starting with '#' as first non-whitespace is a comment.
# '#' after any non-whitespace is not special.
# Order is not preserved, except for the order of the network elements.
# The only ordered, compound-data element supported is the network list.
# No other elements may have { compound data }.
# Blobs are not supported.
# 'cred' is not supported.
# A network's opening { must be on the same line as the 'network' keyword.
# A network's closing } must be on a line by itself.
#
# A typical wpa_supplicant.conf dictionary might look as follows. Note that
# all keys are strings, and all values are lists of either strings or
# dictionaries. Storing the values as lists allows keeping them ordered; this
# is important for the network entries in the config file (order matters).
# Non-dictionary values are stored as lists simply because it keeps the
# structure more uniform, but also because there may be other config files
# this could work with where multiple entries are allowed.
#
# {
#     'ctrl_interface': ['/var/run/wpa_supplicant'],
#     'ctrl_interface_group': ['0'],
#     'manufacturer': ['3D Robotics'],
#     'model_name': ['Solo'],
#     'network': [
#         {
#             'auth_alg': ['OPEN'],
#             'key_mgmt': ['WPA-PSK'],
#             'pairwise': ['CCMP'],
#             'proto': ['RSN'],
#             'psk': ['"3drobotics2014"'],
#             'ssid': ['"SoloLink_Finley_Artoo"']
#         },
#         {
#             'auth_alg': ['OPEN'],
#             'key_mgmt': ['WPA-PSK'],
#             'pairwise': ['CCMP'],
#             'proto': ['RSN'],
#             'psk': ['"3drobotics2014"'],
#             'ssid': ['"SoloLink_Finley_Artoo"']
#         },
#         {
#             'auth_alg': ['OPEN'],
#             'key_mgmt': ['WPA-PSK'],
#             'pairwise': ['CCMP'],
#             'proto': ['RSN'],
#             'psk': ['"3drobotics2014"'],
#             'ssid': ['"SoloLink_Finley_Artoo"']
#         }
#     ],
#     'update_config': ['1']
# }
#
# The read() method populates this dictionary from a file. The write() method
# writes it to a file. Although the top-level order that items are written
# does not matter to wpa_supplicant, some ordering is allowed to make it a
# bit more maintainable. The list keyWriteOrder is a list of keys, defining
# the order they will be written to a file. When the dictionary is to be
# written, the code first goes through keyWriteOrder. For each entry therein,
# all entries from the dictionary with that key are written. After looping
# over keyWriteOrder, one more loop through the dictionary is done, and any
# keys found that are not in keyWriteOrder are written.


import re


# Internal: read lines from file, appending to supplied dictionary, until a
# closing brace is found or end of file is reached. If skip is True, then we
# are just reading until the closing brace or EOF is found, and ignoring the
# data.
def readDict(f, d, skip=False):

    while True:

        line = f.readline()
        #print [ hex(ord(c)) for c in line ]

        if len(line) == 0:
            # end of file, done
            break

        # closing brace, possibly with leading or trailing whitespace, done
        m = re.match('[\t ]*}[\t ]*$', line)
        if m:
            break

        if skip:
            # ignore everything else
            continue;

        # comment line, discard and continue
        m = re.match('[\t ]*#', line)
        if m:
            continue

        # blank line, or whitespace only, discard and continue
        m = re.match('[\t ]*$', line)
        if m:
            continue

        # Key is everything between the start of line and first '=', with
        # whitespace trimmed from the start and end. Value is everything after
        # the first '=' to the end of the line, also with whitespace trimmed
        # from the start and end. Note that both key and value can have
        # embedded whitespace, and the value can contain any character. There
        # must be at least one '=' in the line; that is what currently breaks
        # support for blobs.
        m = re.match('[\t ]*(.+?)[\t ]*=[\t ]*(.+)$', line)
        if m:
            key = m.group(1)
            val = m.group(2)

            if not key in d:
                # initialize key as empty list
                d[key] = []

            if val != '{':
                d[key].append(val)
            else:
                # starting a compound element, recurse
                # can't read blobs (fix that if needed)
                d2 = { }
                d[key].append(d2)
                m = re.match('blob-', key)
                if m:
                    # don't try to parse blob data
                    readDict(f, d2, True)
                else:
                    # read nested element as usual
                    readDict(f, d2)
        else:
            print 'Match fail:', [ hex(ord(c)) for c in line ]

    return d


# return dictionary with file contents
def read(fileName):
    fd = open(fileName) # IOError
    d = { }
    readDict(fd, d)
    return d


# When writing a dictionary, keys are written in this order. Any keys that are
# not in this list are written in an arbitrary order at the end.
keyWriteOrder = [
  'ctrl_interface',
  'ctrl_interface_group',
  'update_config',
  'manufacturer',
  'model_name',
  'network',
   # network element
  'ssid',
  'psk',
  'proto',
  'key_mgmt',
  'pairwise',
  'auth_alg'
]


# Internal: write one key to a file.
# Note that this recurses back into writeDict if the value is a dictionary.
def writeKey(fd, d, key, indent):
    val = d[key]
    # val is always a list. Each element in the list must be either a
    # string or a dictionary. If it is a string, print a line of the form
    # "key=val" to the file. If it is a dictionary, print a line of the
    # form "key={", then print the dictionary, then print a line with only
    # a closing brace "}".
    for v in val:
        if type(v) == str:
            fd.write(indent + key + '=' + str(v) + '\n')
        elif type(v) == dict:
            fd.write(indent + key + '={\n')
            writeDict(fd, v, indent + '    ')
            fd.write(indent + '}\n')
        else:
            fd.write(indent + '# Unknown data:\n')
            fd.write(indent + '# ' + key + '=' + str(val) + '\n')


# Internal: write dictionary to already-open file
def writeDict(fd, d, indent=''):
    # Go through keys keyWriteOrder[], printing any that are in dictonary
    for key in keyWriteOrder:
        if key in d:
            writeKey(fd, d, key, indent)
    # Go through keys in dictionary, printing any not in keyWriteOrder
    for key in d:
        if key not in keyWriteOrder:
            writeKey(fd, d, key, indent)


# write fileDict to fileName
def write(fileName, fileDict):
    fd = open(fileName, 'w') # IOError
    writeDict(fd, fileDict)


# Remove duplicate network entries from dictionary.
# Network entries are duplicates only if they are exactly the same.
def uniqueNetworks(d):
    if not 'network' in d:
        return
    nets = d['network']
    # This top-level loop is done repeatedly until no duplicates are found.
    # Each time a duplicate is found and deleted, we start over at the
    # beginning, to avoid having to worry about what the indices mean after an
    # item is deleted.
    while True:
        deleted = False
        for i in range(len(nets)):
            for j in range(len(nets)):
                if j == i:
                    continue;
                if nets[i] == nets[j]:
                    del(nets[j])
                    deleted = True
                    break # for j
            if deleted:
                break # for i
        # If nothing was deleted, we're done. If something was deleted, we
        # start over at the beginning.
        if not deleted:
            break


if __name__ == '__main__':
    import logging
    import logging.config
    from optparse import OptionParser
    import sys

    logging.config.fileConfig("/etc/sololink.conf")
    logger = logging.getLogger("net")

    logger.info("wpa_supplicant.py starting")

    parser = OptionParser('wpa_supplicant.py [options]')

    parser.add_option('-i', '--inFile', dest='inFile', type='string',
                      help='input file')

    parser.add_option('-o', '--outFile', dest='outFile', type='string',
                      help='output file')

    parser.add_option('-u', '--unique', dest='unique', action='store_true',
                      default=False,
                      help='remove duplicate network entries')

    (opts, args) = parser.parse_args()

    d = { }

    if opts.inFile is None:
        fin = sys.stdin
        logger.info("reading configuration from stdin")
    else:
        try:
            fin = open(opts.inFile)
            logger.info("reading configuration from \"%s\"", opts.inFile)
        except:
            logger.error("can't open \"%s\"", opts.inFile)
            sys.exit(1)

    if opts.outFile is None:
        fout = sys.stdout
        logger.info("writing configuration to stdout")
    else:
        try:
            fout = open(opts.outFile, 'w')
            logger.info("writing configuration to \"%s\"", opts.outFile)
        except:
            logger.error("can't open \"%s\"", opts.outFile)
            sys.exit(1)

    readDict(fin, d)

    if opts.unique:
        uniqueNetworks(d)

    writeDict(fout, d)

    logger.info("done")

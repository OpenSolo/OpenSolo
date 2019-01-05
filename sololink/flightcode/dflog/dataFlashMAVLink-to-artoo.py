#!/usr/bin/python

import subprocess
import time
import string
import os
import re

actually_sync_logs_to_artoo = False

class RecentLogLinker:
    '''RecentLogLinker manages links to the most recent logs.  These links are used by the app to retrieve the most recent logs
    '''
    def __init__(self, directory,link_dir):
        self.directory = directory #location of dataflashlogs
        self.symlink_directory = link_dir #loction of links to the dataflashlogs
        # if you reduce this number, you're going to have to ensure we
        # remove all old stale RECENT links somehow!
        self.num_recent_links_to_create = 10

    # directly copied from LogPruner
    def lognum(self, filename):
        base = filename.partition('.')
        return int(base[0])

    # directly copied from LogPruner
    def ordered_list_of_log_filepaths(self):
        binfiles_regex = re.compile("[0-9]+.BIN")
        files = [ f for f in os.listdir(self.directory) if (binfiles_regex.match(f) and os.path.isfile(os.path.join(self.directory, f))) ]
        files.sort(key=self.lognum)
        return [ os.path.join(self.directory, f)  for f in files ]

    def update_links(self):
        filepaths = self.ordered_list_of_log_filepaths()
        #print("Filepaths: " + str(filepaths))
        for i in range(0, self.num_recent_links_to_create):
            if len(filepaths) == 0:
                break
            source = filepaths.pop()
            if i == 0:
                link_name = "RECENT.BIN"
            else:
                link_name = "RECENT-{0}.BIN".format(i)

            link_path = os.path.join(self.symlink_directory, link_name)
            if os.path.exists(link_path):
                existing_source = None
                try:
                    existing_source = os.readlink(link_path)
                except OSError as e:
                    os.unlink(link_path)
                if existing_source is not None:
                    #print("Leaving link alone")
                    if existing_source == source:
                        continue
                    os.unlink(link_path)

            try:
                os.symlink(source, link_path)
            except OSError as e:
                print "Failed to link ({0} to {1}): {2}".format(source, link_path,  e.strerror)
                break

class LogPruner:
    '''LogPruner removes log files (e.g. 45.BIN) from the supplied
    directory until only the suppied number of logs remain.  Files are
    removed in ascending numerical order
    '''
    def __init__(self, directory, max_files_remaining):
        self.directory = directory
        self.max_files_remaining = max_files_remaining

    # directly copied to RecentLogLinker
    def lognum(self, filename):
        base = filename.partition('.')
        return int(base[0])

    # directly copied to RecentLogLinker
    def ordered_list_of_log_filepaths(self):
        binfiles_regex = re.compile("[0-9]+.BIN")
        files = [ f for f in os.listdir(self.directory) if (binfiles_regex.match(f) and os.path.isfile(os.path.join(self.directory, f))) ]
        files.sort(key=self.lognum)
        return [ os.path.join(self.directory, f)  for f in files ]

    def run(self):
        if not os.path.exists(self.directory):
            print("Directory does not exist: {0}".format(self.directory))
            return
        ordered_list = self.ordered_list_of_log_filepaths()
        while len(ordered_list) > self.max_files_remaining:
            to_remove = ordered_list.pop(0)
            try:
                os.unlink(to_remove)
            except IOError as e:
                print "Failed to remove ({0}): {1}".format(to_remove, e.strerror)
                break

class LogSyncer:
    '''
    an instance of LogSyncer loops over rsync'ing dataflash logs from
    the log data directory on solo onto Artoo
    '''
    def __init__(self, src, dest, ssh_id_path, rate=100):
        self.rsyncSrc = src
        self.rsyncDest = dest
        self.ssh_id_path = ssh_id_path
        self.rate = rate
        self.rsyncPartialDest = '.'.join((self.rsyncDest,'part'))
        if not os.path.exists(src):
            os.makedirs(src)

    def run(self):
        # quick sanity checks here.  --delete is a very, very big hammer
        if len(self.rsyncSrc) < 10:
            print("short rsync src")
            sys.exit(1)
        if len(self.rsyncDest) < 10:
            print("short rsync dest")
            sys.exit(1)

        recentloglinker = RecentLogLinker(src)

	while True:
            recentloglinker.update_links()

            cmd = [ 'ionice', '-c', '3', 'nice',
                "rsync", "-a", "--size-only", "--progress",
                '-e', 'ssh -o StrictHostKeyChecking=no -i "%s"' % self.ssh_id_path,
                "--partial",
                "--delete",
                '--bwlimit=%s' % (self.rate,),
                self.rsyncSrc, self.rsyncDest]
#            print "cmd: %s" % (' '.join(cmd))
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout,stderr = p.communicate()
            rc = p.returncode
            if rc != 0:
                print "stderr: (%s)" % stderr
                time.sleep(1);
                continue

#            print "stdout: (%s)" % stdout

            timeout = 10
            if string.find(stdout,"xfr") != -1:
                timeout = 1
            time.sleep(timeout);

# TODO: get artoo's address from config
# TODO: get source and dest addresses from config
src = "/log/dataflash/"
dest = "root@10.1.1.1:/log/solo/dataflash"
link_dir = "/log/" #location of symlinks for app to retrieve
ssh_id_path = "/home/root/.ssh/id_rsa-mav-df-xfer"
max_log_files=50

p = LogPruner(src, max_log_files)
p.run()

if actually_sync_logs_to_artoo:
    l = LogSyncer(src, dest, ssh_id_path)
    l.run()
else:
    # we still update the links on SoloLink so the app can fetch them
    recentloglinker = RecentLogLinker(src,link_dir)

    while True:
        recentloglinker.update_links()
        time.sleep(10);

# neither reached nor necessary if the LogSyncer runs
while True:
    time.sleep(86400)

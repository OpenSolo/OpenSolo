#!/usr/bin/python

import sys
import time
import pwd
import subprocess
import os, pwd, grp

def get_username():
    return pwd.getpwuid( os.getuid() )[ 0 ]

me = get_username()
if ( me != 'root' ) :
	print(" must be run as root, sorry, aborting. \n");
	exit(1);

# open logfile:
logfile = "/vagrant/progress.log"
log = open(logfile, "w+")


#  we display results as-it-happens, but also capture them
def run_command_capture_results(cmd='true', doLog=True): 
  if doLog:
  	print >>log, "cmd: "+cmd+"\n"
  print "cmd: "+cmd+"\n"
  p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,stdout=subprocess.PIPE)
  ret  = ''

  dobreak = False
  doNext = False
  while True:
    #print p.poll()

    #out = p.stdout.readline()
    out = p.stdout.read(1)
    # poll() returns None if process is still running, or exit code if it's done
    if out == "":
	if p.poll() is not None:
	  #print "OUT BREAK : " + str(p.poll())
	  dobreak = True
    # otherwise handle the data we got prom the process:	
    while out != '' and doNext == False:
	#if doNext == True:
	#	out = out + "\n"
	#	doNext = False
        sys.stdout.write(out)
	sys.stdout.flush()
	if doLog:
		log.write(out)
		log.flush()
	ret += out
	out = p.stdout.read(1)
	#if out == "\n":
	#	doNext = True

    #err = p.stderr.readline()
    err = p.stderr.read(1)
    if err == "":
	if p.poll() is not None:
	  #print "ERR BREAK" + str(p.poll())
	  dobreak = True
    while err != '' and doNext == False:
        #if doNext == True:
        #        out = out + "\n"
        #        doNext = False
        sys.stdout.write(err)
	sys.stdout.flush()
	if doLog:
		log.write(err)
		log.flush()
	ret += err
	err = p.stderr.read(1)
	#if err == "\n":
	#	doNext = True

    if dobreak == True:
	break
  return ret


def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    if os.getuid() != 0:
        # We're not root so, like, whatever dude
        return

    # Get the uid/gid from the name
    running_uid = pwd.getpwnam(uid_name).pw_uid
    running_gid = grp.getgrnam(gid_name).gr_gid

    # Remove group privileges
    os.setgroups([])

    # Try setting the new uid/gid
    os.setgid(running_gid)
    os.setuid(running_uid)

    # Ensure a very conservative umask
    old_umask = os.umask(002)

# tasks potentially needing root:

print >>log, "fixing perms\n";
print "fixing perms\n";
run_command_capture_results("chown -R vagrant /vagrant/.git /vagrant/.gitignore");
run_command_capture_results("chown -R vagrant /vagrant/*");

# now actually do ita:
#print >>log, "dropping privs to 'vagrant'\n";
drop_privileges('vagrant','vagrant');

me = get_username()
if ( me != 'vagrant' ) :
	print >>log, "error while trying to drop root and running as vagrant user, aborting. \n";
	exit(1);


run_command_capture_results("rm /vagrant/www/latest_run.txt", False);

#run_command_capture_results("touch /vagrant/www/in-progress.txt", False);
progress = open("/vagrant/www/in-progress.txt",'w+')


print >>log, "now running as 'vagrant' user.\nstarting run at:\n";
print "now running as 'vagrant' user.\nstarting run at:\n";
run_command_capture_results("date");


print >>log, "chdir /vagrant";
print "chdir /vagrant";
os.chdir("/vagrant");

run_command_capture_results("git pull");

# compare git rev with last-run, if changed, then we run again...
gitrev = run_command_capture_results("git rev-parse --verify HEAD");
touch = run_command_capture_results("touch /vagrant/gitrev.txt");
with open('gitrev.txt', 'r+') as f_in:
	prev = f_in.read()	
f_in.close()
# if they are different, make them the same.
if gitrev != prev:
  with open('gitrev.txt', 'w+') as f_out:
        f_out.write(gitrev)
  f_in.close()
# just let the human know the thing we are currently trying to do, by it's git hash..
progress.write(gitrev)

# if no change, then don't re-run
if gitrev == prev:
  print >>log, "no change in solo-builder git revision, not re-running. ( to force re-run, delete /vagrant/gitrev.txt file)";
  print "no change in solo-builder git revision, not re-running. ( to force re-run, delete /vagrant/gitrev.txt file)";

else:
  # run something.
  run_command_capture_results("echo \"y\" |/vagrant/builder.sh");

  print >>log, "finished run at:\n";
  run_command_capture_results("date");

  print "log closed. \n";
  log.close();

  print "log relocated. \n";

  comp = ''
  with open('/tmp/COMP.txt', 'r+') as f_in:
        comp = f_in.read()
  f_in.close()
  comp = comp.rstrip()
  if comp == '':
	print "log relocation aborted,cant find /tmp/COMP.txt";
	
  run_command_capture_results("mv /vagrant/progress.log /vagrant/binaries/"+comp+"/latest_run.txt", False);

# either way, wind up the files and handles:
progress.close()
run_command_capture_results("rm /vagrant/www/latest_run.txt", False);
run_command_capture_results("mv /vagrant/www/in-progress.txt /vagrant/www/latest_run.txt", False);



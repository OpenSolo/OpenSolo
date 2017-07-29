#!/usr/bin/env python

import os, sys, subprocess

extensions = (
    ".cpp", ".cxx", ".c++", ".cc", ".cp",
    ".c",".i", ".ii", ".h", ".h++", ".hpp",
    ".hxx", ".hh", ".inl", ".inc", ".ipp",
    ".ixx", ".txx", ".tpp", ".tcc", ".tpl"
)

def find_clang_format(options):
    for c in options:
        try:
            v = subprocess.check_output([c, "--version"])
            return c, v.strip()
        except:
            pass
    print "can't find clang-format in %s" % str(clang_format_list)
    sys.exit(1)

# find the installed version of clang-format - we require at least 3.6
clang_format_list = ("clang-format-3.6", "clang-format-3.7", "clang-format")
clang_format, cf_version = find_clang_format(clang_format_list)

# report differences unless "--apply" is given as argument
do_apply = (len(sys.argv) >= 2) and (sys.argv[1] == "--apply")

diff_files = []

for root, dirs, files in os.walk("."):
    if 'build' in dirs:
        dirs.remove('build')
    if 'install' in dirs:
        dirs.remove('install')
    for file in files:
        if file.endswith(extensions):
            fpath = os.path.join(root, file)
            if do_apply:
                subprocess.check_call([clang_format, "-i", "-style=file", fpath], stdout=subprocess.PIPE)
            else:
                # compare the output of clang-format with the current file, complain if there's a diff
                p1 = subprocess.Popen([clang_format, "-style=file", fpath], stdout=subprocess.PIPE)
                p2 = subprocess.Popen(["diff", "-u", fpath, "-"], stdin=p1.stdout, stdout=subprocess.PIPE)
                if p2.wait() != 0:
                    diff_files.append(fpath)

if len(diff_files) != 0:
    print cf_version, "reported differences for the following files:"
    for f in diff_files:
        print "    ", f
    sys.exit(1)

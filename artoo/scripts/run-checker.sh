#!/bin/sh

#
# run http://clang-analyzer.llvm.org for static code analysis
#

# adjust this for your system...
CHECKER_PATH=~/Downloads/checker-276

# tup will complain if generated files (.o, build results, etc) are already there
git clean -fX

# scan-build interposing appears not to work with normal tup invocation,
# use the non-fuse-ified approach
tup generate tup-once.sh
${CHECKER_PATH}/scan-build sh tup-once.sh
rm tup-once.sh

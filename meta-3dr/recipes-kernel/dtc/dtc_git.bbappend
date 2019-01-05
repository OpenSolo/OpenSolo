
# Without this change, the observed behavior is:
# - bitbake tries to clone dtc from jdl.com and fails
# - bitbake gets a dtc tarball from a mirror (succeeds)
# - bitbake bails out because of the failure-to-clone
# - another run of bitbake works
# This makes it so it never tries jdl.com (which is often down).

SRC_URI_remove = "git://www.jdl.com/software/dtc.git"
SRC_URI_prepend = "git://git.kernel.org/pub/scm/utils/dtc/dtc.git "

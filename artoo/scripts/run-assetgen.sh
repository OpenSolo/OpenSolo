#!/bin/sh

#
# run just the assetgen step, as a way to test asset config
# locally, before committing.
#
# intended to be run from the project's top level directory.
# should match the invocation in the Tupfile.
#

python tools/assetgen.py resources/assets.cfg src --show-stats

echo assetgen complete

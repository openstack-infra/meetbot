# Richard Darst, 2009

import os
import sys

run_tests = True
os.chdir(os.path.join(os.path.dirname(__file__), '.'))

print sys.path
sys.path.insert(0, "..")

sys.argv[1:] = ["replay", "test-script-1.log.txt"]
execfile("../meeting.py")

del sys.path[0]


# Supybot-based tests

os.symlink("..", "MeetBot")
try:
    sys.argv[1:] = ["./MeetBot"]
    execfile("/usr/bin/supybot-test")
finally:
    os.unlink("MeetBot")



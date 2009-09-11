# Richard Darst, 2009

import os
import sys
import unittest

running_tests = True

class MeetBotTest(unittest.TestCase):

    def test_replay(self):
        """Replay of a meeting, using __meeting__.
        """
        sys.argv[1:] = ["replay", "test-script-1.log.txt"]
        sys.path.insert(0, "..")
        try:
            execfile("../meeting.py", globals())
        finally:
            del sys.path[0]

    def test_supybottests(self):
        """Test by sending input to supybot, check responses.

        Uses the external supybot-test command.  Unfortunantly, that
        doesn't have a useful status code, so I need to parse the
        output.
        """
        os.symlink("..", "MeetBot")
        try:
            output = os.popen("supybot-test ./MeetBot 2>&1").read()
            print output
            assert 'FAILED' not in output, "supybot-based tests failed."
        finally:
            os.unlink("MeetBot")



if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(__file__), '.'))
    unittest.main()










# Richard Darst, 2009

import os
import sys
import tempfile
import unittest

import meeting

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

    trivial_contents = """
    10:10:10 <x> #startmeeting
    10:10:10 <x> blah
    10:10:10 <x> #endmeeting
    """

    def M_trivial(self, extraConfig={}):
        return meeting.process_meeting(contents=self.trivial_contents,
                                       channel="#none",
                                       filename='/dev/null',
                                       dontSave=True,
                                       extraConfig=extraConfig,
                                       safeMode=False)

    def t_css(self):
        self.test_css_embed()
        self.test_css_noembed()
        self.test_css_file_embed()
        self.test_css_file()
        self.test_css_none()
    def test_css_embed(self):
        extraConfig={ }
        results = self.M_trivial(extraConfig={}).save()
        self.assert_('<link rel="stylesheet" ' not in results['.html'])
        self.assert_('body {'                      in results['.html'])
        self.assert_('<link rel="stylesheet" ' not in results['.log.html'])
        self.assert_('body {'                      in results['.log.html'])
    def test_css_noembed(self):
        extraConfig={'cssEmbed_minutes':False,
                     'cssEmbed_log':False,}
        M = self.M_trivial(extraConfig=extraConfig)
        results = M.save()
        self.assert_('<link rel="stylesheet" '     in results['.html'])
        self.assert_('body {'                  not in results['.html'])
        self.assert_('<link rel="stylesheet" '     in results['.log.html'])
        self.assert_('body {'                  not in results['.log.html'])
    def test_css_file(self):
        tmpf = tempfile.NamedTemporaryFile()
        magic_string = '546uorck6o45tuo6'
        tmpf.write(magic_string)
        tmpf.flush()
        extraConfig={'cssFile_minutes':  tmpf.name,
                     'cssFile_log':      tmpf.name,}
        M = self.M_trivial(extraConfig=extraConfig)
        results = M.save()
        self.assert_('<link rel="stylesheet" ' not in results['.html'])
        self.assert_(magic_string                  in results['.html'])
        self.assert_('<link rel="stylesheet" ' not in results['.log.html'])
        self.assert_(magic_string                  in results['.log.html'])
    def test_css_file_embed(self):
        tmpf = tempfile.NamedTemporaryFile()
        magic_string = '546uorck6o45tuo6'
        tmpf.write(magic_string)
        tmpf.flush()
        extraConfig={'cssFile_minutes':  tmpf.name,
                     'cssFile_log':      tmpf.name,
                     'cssEmbed_minutes': False,
                     'cssEmbed_log':     False,}
        M = self.M_trivial(extraConfig=extraConfig)
        results = M.save()
        self.assert_('<link rel="stylesheet" '     in results['.html'])
        self.assert_(tmpf.name                     in results['.html'])
        self.assert_('<link rel="stylesheet" '     in results['.log.html'])
        self.assert_(tmpf.name                     in results['.log.html'])
    def test_css_none(self):
        tmpf = tempfile.NamedTemporaryFile()
        magic_string = '546uorck6o45tuo6'
        tmpf.write(magic_string)
        tmpf.flush()
        extraConfig={'cssFile_minutes':  'none',
                     'cssFile_log':      'none',}
        M = self.M_trivial(extraConfig=extraConfig)
        results = M.save()
        self.assert_('<link rel="stylesheet" ' not in results['.html'])
        self.assert_('<style type="text/css" ' not in results['.html'])
        self.assert_('<link rel="stylesheet" ' not in results['.log.html'])
        self.assert_('<style type="text/css" ' not in results['.log.html'])



if __name__ == '__main__':
    if len(sys.argv) <= 1:
        os.chdir(os.path.join(os.path.dirname(__file__), '.'))
        unittest.main()
    else:
        for testname in sys.argv[1:]:
            print testname
            if hasattr(MeetBotTest, testname):
                MeetBotTest(methodName=testname).debug()
            else:
                MeetBotTest(methodName='test_'+testname).debug()


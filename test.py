###
# Copyright (c) 2009, Richard Darst
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

import os
import sys

class MeetBotTestCase(ChannelPluginTestCase):
    channel = "#testchannel"
    plugins = ('MeetBot',)

    def testRunMeeting(self):
        test_script = file(os.path.join(os.path.dirname(__file__),
                                        "tests/test-script-2.log.txt"))
        for line in test_script:
            # Normalize input lines somewhat.
            line = line.strip()
            if not line: continue
            # This consists of input/output pairs we expect.  If it's
            # not here, it's not checked for.
            match_pairs = (('#startmeeting', 'Meeting started'),
                           ('#endmeeting', 'Meeting ended'),
                           ('#topic (.*)', 1),
                           ('#meetingtopic (.*)', 1),
                           ('#meetingname','The meeting name has been set to'),
                           ('#chair', 'Current chairs:'),
                           ('#unchair', 'Current chairs:'),
                           )
            # Run the command and get any possible output
            reply = [ ]
            self.feedMsg(line)
            r = self.irc.takeMsg()
            while r:
                reply.append(r.args[1])
                r = self.irc.takeMsg()
            reply = "\n".join(reply)
            # If our input line matches a test pattern, then insist
            # that the output line matches the expected output
            # pattern.
            for test in match_pairs:
                if re.search(test[0], line):
                    groups = re.search(test[0], line).groups()
                    # Output pattern depends on input pattern
                    if isinstance(test[1], int):
                        assert re.search(re.escape(groups[test[1]-1]),
                                             reply), 'line "%s" gives output "%s"'%(line, reply)
                    # Just match the given pattern.
                    else:
                        assert re.search(test[1], reply), 'line "%s" gives output "%s"'%(line, reply)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

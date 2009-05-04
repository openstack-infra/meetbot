# Richard Darst, May 2009

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

import time
import os
import re
import stat

import pygments

#
# Throw any overrides into meetingLocalConfig.py in this directory:
#
# Where to store files on disk
logFileDir = '/home/richard/meatbot/'
# The links to the logfiles are given this prefix
logUrlPrefix = 'http://rkd.zgib.net/meatbot/'
# Where to say to go for more information about MeatBot
MeetBotInfoURL = 'http://wiki.debian.org/MeatBot'
# This is used with the #restrict command to remove permissions from files.
RestrictPerm = stat.S_IRWXO|stat.S_IRWXG  # g,o perm zeroed
# RestrictPerm = stat.S_IRWXU|stat.S_IRWXO|stat.S_IRWXG  # u,g,o perm zeroed.
# used to detect #link :
UrlProtocols = ('http:', 'https:', 'irc:', 'ftp:', 'mailto:', 'ssh:')
# regular expression for parsing commands
command_RE = re.compile('#([\w]+)(?:[ \t]*(.*))?')
# This is the help printed when a meeting starts
usefulCommands = "#action #agreed #halp #info #idea #link #topic"
# The channels which won't have date/time appended to the filename.
testChannels = ("#meatbot-test", )

# load custom local configurations
try:
    from meetingLocalConfig import *
except ImportError:
    pass

def html(text):
    """Escape bad sequences (in HTML) in user-generated lines."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class MeetingCommands(object):
    # Command Definitions
    # generic parameters to these functions:
    #  nick=
    #  line=    <the payload of the line>
    #  linenum= <the line number, 1-based index (for logfile)>
    #  time_=   <time it was said>
    # Commands for Chairs:
    def do_startmeeting(self, nick, time_, **kwargs):
        """Begin a meeting."""
        self.reply("Meeting started %s UTC.  The chair is %s."%\
                   (time.asctime(time_), self.owner))
        self.reply(("Information about MeatBot at %s , Useful Commands: %s.")%\
                   (MeetBotInfoURL, usefulCommands))
        self.starttime = time_
    def do_endmeeting(self, nick, time_, **kwargs):
        """End the meeting."""
        if not self.isChair(nick): return
        self.endtime = time_
        self.save()
        self.reply("Meeting ended %s UTC.  Information about MeatBot at %s ."%\
                   (time.asctime(time_),MeetBotInfoURL))
        self.reply("Minutes: "+self.minutesFilename(url=True))
        self.reply("Log:     "+self.logFilename(url=True))
        if hasattr(self, 'oldtopic'):
            self.topic(self.oldtopic)
    def do_topic(self, nick, line, **kwargs):
        """Set a new topic in the channel."""
        if not self.isChair(nick): return
        m = Topic(nick=nick, line=line, **kwargs)
        self.minutes.append(m)
        self.topic(line)
    def do_save(self, nick, time_, **kwargs):
        """Add a chair to the meeting."""
        if not self.isChair(nick): return
        self.endtime = time_
        self.save()
    def do_agreed(self, nick, **kwargs):
        """Add aggreement to the minutes - chairs only."""
        if not self.isChair(nick): return
        m = Agreed(nick, **kwargs)
        self.minutes.append(m)
    do_agree = do_agreed
    def do_chair(self, nick, line, **kwargs):
        """Add a chair to the meeting."""
        if not self.isChair(nick): return
        for chair in line.strip().split():
            self.addnick(chair, lines=0)
            self.chairs.setdefault(chair.strip(), True)
            self.reply("Chair added: %s"%chair)
    def do_unchair(self, nick, line, **kwargs):
        """Remove a chair to the meeting (founder can not be removed)."""
        if not self.isChair(nick): return
        for chair in line.strip().split():
            if self.chairs.has_key(chair.strip()):
                del self.chairs[chair]
                self.reply("Chair removed: %s"%chair)
    def do_undo(self, nick, **kwargs):
        """Remove the last item from the minutes."""
        if not self.isChair(nick): return
        if len(self.minutes) == 0: return
        self.reply("Removing item from minutes: %s"%str(self.minutes[-1]))
        del self.minutes[-1]
    def do_restrictlogs(self, nick, **kwargs):
        """When saved, remove permissions from the files."""
        if not self.isChair(nick): return
        self._restrictlogs = True
        self.reply("Restricting permissions on minutes: -%s on next #save"%\
                   oct(RestrictPerm))
    def do_lurk(self, nick, **kwargs):
        """Don't interact in the channel."""
        if not self.isChair(nick): return
        self._lurk = True
    def do_unlurk(self, nick, **kwargs):
        """Do interact in the channel."""
        if not self.isChair(nick): return
        self._lurk = False
    # Commands for Anyone:
    def do_action(self, **kwargs):
        """Add action item to the minutes.

        The line is searched for nicks, and a per-person action item
        list is compiled after the meeting.  Only nicks which have
        been seen during the meeting will have an action item list
        made for them, but you can use the #nick command to cause a
        nick to be seen."""
        m = Action(**kwargs)
        self.minutes.append(m)
    def do_info(self, **kwargs):
        """Add informational item to the minutes."""
        m = Info(**kwargs)
        self.minutes.append(m)
    def do_idea(self, **kwargs):
        """Add informational item to the minutes."""
        m = Idea(**kwargs)
        self.minutes.append(m)
    def do_halp(self, **kwargs):
        """Add call for halp to the minutes."""
        m = Halp(**kwargs)
        self.minutes.append(m)
    do_help = do_halp
    def do_nick(self, nick, line, **kwargs):
        """Make meetbot aware of a nick which hasn't said anything.

        To see where this can be used, see #action command"""
        nicks = line.strip().split()
        for nick in nicks:
            self.addnick(nick, lines=0)
    def do_link(self, **kwargs):
        """Add informational item to the minutes."""
        m = Link(**kwargs)
        self.minutes.append(m)
    def do_commands(self, **kwargs):
        commands = [ "#"+x[3:] for x in dir(self) if x[:3]=="do_" ]
        commands.sort()
        self.reply("Available commands: "+(" ".join(commands)))
            




class Meeting(MeetingCommands, object):
    _lurk = False
    _restrictlogs = False
    def __init__(self, channel, owner, oldtopic=None,
                 filename=None, writeRawLog=True):
        self.owner = owner
        self.channel = channel
        self.oldtopic = oldtopic
        self.lines = [ ]
        self.minutes = [ ]
        self.attendees = { }
        self.chairs = {owner:True}
        self._writeRawLog = writeRawLog
        if filename is not None:
            self.filename = filename
        elif channel in testChannels:
            self.filename = channel.strip('# ')
        else:
            self.filename = channel.strip('# ') + \
                            time.strftime('-%Y-%m-%d-%H.%M', time.gmtime())

    # These commands are callbacks to manipulate the IRC protocol.
    # set self._sendReply and self._setTopic to an callback to do these things.
    def reply(self, x):
        """Send a reply to the IRC channel."""
        if hasattr(self, '_sendReply') and not self._lurk:
            self._sendReply(x)
        else:
            print "REPLY:", x
    def topic(self, x):
        """Set the topic in the IRC channel."""
        if hasattr(self, '_setTopic') and not self._lurk:
            self._setTopic(x)
        else:
            print "TOPIC:", x
    def addnick(self, nick, lines=1):
        """This person has spoken, lines=<how many lines>"""
        self.attendees[nick] = self.attendees.get(nick, 0) + lines
    def isChair(self, nick):
        """Is the nick a chair?"""
        return (nick == self.owner or self.chairs.has_key(nick))
    # Primary enttry point for new lines in the log:
    def addline(self, nick, line, time_=None):
        """This is the way to add lines to the Meeting object.
        """
        self.addnick(nick)
        line = line.strip(' \x01') # \x01 is present in ACTIONs
        # Setting a custom time is useful when replying logs,
        # otherwise use our current time:
        if time_ is None: time_ = time.gmtime()
        
        # Handle the logging of the line
        if line[:6] == 'ACTION':
            logline = "%s * %s %s"%(time.strftime("%H:%M:%S", time_),
                                 nick, line[7:].strip())
        else:
            logline = "%s <%s> %s"%(time.strftime("%H:%M:%S", time_),
                                 nick, line.strip())
        self.lines.append(logline)
        linenum = len(self.lines)

        # Handle any commands given in the line.
        matchobj = command_RE.match(line)
        if matchobj is not None:
            command, line = matchobj.groups()
            command = command.lower()
            # to define new commands, define a method do_commandname .
            if hasattr(self, "do_"+command):
                getattr(self, "do_"+command)(nick=nick, line=line,
                                             linenum=linenum, time_=time_)
        else:
            # Detect URLs automatically
            if line.split('//')[0] in UrlProtocols:
                self.do_link(nick=nick, line=line,
                             linenum=linenum, time_=time_)

        
    def save(self):
        """Write all output files."""
        if self._writeRawLog:
            self.writeRawLog()
        self.writeLogs()
        self.writeMinutes()
    def writeLogs(self):
        """Write pretty HTML logs."""
        # pygments lexing setup:
        # (pygments HTML-formatter handles HTML-escaping)
        from pygments.lexers import IrcLogsLexer
        from pygments.formatters import HtmlFormatter
        formatter = HtmlFormatter(encoding='utf-8', lineanchors='l',
                                  full=True)
        lexer = IrcLogsLexer(encoding='utf-8')
        out = pygments.highlight("\n".join(self.lines), lexer, formatter)
        # Do the writing...
        f = file(self.logFilename(), 'w')
        # We might want to restrict read-permissions of the files from
        # the webserver.
        if self._restrictlogs:
            self.restrictPermissions(f)
        f.write(out)
    def writeMinutes(self):
        """Write the minutes summary."""
        f = file(self.minutesFilename(), 'w')
        # We might want to restrict read-permissions of the files from
        # the webserver.
        if self._restrictlogs:
            self.restrictPermissions(f)


        # Header and things stored
        print >> f, \
        '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        <html>
        <head>
        <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
        <title>%s Meeting Minutes</title>
        </head>
        <body>
        Meeting started by %s at %s UTC.  (<a href="%s">full logs</a>)<br>
        \n\n<table border=1>'''%(self.channel, self.owner,
                             time.strftime("%H:%M:%S", self.starttime),
                             os.path.basename(self.logFilename()))
        # Add all minute items to the table
        for m in self.minutes:
            print >> f, m.html(self)
        # End the log portion
        print >> f, """</table>
        Meeting ended at %s UTC.  (<a href="%s">full logs</a>)"""%\
            (time.strftime("%H:%M:%S", self.endtime),
             os.path.basename(self.logFilename()))
        print >> f, "\n<br><br><br>"


        # Action Items
        print >> f, "<b>Action Items</b><ol>"
        import meeting
        for m in self.minutes:
            # The hack below is needed because of pickling problems
            if not isinstance(m, (Action, meeting.Action)): continue
            print >> f, "  <li>%s</li>"%html(m.line)
        print >> f, "</ol>\n\n<br>"
        

        # Action Items, by person (This could be made lots more efficient)
        print >> f, "<b>Action Items, by person</b>\n<ol>"
        for nick in sorted(self.attendees.keys(), key=lambda x: x.lower()):
            headerPrinted = False
            for m in self.minutes:
                # The hack below is needed because of pickling problems
                if not isinstance(m, (Action, meeting.Action)): continue
                if m.line.find(nick) == -1: continue
                if not headerPrinted:
                    print >> f, "  <li> %s <ol>"%nick
                    headerPrinted = True
                print >> f, "    <li>%s</li>"%html(m.line)
                m.assigned = True
            if headerPrinted:
                print >> f, "  </ol></li>"
        # unassigned items:
        print >> f, "  <li><b>UNASSIGNED</b><ol>"
        numberUnassigned = 0
        for m in self.minutes:
            if not isinstance(m, (Action, meeting.Action)): continue
            if getattr(m, 'assigned', False): continue
            print >> f, "    <li>%s</li>"%html(m.line)
            numberUnassigned += 1
        if numberUnassigned == 0: print >> f, "    <li>(none)</li>"
        print >> f, '  </ol>\n</li>'
        # clean-up
        print >> f, "</ol>\n\n<br>"


        # People Attending
        print >> f, """<b>People Present (lines said):</b><ol>"""
        # sort by number of lines spoken
        nicks = [ (n,c) for (n,c) in self.attendees.iteritems() ]
        nicks.sort(key=lambda x: x[1], reverse=True)
        for nick in nicks:
            print >> f, '  <li>%s (%s)</li>'%(nick[0], nick[1])
        print >> f, "</ol>\n\n<br>"
        print >> f, """Generated by <a href="%s">MeatBot</a>."""%MeetBotInfoURL
        print >> f, "</body></html>"
    def writeRawLog(self):
        """Write raw text logs."""
        f = file(self.logFilename(raw=True), 'w')
        if self._restrictlogs:
            self.restrictPermissions(f)
        f.write("\n".join(self.lines))
    def logFilename(self, url=False, raw=False):
        extension = '.log.html'
        if raw: extension = '.log.txt'
        """Name of the meeting logfile"""
        filename = self.filename + extension
        if url:
            return os.path.join(logUrlPrefix, filename)
        return os.path.join(logFileDir, filename)
    def minutesFilename(self, url=False):
        """Name of the meeting minutes file"""
        filename = self.filename +'.html'
        if url:
            return os.path.join(logUrlPrefix, filename)
        return os.path.join(logFileDir, filename)
    def restrictPermissions(self, f):
        """Remove the permissions given in the variable RestrictPerm."""
        f.flush()
        newmode = os.stat(f.name).st_mode & (~RestrictPerm)
        os.chmod(f.name, newmode)
        


#
# These are objects which we can add to the meeting minutes.  Mainly
# they exist to aid in HTML-formatting.
#
class Topic:
    def __init__(self, nick, line, linenum, time_):
        self.nick = nick ; self.topic = line ; self.linenum = linenum
        self.time = time.strftime("%H:%M:%S", time_)
    def html(self, M):
        self.link = os.path.basename(M.logFilename())
        self.topic = html(self.topic)
        self.anchor = 'l-'+str(self.linenum)
        return """<tr><td><a href='%(link)s#%(anchor)s'>%(time)s</a></td>
        <th colspan=3>Topic: %(topic)s</th>
        </tr>"""%self.__dict__
class GenericItem:
    itemtype = ''
    def __init__(self, nick, line, linenum, time_):
        self.nick = nick ; self.line = line ; self.linenum = linenum
        self.time = time.strftime("%H:%M:%S", time_)
    def html(self, M):
        self.link = os.path.basename(M.logFilename())
        self.line = html(self.line)
        self.anchor = 'l-'+str(self.linenum)
        self.__dict__['itemtype'] = self.itemtype
        return """<tr><td><a href='%(link)s#%(anchor)s'>%(time)s</a></td>
        <td>%(itemtype)s</td><td>%(nick)s</td><td>%(line)s</td>
        </tr>"""%self.__dict__
class Info(GenericItem):
    itemtype = 'INFO'
class Idea(GenericItem):
    itemtype = 'IDEA'
class Agreed(GenericItem):
    itemtype = 'AGREED'
class Action(GenericItem):
    itemtype = 'ACTION'
class Halp(GenericItem):
    itemtype = 'HALP'
class Link:
    itemtype = 'LINK'
    def __init__(self, nick, line, linenum, time_):
        self.nick = nick ; self.linenum = linenum
        self.url, self.line = (line+' ').split(' ', 1)
        self.line = self.line.strip()
        self.time = time.strftime("%H:%M:%S", time_)
    def html(self, M):
        self.link = os.path.basename(M.logFilename())
        self.anchor = 'l-'+str(self.linenum)
        self.__dict__['itemtype'] = self.itemtype
        return """<tr><td><a href='%(link)s#%(anchor)s'>%(time)s</a></td>
        <td>%(itemtype)s</td><td>%(nick)s</td><td><a href="%(url)s">%(url)s</a> %(line)s</td>
        </tr>"""%self.__dict__


def parse_time(time_):
    try: return time.strptime(time_, "%H:%M:%S")
    except ValueError: pass
    try: return time.strptime(time_, "%H:%M")
    except ValueError: pass

# None of this is very well refined.
if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'replay':
        dir, fname = os.path.split(sys.argv[2])
        logFileDir = dir  # OVERWRITING global variable!
        m = re.match('(.*)\.log\.txt', fname)
        if m:
            filename = m.group(1)
        else:
            filename = os.path.splitext(fname)[0]
        print 'Saving to:', filename
        channel = os.path.basename(sys.argv[2]).split('.')[0]


        M = Meeting(channel=channel, owner=None,
                    filename=filename, writeRawLog=False)
        for line in file(sys.argv[2]):
            # match regular spoken lines:
            r = re.compile(r'\[?([0-9: ]+)\]? <([ \w]+)> (.*)')
            m = r.match(line)
            if m:
                time_ = parse_time(m.group(1).strip())
                nick = m.group(2).strip()
                line = m.group(3).strip()
                if M.owner is None:
                    M.owner = nick ; M.chairs = {nick:True}
                M.addline(nick, line, time_=time_)
            # match /me lines
            r = re.compile(r'\[?([0-9: ]+)\]? \* ([\w]+) (.*)')
            m = r.match(line)
            if m:
                time_ = parse_time(m.group(1).strip())
                nick = m.group(2).strip()
                line = m.group(3).strip()
                M.addline(nick, "ACTION "+line, time_=time_)
        M.save()



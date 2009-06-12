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
logFileDir = '/home/richard/meetbot/'
# The links to the logfiles are given this prefix
logUrlPrefix = 'http://rkd.zgib.net/meetbot/'
# Give the pattern to save files into here.  Use %(channel)s for
# channel.  This will be sent through strftime for substituting it
# times, howover, for strftime codes you must use doubled percent
# signs (%%).  This will be joined with the directories above.
filenamePattern = '%(channel)s/%%Y/%(channel)s.%%F-%%H.%%M'
# Where to say to go for more information about MeetBot
MeetBotInfoURL = 'http://wiki.debian.org/MeetBot'
# This is used with the #restrict command to remove permissions from files.
RestrictPerm = stat.S_IRWXO|stat.S_IRWXG  # g,o perm zeroed
# RestrictPerm = stat.S_IRWXU|stat.S_IRWXO|stat.S_IRWXG  # u,g,o perm zeroed.
# used to detect #link :
UrlProtocols = ('http:', 'https:', 'irc:', 'ftp:', 'mailto:', 'ssh:')
# regular expression for parsing commands.  First group is the command name,
# second group is the rest of the line.
command_RE = re.compile(r'#([\w]+)[ \t]*(.*)')
# This is the help printed when a meeting starts
usefulCommands = "#action #agreed #halp #info #idea #link #topic"
# The channels which won't have date/time appended to the filename.
specialChannels = ("#meetbot-test", "#meetbot-test2")
specialChannelFilenamePattern = '%(channel)s/%(channel)s'
# HTML irc log highlighting style.  `pygmentize -L styles` to list.
pygmentizeStyle = 'friendly'
# Timezone setting.  You can use friendly names like 'US/Eastern', etc.
# Check /usr/share/zoneinfo/ .  Or `man timezone`: this is the contents
# of the TZ environment variable.
timeZone = 'UTC'

def html(text):
    """Escape bad sequences (in HTML) in user-generated lines."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def enc(text): return text.encode('utf-8', 'replace')
def dec(text): return text.decode('utf-8', 'replace')

# Set the timezone, using the variable above
os.environ['TZ'] = timeZone
time.tzset()

def parse_time(time_):
    try: return time.strptime(time_, "%H:%M:%S")
    except ValueError: pass
    try: return time.strptime(time_, "%H:%M")
    except ValueError: pass
logline_re = re.compile(r'\[?([0-9: ]*)\]? ?<([ \w]+)> (.*)')
loglineAction_re = re.compile(r'\[?([0-9: ]*)\]? \* ([\w]+) (.*)')

# load custom local configurations
try:
    import meetingLocalConfig
    meetingLocalConfig = reload(meetingLocalConfig)
    from meetingLocalConfig import *
except ImportError:
    pass



class MeetingCommands(object):
    # Command Definitions
    # generic parameters to these functions:
    #  nick=
    #  line=    <the payload of the line>
    #  linenum= <the line number, 1-based index (for logfile)>
    #  time_=   <time it was said>
    # Commands for Chairs:
    def do_startmeeting(self, nick, time_, line, **kwargs):
        """Begin a meeting."""
        self.reply("Meeting started %s %s.  The chair is %s."%\
                   (time.asctime(time_), timeZone, self.owner))
        self.reply(("Information about MeetBot at %s , Useful Commands: %s.")%\
                   (MeetBotInfoURL, usefulCommands))
        self.starttime = time_
        if line.strip():
            self.do_meetingtopic(nick=nick, line=line, time_=time_, **kwargs)
    def do_endmeeting(self, nick, time_, **kwargs):
        """End the meeting."""
        if not self.isChair(nick): return
        if self.oldtopic:
            self.topic(self.oldtopic)
        self.endtime = time_
        self.save()
        self.reply("Meeting ended %s %s.  Information about MeetBot at %s ."%\
                   (time.asctime(time_), timeZone, MeetBotInfoURL))
        self.reply("Minutes: "+self.minutesFilename(url=True))
        self.reply("Log:     "+self.logFilename(url=True))
        self._meetingIsOver = True
    def do_topic(self, nick, line, **kwargs):
        """Set a new topic in the channel."""
        if not self.isChair(nick): return
        self.currenttopic = line
        m = Topic(nick=nick, line=line, **kwargs)
        self.minutes.append(m)
        self.settopic()
    def do_meetingtopic(self, nick, line, **kwargs):
        """Set a meeting topic (included in all sub-topics)"""
        if not self.isChair(nick): return
        line = line.strip()
        if line == '' or line.lower() == 'none' or line.lower() == 'unset':
            self._meetingTopic = None
        else:
            self._meetingTopic = line
        self.settopic()
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
        for chair in re.split('[, ]+', line.strip()):
            chair = html(chair.strip())
            if chair not in self.chairs:
                self.addnick(chair, lines=0)
                self.chairs.setdefault(chair, True)
                self.reply("Chair added: %s"%chair)
    def do_unchair(self, nick, line, **kwargs):
        """Remove a chair to the meeting (founder can not be removed)."""
        if not self.isChair(nick): return
        for chair in line.strip().split():
            chair = html(chair.strip())
            if chair in self.chairs:
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
            self.addnick(html(nick), lines=0)
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
                 filename=None, writeRawLog=False):
        self.owner = owner
        self.channel = channel
        self.currenttopic = ""
        self.oldtopic = oldtopic
        self.lines = [ ]
        self.minutes = [ ]
        self.attendees = { }
        self.chairs = { }
        self._writeRawLog = writeRawLog
        self._meetingTopic = None
        self._meetingIsOver = False
        if filename:
            self._filename = filename

    # These commands are callbacks to manipulate the IRC protocol.
    # set self._sendReply and self._setTopic to an callback to do these things.
    def reply(self, x):
        """Send a reply to the IRC channel."""
        if hasattr(self, '_sendReply') and not self._lurk:
            self._sendReply(x)
        else:
            print "REPLY:", enc(x)
    def topic(self, x):
        """Set the topic in the IRC channel."""
        if hasattr(self, '_setTopic') and not self._lurk:
            self._setTopic(x)
        else:
            print "TOPIC:", enc(x)
    def settopic(self):
        "The actual code to set the topic"
        if self._meetingTopic:
            topic = '%s (Meeting topic: %s)'%(self.currenttopic,
                                              self._meetingTopic)
        else:
            topic = self.currenttopic
        self.topic(topic)
    def addnick(self, nick, lines=1):
        """This person has spoken, lines=<how many lines>"""
        self.attendees[nick] = self.attendees.get(nick, 0) + lines
    def isChair(self, nick):
        """Is the nick a chair?"""
        return (nick == self.owner  or  nick in self.chairs)
    # Primary enttry point for new lines in the log:
    def addline(self, nick, line, time_=None):
        """This is the way to add lines to the Meeting object.
        """
        nick = html(nick)
        self.addnick(nick)
        line = line.strip(' \x01') # \x01 is present in ACTIONs
        nick = dec(nick)
        line = dec(line)
        # Setting a custom time is useful when replying logs,
        # otherwise use our current time:
        if time_ is None: time_ = time.localtime()
        
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
        import pygments.token as token
        from pygments.lexer import bygroups
        formatter = HtmlFormatter(encoding='utf-8', lineanchors='l',
                                  full=True, style=pygmentizeStyle)
        Lexer = IrcLogsLexer
        Lexer.tokens['msg'][1:1] = \
           [ # match:   #topic commands
            (r"(\#topic[ \t\f\v]*)(.*\n)",
             bygroups(token.Keyword, token.Generic.Heading), '#pop'),
             # match:   #command   (others)
            (r"(\#[^\s]+[ \t\f\v]*)(.*\n)",
             bygroups(token.Keyword, token.Generic.Strong), '#pop'),
           ]
        lexer = Lexer(encoding='utf-8')
        #from rkddp.interact import interact ; interact()
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
        data = [ ]
        # We might want to restrict read-permissions of the files from
        # the webserver.
        if self._restrictlogs:
            self.restrictPermissions(f)

        if self._meetingTopic:
            pageTitle = "%s: %s"%(self.channel, self._meetingTopic)
        else:
            pageTitle = "%s Meeting"%self.channel
        # Header and things stored
        data.append(
        '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        <html>
        <head>
        <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
        <title>%s</title>
        </head>
        <body>
        <h1>%s</h1>
        Meeting started by %s at %s %s.  (<a href="%s">full logs</a>)<br>
        \n\n<table border=1>'''%(pageTitle, pageTitle, self.owner,
                             time.strftime("%H:%M:%S", self.starttime),
                             timeZone,
                             os.path.basename(self.logFilename())))
        # Add all minute items to the table
        for m in self.minutes:
            data.append(m.html(self))
        # End the log portion
        data.append("""</table>
        Meeting ended at %s %s.  (<a href="%s">full logs</a>)"""%\
            (time.strftime("%H:%M:%S", self.endtime), timeZone,
             os.path.basename(self.logFilename())))
        data.append("\n<br><br><br>")


        # Action Items
        data.append("<b>Action Items</b><ol>")
        import meeting
        for m in self.minutes:
            # The hack below is needed because of pickling problems
            if not isinstance(m, (Action, meeting.Action)): continue
            data.append("  <li>%s</li>"%m.line) #already escaped
        data.append("</ol>\n\n<br>")
        

        # Action Items, by person (This could be made lots more efficient)
        data.append("<b>Action Items, by person</b>\n<ol>")
        for nick in sorted(self.attendees.keys(), key=lambda x: x.lower()):
            headerPrinted = False
            for m in self.minutes:
                # The hack below is needed because of pickling problems
                if not isinstance(m, (Action, meeting.Action)): continue
                if m.line.find(nick) == -1: continue
                if not headerPrinted:
                    data.append("  <li> %s <ol>"%nick)
                    headerPrinted = True
                data.append("    <li>%s</li>"%m.line) # already escaped
                m.assigned = True
            if headerPrinted:
                data.append("  </ol></li>")
        # unassigned items:
        data.append("  <li><b>UNASSIGNED</b><ol>")
        numberUnassigned = 0
        for m in self.minutes:
            if not isinstance(m, (Action, meeting.Action)): continue
            if getattr(m, 'assigned', False): continue
            data.append("    <li>%s</li>"%m.line) # already escaped
            numberUnassigned += 1
        if numberUnassigned == 0: data.append("    <li>(none)</li>")
        data.append('  </ol>\n</li>')
        # clean-up
        data.append("</ol>\n\n<br>")


        # People Attending
        data.append("""<b>People Present (lines said):</b><ol>""")
        # sort by number of lines spoken
        nicks = [ (n,c) for (n,c) in self.attendees.iteritems() ]
        nicks.sort(key=lambda x: x[1], reverse=True)
        for nick in nicks:
            data.append('  <li>%s (%s)</li>'%(nick[0], nick[1]))
        data.append("</ol>\n\n<br>")
        data.append("""Generated by <a href="%s">MeetBot</a>."""%
                                                             MeetBotInfoURL)
        data.append("</body></html>")

        f.write(enc("\n".join(data)))
    def writeRawLog(self):
        """Write raw text logs."""
        f = file(self.logFilename(raw=True), 'w')
        if self._restrictlogs:
            self.restrictPermissions(f)
        f.write(enc("\n".join(self.lines)))
    def filename(self, url=False):
        # provide a way to override the filename.  If it is
        # overridden, it must be a full path (and the URL-part may not
        # work.):
        if getattr(self, '_filename', None):
            return self._filename
        # names useful for pathname formatting.
        # Certain test channels always get the same name - don't need
        # file prolifiration for them
        if self.channel in specialChannels:
            # mask global!!
            pattern = specialChannelFilenamePattern
        else:
            pattern = filenamePattern
        channel = self.channel.strip('# ')
        path = pattern%locals()
        path = time.strftime(path, self.starttime)
        # If we want the URL name, append URL prefix and return
        if url:
            return os.path.join(logUrlPrefix, path)
        path = os.path.join(logFileDir, path)
        return path
    def logFilename(self, url=False, raw=False):
        """Name of the meeting logfile"""
        extension = '.log.html'
        if raw:
            extension = '.log.txt'
        fname = self.filename(url=url)+extension
        if not url and not os.access(os.path.dirname(fname), os.F_OK):
            os.makedirs(os.path.dirname(fname))
        return fname
    def minutesFilename(self, url=False):
        """Name of the meeting minutes file"""
        fname = self.filename(url=url)+'.html'
        if not url and not os.access(os.path.dirname(fname), os.F_OK):
            os.makedirs(os.path.dirname(fname))
        return fname
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
        self.time = time.strftime("%H:%M:%S", time_)
        self.url, self.line = (line+' ').split(' ', 1)
        # URL-sanitization
        self.url_readable = html(self.url) # readable line version
        self.url = self.url.replace('"', "%22")
        # readable line satitization:
        self.line = html(self.line.strip())
    def html(self, M):
        self.link = os.path.basename(M.logFilename())
        self.anchor = 'l-'+str(self.linenum)
        self.__dict__['itemtype'] = self.itemtype
        return """<tr><td><a href='%(link)s#%(anchor)s'>%(time)s</a></td>
        <td>%(itemtype)s</td><td>%(nick)s</td><td><a href="%(url)s">%(url_readable)s</a> %(line)s</td>
        </tr>"""%self.__dict__

# None of this is very well refined.
if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'replay':
        fname = sys.argv[2]
        m = re.match('(.*)\.log\.txt', fname)
        if m:
            filename = m.group(1)
        else:
            filename = os.path.splitext(fname)[0]
        print 'Saving to:', filename
        channel = '#'+os.path.basename(sys.argv[2]).split('.')[0]

        M = Meeting(channel=channel, owner=None,
                    filename=filename, writeRawLog=False)
        for line in file(sys.argv[2]):
            # match regular spoken lines:
            m = logline_re.match(line)
            if m:
                time_ = parse_time(m.group(1).strip())
                nick = m.group(2).strip()
                line = m.group(3).strip()
                if M.owner is None:
                    M.owner = nick ; M.chairs = {nick:True}
                M.addline(nick, line, time_=time_)
            # match /me lines
            m = loglineAction_re.match(line)
            if m:
                time_ = parse_time(m.group(1).strip())
                nick = m.group(2).strip()
                line = m.group(3).strip()
                M.addline(nick, "ACTION "+line, time_=time_)
        #M.save() # should be done by #endmeeting in the logs!



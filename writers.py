# Richard Darst, June 2009

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

import os
import re
import textwrap
import time

#from meeting import timeZone, meetBotInfoURL

# Needed for testing with isinstance() for properly writing.
#from items import Topic, Action
import items

# Data sanitizing for various output methods
def html(text):
    """Escape bad sequences (in HTML) in user-generated lines."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
rstReplaceRE = re.compile('_( |-|$)')
def rst(text):
    """Escapes bad sequences in reST"""
    return rstReplaceRE.sub(r'\_\1', text)
def text(text):
    """Escapes bad sequences in text (not implemented yet)"""
    return text

# wraping functions (for RST)
class TextWrapper(textwrap.TextWrapper):
    wordsep_re = re.compile(r'(\s+)')
def wrapList(item, indent=0):
    return TextWrapper(width=72, initial_indent=' '*indent,
                       subsequent_indent= ' '*(indent+2),
                       break_long_words=False).fill(item)
def replaceWRAP(item):
    re_wrap = re.compile('WRAP(.*)WRAP', re.DOTALL)
    def repl(m):
        return TextWrapper(width=72, break_long_words=False).fill(m.group(1))
    return re_wrap.sub(repl, item)


def MeetBotVersion():
    import meeting
    if hasattr(meeting, '__version__'):
        return ' '+meeting.__version__
    else:
        return ''


class _BaseWriter(object):
    def __init__(self, M, **kwargs):
        self.M = M

    def format(self, extension=None):
        """Override this method to implement the formatting.

        For file output writers, the method should return a unicode
        object containing the contents of the file to write.

        The argument 'extension' is the key from `writer_map`.  For
        file writers, this can (and should) be ignored.  For non-file
        outputs, this can be used to This can be used to pass data,
        """
        raise NotImplementedError

    @property
    def pagetitle(self):
        if self.M._meetingTopic:
            return "%s: %s"%(self.M.channel, self.M._meetingTopic)
        return "%s Meeting"%self.M.channel

    def replacements(self):
        return {'pageTitle':self.pagetitle,
                'owner':self.M.owner,
                'starttime':time.strftime("%H:%M:%S", self.M.starttime),
                'endtime':time.strftime("%H:%M:%S", self.M.endtime),
                'timeZone':self.M.config.timeZone,
                'fullLogs':self.M.config.basename+'.log.html',
                'MeetBotInfoURL':self.M.config.MeetBotInfoURL,
                'MeetBotVersion':MeetBotVersion(),
             }
    def iterNickCounts(self):
        nicks = [ (n,c) for (n,c) in self.M.attendees.iteritems() ]
        nicks.sort(key=lambda x: x[1], reverse=True)
        return nicks

    def iterActionItemsNick(self):
        for nick in sorted(self.M.attendees.keys(), key=lambda x: x.lower()):
            def nickitems():
                for m in self.M.minutes:
                    # The hack below is needed because of pickling problems
                    if m.itemtype != "ACTION": continue
                    if m.line.find(nick) == -1: continue
                    m.assigned = True
                    yield m
            yield nick, nickitems()
    def iterActionItemsUnassigned(self):
        for m in self.M.minutes:
            if m.itemtype != "ACTION": continue
            if getattr(m, 'assigned', False): continue
            yield m


class TextLog(_BaseWriter):
    def format(self, extension=None):
        M = self.M
        """Write raw text logs."""
        return "\n".join(M.lines)
    update_realtime = True



class HTMLlog(_BaseWriter):
    def format(self, extension=None):
        """Write pretty HTML logs."""
        M = self.M
        # pygments lexing setup:
        # (pygments HTML-formatter handles HTML-escaping)
        import pygments
        from pygments.lexers import IrcLogsLexer
        from pygments.formatters import HtmlFormatter
        import pygments.token as token
        from pygments.lexer import bygroups
        # Don't do any encoding in this function with pygments.
        # That's only right before the i/o functions in the Config
        # object.
        formatter = HtmlFormatter(lineanchors='l',
                                  full=True, style=M.config.pygmentizeStyle,
                                  output_encoding=self.M.config.output_codec)
        Lexer = IrcLogsLexer
        Lexer.tokens['msg'][1:1] = \
           [ # match:   #topic commands
            (r"(\#topic[ \t\f\v]*)(.*\n)",
             bygroups(token.Keyword, token.Generic.Heading), '#pop'),
             # match:   #command   (others)
            (r"(\#[^\s]+[ \t\f\v]*)(.*\n)",
             bygroups(token.Keyword, token.Generic.Strong), '#pop'),
           ]
        lexer = Lexer()
        #from rkddp.interact import interact ; interact()
        out = pygments.highlight("\n".join(M.lines), lexer, formatter)
        return out


class HTML(_BaseWriter):

    body = textwrap.dedent('''\
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
    <html>
    <head>
    <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
    <title>%(pageTitle)s</title>
    </head>
    <body>
    <h1>%(pageTitle)s</h1>
    Meeting started by %(owner)s at %(starttime)s %(timeZone)s.
    (<a href="%(fullLogs)s">full logs</a>)<br>


    <table border=1>
    %(MeetingItems)s
    </table>
    Meeting ended at %(endtime)s %(timeZone)s.
    (<a href="%(fullLogs)s">full logs</a>)

    <br><br><br>

    <b>Action Items</b><ol>
    %(ActionItems)s
    </ol>
    <br>

    <b>Action Items, by person</b>
    <ol>
    %(ActionItemsPerson)s
    </ol><br>

    <b>People Present (lines said):</b><ol>
    %(PeoplePresent)s
    </ol>

    <br>
    Generated by <a href="%(MeetBotInfoURL)s">MeetBot</a>%(MeetBotVersion)s.
    </body></html>
    ''')

    def format(self, extension=None):
        """Write the minutes summary."""
        M = self.M

        # Add all minute items to the table
        MeetingItems = [ ]
        for m in M.minutes:
            MeetingItems.append(m.html(M))
        MeetingItems = "\n".join(MeetingItems)

        # Action Items
        ActionItems = [ ]
        for m in M.minutes:
            # The hack below is needed because of pickling problems
            if m.itemtype != "ACTION": continue
            ActionItems.append("  <li>%s</li>"%html(m.line))
        if len(ActionItems) == 0:
            ActionItems.append("  <li>(none)</li>")
        ActionItems = "\n".join(ActionItems)

        # Action Items, by person (This could be made lots more efficient)
        ActionItemsPerson = [ ]
        for nick, items in self.iterActionItemsNick():
            headerPrinted = False
            for m in items:
                if not headerPrinted:
                    ActionItemsPerson.append("  <li> %s <ol>"%html(nick))
                    headerPrinted = True
                ActionItemsPerson.append("    <li>%s</li>"%html(m.line))
            if headerPrinted:
                ActionItemsPerson.append("  </ol></li>")
        # unassigned items:
        ActionItemsPerson.append("  <li><b>UNASSIGNED</b><ol>")
        numberUnassigned = 0
        for m in self.iterActionItemsUnassigned():
            ActionItemsPerson.append("    <li>%s</li>"%html(m.line))
            numberUnassigned += 1
        if numberUnassigned == 0:
            ActionItemsPerson.append("    <li>(none)</li>")
        ActionItemsPerson.append('  </ol>\n</li>')
        ActionItemsPerson = "\n".join(ActionItemsPerson)

        # People Attending
        PeoplePresent = [ ]
        # sort by number of lines spoken
        for nick, count in self.iterNickCounts():
            PeoplePresent.append('  <li>%s (%s)</li>'%(html(nick), count))
        PeoplePresent = "\n".join(PeoplePresent)

        # Actual formatting and replacement
        repl = self.replacements()
        repl.update({'MeetingItems':MeetingItems,
                     'ActionItems': ActionItems,
                     'ActionItemsPerson': ActionItemsPerson,
                     'PeoplePresent':PeoplePresent,
                     })
        body = self.body
        body = body%repl
        body = replaceWRAP(body)
        return body
class HTML2(_BaseWriter):

    body = textwrap.dedent('''\
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
    <html>
    <head>
    <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
    <title>%(pageTitle)s</title>
    </head>
    <body>
    <h1>%(pageTitle)s</h1>
    Meeting started by %(owner)s at %(starttime)s %(timeZone)s.
    (<a href="%(fullLogs)s">full logs</a>)<br>
    
    %(MeetingItems)s
    Meeting ended at %(endtime)s %(timeZone)s.
    (<a href="%(fullLogs)s">full logs</a>)

    <br><br><br>

    <b>Action Items</b><ol>
    %(ActionItems)s
    </ol>
    <br>

    <b>Action Items, by person</b>
    <ol>
    %(ActionItemsPerson)s
    </ol><br>

    <b>People Present (lines said):</b><ol>
    %(PeoplePresent)s
    </ol>

    <br>
    Generated by <a href="%(MeetBotInfoURL)s">MeetBot</a>%(MeetBotVersion)s.
    </body></html>
    ''')

    def format(self, extension=None):
        """Write the minutes summary."""
        M = self.M

        # Add all minute items to the table
        MeetingItems = [ ]
        MeetingItems.append("<ol>")



        haveTopic = None
        inSublist = False
        for m in M.minutes:
            item = '<li>'+m.html2(M)
            if m.itemtype == "TOPIC":
                if inSublist:
                    MeetingItems.append("</ol>")
                    inSublist = False
                if haveTopic:
                    MeetingItems.append("<br></li>")
                item = item
                haveTopic = True
            else:
                if not inSublist:
                    MeetingItems.append('<ol type="a">')
                    inSublist = True
                if haveTopic: item = wrapList(item, 2)+"</li>"
                else:         item = wrapList(item, 0)+"</li>"
            MeetingItems.append(item)
            #MeetingItems.append("</li>")

        if inSublist:
            MeetingItems.append("</ol>")
        if haveTopic:
            MeetingItems.append("</li>")



        MeetingItems.append("</ol>")
        MeetingItems = "\n".join(MeetingItems)

        # Action Items
        ActionItems = [ ]
        for m in M.minutes:
            # The hack below is needed because of pickling problems
            if m.itemtype != "ACTION": continue
            ActionItems.append("  <li>%s</li>"%html(m.line))
        if len(ActionItems) == 0:
            ActionItems.append("  <li>(none)</li>")
        ActionItems = "\n".join(ActionItems)

        # Action Items, by person (This could be made lots more efficient)
        ActionItemsPerson = [ ]
        for nick, items in self.iterActionItemsNick():
            headerPrinted = False
            for m in items:
                if not headerPrinted:
                    ActionItemsPerson.append("  <li> %s <ol>"%html(nick))
                    headerPrinted = True
                ActionItemsPerson.append("    <li>%s</li>"%html(m.line))
            if headerPrinted:
                ActionItemsPerson.append("  </ol></li>")
        # unassigned items:
        ActionItemsPerson.append("  <li><b>UNASSIGNED</b><ol>")
        numberUnassigned = 0
        for m in self.iterActionItemsUnassigned():
            ActionItemsPerson.append("    <li>%s</li>"%html(m.line))
            numberUnassigned += 1
        if numberUnassigned == 0:
            ActionItemsPerson.append("    <li>(none)</li>")
        ActionItemsPerson.append('  </ol>\n</li>')
        ActionItemsPerson = "\n".join(ActionItemsPerson)

        # People Attending
        PeoplePresent = [ ]
        # sort by number of lines spoken
        for nick, count in self.iterNickCounts():
            PeoplePresent.append('  <li>%s (%s)</li>'%(html(nick), count))
        PeoplePresent = "\n".join(PeoplePresent)

        # Actual formatting and replacement
        repl = self.replacements()
        repl.update({'MeetingItems':MeetingItems,
                     'ActionItems': ActionItems,
                     'ActionItemsPerson': ActionItemsPerson,
                     'PeoplePresent':PeoplePresent,
                     })
        body = self.body
        body = body%repl
        body = replaceWRAP(body)
        return body


class ReST(_BaseWriter):

    body = textwrap.dedent("""\
    %(titleBlock)s
    %(pageTitle)s
    %(titleBlock)s


    WRAPMeeting started by %(owner)s at %(starttime)s %(timeZone)s.
    The `full logs`_ are available.WRAP

    .. _`full logs`: %(fullLogs)s



    Meeting log
    -----------
    %(MeetingItems)s

    Meeting ended at %(endtime)s %(timeZone)s.




    Action Items
    ------------
    %(ActionItems)s




    Action Items, by person
    -----------------------
    %(ActionItemsPerson)s




    People Present (lines said)
    ---------------------------
    %(PeoplePresent)s




    Generated by `MeetBot`_%(MeetBotVersion)s

    .. _`MeetBot`: %(MeetBotInfoURL)s
    """)

    def format(self, extension=None):
        """Return a ReStructured Text minutes summary."""
        M = self.M

        # Agenda items
        MeetingItems = [ ]
        M.rst_urls = [ ]
        M.rst_refs = { }
        haveTopic = None
        for m in M.minutes:
            item = "* "+m.rst(M)
            if m.itemtype == "TOPIC":
                item = wrapList(item, 0)
                haveTopic = True
            else:
                if haveTopic: item = wrapList(item, 2)
                else:         item = wrapList(item, 0)
            MeetingItems.append(item)
        MeetingItems = '\n\n'.join(MeetingItems)
        MeetingURLs = "\n".join(M.rst_urls)
        del M.rst_urls, M.rst_refs
        MeetingItems = MeetingItems + '\n\n'+MeetingURLs

        # Action Items
        ActionItems = [ ]
        for m in M.minutes:
            # The hack below is needed because of pickling problems
            if m.itemtype != "ACTION": continue
            #already escaped
            ActionItems.append(wrapList("* %s"%rst(m.line), indent=0))
        ActionItems = "\n\n".join(ActionItems)

        # Action Items, by person (This could be made lots more efficient)
        ActionItemsPerson = [ ]
        for nick in sorted(M.attendees.keys(), key=lambda x: x.lower()):
            headerPrinted = False
            for m in M.minutes:
                # The hack below is needed because of pickling problems
                if m.itemtype != "ACTION": continue
                if m.line.find(nick) == -1: continue
                if not headerPrinted:
                    ActionItemsPerson.append("* %s"%rst(nick))
                    headerPrinted = True
                ActionItemsPerson.append(wrapList("* %s"%rst(m.line), 2))
                m.assigned = True
        # unassigned items:
        ActionItemsPerson.append("* **UNASSIGNED**")
        numberUnassigned = 0
        for m in M.minutes:
            if m.itemtype != "ACTION": continue
            if getattr(m, 'assigned', False): continue
            ActionItemsPerson.append(wrapList("* %s"%rst(m.line), 2))
            numberUnassigned += 1
        if numberUnassigned == 0: ActionItemsPerson.append("  * (none)")
        ActionItemsPerson = "\n\n".join(ActionItemsPerson)

        # People Attending
        PeoplePresent = [ ]
        # sort by number of lines spoken
        for nick, count in self.iterNickCounts():
            PeoplePresent.append('* %s (%s)'%(rst(nick), count))
        PeoplePresent = "\n\n".join(PeoplePresent)

        # Actual formatting and replacement
        repl = self.replacements()
        repl.update({'titleBlock':('='*len(repl['pageTitle'])),
                     'MeetingItems':MeetingItems,
                     'ActionItems': ActionItems,
                     'ActionItemsPerson': ActionItemsPerson,
                     'PeoplePresent':PeoplePresent,
                     })
        body = self.body
        body = replaceWRAP(body)
        body = body%repl
        return body

class HTMLfromReST(_BaseWriter):

    def format(self, extension=None):
        M = self.M
        import docutils.core
        rst = ReST(M).format(extension)
        rstToHTML = docutils.core.publish_string(rst, writer_name='html',
                             settings_overrides={'file_insertion_enabled': 0,
                                                 'raw_enabled': 0,
                                'output_encoding':self.M.config.output_codec})
        return rstToHTML



class Text(_BaseWriter):

    body = textwrap.dedent("""\
    %(titleBlock)s
    %(pageTitle)s
    %(titleBlock)s


    WRAPMeeting started by %(owner)s at %(starttime)s %(timeZone)s.
    The `full logs`_ are available.WRAP

    .. _`full logs`: %(fullLogs)s



    Meeting log
    -----------
    %(MeetingItems)s

    Meeting ended at %(endtime)s %(timeZone)s.




    Action Items
    ------------
    %(ActionItems)s




    Action Items, by person
    -----------------------
    %(ActionItemsPerson)s




    People Present (lines said)
    ---------------------------
    %(PeoplePresent)s




    Generated by `MeetBot`_%(MeetBotVersion)s

    .. _`MeetBot`: %(MeetBotInfoURL)s
    """)

    def format(self, extension=None):
        """Return a ReStructured Text minutes summary."""
        M = self.M

        # Agenda items
        MeetingItems = [ ]
        #M.rst_urls = [ ]
        #M.rst_refs = { }
        haveTopic = None
        for m in M.minutes:
            item = "* "+m.text(M)
            if m.itemtype == "TOPIC":
                if haveTopic:
                    MeetingItems.append("")
                item = wrapList(item, 0)
                haveTopic = True
            else:
                if haveTopic: item = wrapList(item, 2)
                else:         item = wrapList(item, 0)
            MeetingItems.append(item)
        MeetingItems = '\n'.join(MeetingItems)
        #MeetingURLs = "\n".join(M.rst_urls)
        #del M.rst_urls, M.rst_refs
        MeetingItems = MeetingItems# + '\n\n'+MeetingURLs

        # Action Items
        ActionItems = [ ]
        for m in M.minutes:
            # The hack below is needed because of pickling problems
            if m.itemtype != "ACTION": continue
            #already escaped
            ActionItems.append(wrapList("* %s"%text(m.line), indent=0))
        ActionItems = "\n".join(ActionItems)

        # Action Items, by person (This could be made lots more efficient)
        ActionItemsPerson = [ ]
        for nick in sorted(M.attendees.keys(), key=lambda x: x.lower()):
            headerPrinted = False
            for m in M.minutes:
                # The hack below is needed because of pickling problems
                if m.itemtype != "ACTION": continue
                if m.line.find(nick) == -1: continue
                if not headerPrinted:
                    ActionItemsPerson.append("* %s"%text(nick))
                    headerPrinted = True
                ActionItemsPerson.append(wrapList("* %s"%text(m.line), 2))
                m.assigned = True
        # unassigned items:
        ActionItemsPerson.append("* **UNASSIGNED**")
        numberUnassigned = 0
        for m in M.minutes:
            if m.itemtype != "ACTION": continue
            if getattr(m, 'assigned', False): continue
            ActionItemsPerson.append(wrapList("* %s"%text(m.line), 2))
            numberUnassigned += 1
        if numberUnassigned == 0: ActionItemsPerson.append("  * (none)")
        ActionItemsPerson = "\n".join(ActionItemsPerson)

        # People Attending
        PeoplePresent = [ ]
        # sort by number of lines spoken
        for nick, count in self.iterNickCounts():
            PeoplePresent.append('* %s (%s)'%(text(nick), count))
        PeoplePresent = "\n".join(PeoplePresent)

        # Actual formatting and replacement
        repl = self.replacements()
        repl.update({'titleBlock':('='*len(repl['pageTitle'])),
                     'MeetingItems':MeetingItems,
                     'ActionItems': ActionItems,
                     'ActionItemsPerson': ActionItemsPerson,
                     'PeoplePresent':PeoplePresent,
                     })
        body = self.body
        body = replaceWRAP(body)
        body = body%repl
        return body


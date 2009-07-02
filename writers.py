# Richard Darst, 2009

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
def rst(text):
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




class _BaseWriter(object):
    def __init__(self, M):
        self.M = M

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
    def format(self):
        M = self.M
        """Write raw text logs."""
        return "\n".join(M.lines)


class HTMLlog(_BaseWriter):
    def format(self):
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
                                  full=True, style=M.config.pygmentizeStyle)
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
    def format(self):
        """Write the minutes summary."""
        M = self.M
        # Header and things stored

        # Add all minute items to the table
        MeetingItems = [ ]
        for m in M.minutes:
            MeetingItems.append(m.html(M))
        MeetingItems = "\n".join(MeetingItems)

        # End the log portion


        # Action Items
        ActionItems = [ ]
        for m in M.minutes:
            # The hack below is needed because of pickling problems
            if m.itemtype != "ACTION": continue
            ActionItems.append("  <li>%s</li>"%m.line) #already escaped
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
            PeoplePresent.append('  <li>%s (%s)</li>'%(nick, count))
        PeoplePresent = "\n".join(PeoplePresent)



        body = '''\
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        <html>
        <head>
        <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
        <title>%(pageTitle)s</title>
        </head>
        <body>
        <h1>%(pageTitle)s</h1>
        Meeting started by %(chair)s at %(starttime)s %(timeZone)s.
        (<a href="%(fullLogs)s">full logs</a>)<br>
        \n\n<table border=1>
        %(MeetingItems)s
        </table>
        Meeting ended at %(endtime)s %(timeZone)s.
        (<a href="%(fullLogs)s">full logs</a>)

        <br><br><br>

        <b>Action Items</b><ol>
        %(ActionItems)s
        </ol>
        <br>

        <b>Action Items, by person</b>\n<ol>
        %(ActionItemsPerson)s
        </ol><br>

        <b>People Present (lines said):</b><ol>
        %(PeoplePresent)s
        </ol>

        <br>
        Generated by <a href="%(MeetBotInfoURLs">MeetBot</a>."""
        </body></html>
        '''


        #%(pageTitle, pageTitle, M.owner,
        #  time.strftime("%H:%M:%S", M.starttime),
        #  M.config.timeZone,
        #  M.config.basename+'.log.html',
        #  time.strftime("%H:%M:%S", M.endtime), M.config.timeZone,
        #     M.config.basename+'.log.html'
        #                         ))


        body = textwrap.dedent(body)
        body = replaceWRAP(body)
        repl = self.replacements()
        repl.update({'MeetingItems':MeetingItems,
                     'ActionItems': ActionItems,
                     'ActionItemsPerson': ActionItemsPerson,
                     'PeoplePresent':PeoplePresent,
                     })
        body = body%repl
        return body


class RST(_BaseWriter):
    def format(self):
        """Return a ReStructured Text minutes summary."""
        M = self.M

        pageTitle = self.pagetitle

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
                else:         item = wrapList(item, 1)
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
            ActionItems.append(wrapList("* %s"%m.line, indent=0))
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
                    ActionItemsPerson.append("* %s"%nick)
                    headerPrinted = True
                # already escaped
                ActionItemsPerson.append(wrapList("* %s"%m.line, 2)) 
                m.assigned = True
            #if headerPrinted:
            #    ActionItemsPerson.append("  </ol></li>")
        # unassigned items:
        ActionItemsPerson.append("* **UNASSIGNED**")
        numberUnassigned = 0
        for m in M.minutes:
            if m.itemtype != "ACTION": continue
            if getattr(m, 'assigned', False): continue
            # already escaped
            ActionItemsPerson.append(wrapList("* %s"%m.line, 2))
            numberUnassigned += 1
        if numberUnassigned == 0: ActionItemsPerson.append("  * (none)")
        #ActionItemsPerson.append('  </ol>\n</li>')
        # clean-up
        #ActionItemsPerson.append("</ol>\n\n<br>")
        ActionItemsPerson = "\n\n".join(ActionItemsPerson)


        # People Attending
        PeoplePresent = [ ]
        # sort by number of lines spoken
        for nick, count in self.iterNickCounts():
            PeoplePresent.append('* %s (%s)'%(nick, count))
        PeoplePresent = "\n\n".join(PeoplePresent)

        # End the log portion
        body = """\
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




        Generated by `MeetBot`_

        .. _`MeetBot`: %(MeetBotInfoURL)s
        """
        body = textwrap.dedent(body)
        body = replaceWRAP(body)
        repl = self.replacements()
        repl.update({'titleBlock':('='*len(repl['pageTitle'])),
                     'MeetingItems':MeetingItems,
                     'ActionItems': ActionItems,
                     'ActionItemsPerson': ActionItemsPerson,
                     'PeoplePresent':PeoplePresent,
                     })
        body = body%repl
        return body

class HTMLfromRST(_BaseWriter):

    def format(self):
        M = self.M
        import docutils.core
        rst = RST(M).format()
        rstToHTML = docutils.core.publish_string(rst, writer_name='html',
                             settings_overrides={'file_insertion_enabled': 0,
                                                 'raw_enabled': 0})
        return rstToHTML

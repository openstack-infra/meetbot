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

class _BaseWriter(object):
    pass

class TextLog(object):
    def format(self, M):
        """Write raw text logs."""
        return "\n".join(M.lines)


class HTMLlog(object):
    def format(self, M):
        """Write pretty HTML logs."""
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


class HTML(object):
    def format(self, M):
        """Write the minutes summary."""
        data = [ ]
        if M._meetingTopic:
            pageTitle = "%s: %s"%(M.channel, M._meetingTopic)
        else:
            pageTitle = "%s Meeting"%M.channel
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
        \n\n<table border=1>'''%(pageTitle, pageTitle, M.owner,
                             time.strftime("%H:%M:%S", M.starttime),
                             M.config.timeZone,
                             M.config.basename+'.log.html',
                                 ))
        # Add all minute items to the table
        for m in M.minutes:
            data.append(m.html(M))
        # End the log portion
        data.append("""</table>
        Meeting ended at %s %s.  (<a href="%s">full logs</a>)"""%\
            (time.strftime("%H:%M:%S", M.endtime), M.config.timeZone,
             M.config.basename+'.log.html'))
        data.append("\n<br><br><br>")


        # Action Items
        data.append("<b>Action Items</b><ol>")
        import meeting
        for m in M.minutes:
            # The hack below is needed because of pickling problems
            if m.itemtype != "ACTION": continue
            data.append("  <li>%s</li>"%m.line) #already escaped
        data.append("</ol>\n\n<br>")
        

        # Action Items, by person (This could be made lots more efficient)
        data.append("<b>Action Items, by person</b>\n<ol>")
        for nick in sorted(M.attendees.keys(), key=lambda x: x.lower()):
            headerPrinted = False
            for m in M.minutes:
                # The hack below is needed because of pickling problems
                if m.itemtype != "ACTION": continue
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
        for m in M.minutes:
            if m.itemtype != "ACTION": continue
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
        nicks = [ (n,c) for (n,c) in M.attendees.iteritems() ]
        nicks.sort(key=lambda x: x[1], reverse=True)
        for nick in nicks:
            data.append('  <li>%s (%s)</li>'%(nick[0], nick[1]))
        data.append("</ol>\n\n<br>")
        data.append("""Generated by <a href="%s">MeetBot</a>."""%
                                                  M.config.MeetBotInfoURL)
        data.append("</body></html>")

        return "\n".join(data)

class RST(object):
    def __init__(self):
        pass

    def format(self, M):
        """Return a ReStructured Text minutes summary."""
        dedent = textwrap.dedent
        wrap = textwrap.wrap
        fill = textwrap.fill
        def wrapList(item, indent=0):
            return fill(item, 72,
                        initial_indent=' '*indent,
                        subsequent_indent= ' '*(indent+2))
        def replaceWRAP(item):
            re_wrap = re.compile('WRAP(.*)WRAP', re.DOTALL)
            def repl(m):
                return fill(m.group(1), 72,
                            break_long_words=False)
            return re_wrap.sub(repl, item)


        if M._meetingTopic:
            pageTitle = "%s: %s"%(M.channel, M._meetingTopic)
        else:
            pageTitle = "%s Meeting"%M.channel

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
        nicks = [ (n,c) for (n,c) in M.attendees.iteritems() ]
        nicks.sort(key=lambda x: x[1], reverse=True)
        for nick in nicks:
            PeoplePresent.append('* %s (%s)'%(nick[0], nick[1]))
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
        body = replaceWRAP(dedent(body))
        body = body%{'titleBlock':('='*len(pageTitle)),
             'pageTitle':pageTitle,
             'owner':M.owner,
             'starttime':time.strftime("%H:%M:%S", M.starttime),
             'timeZone':M.config.timeZone,
             'fullLogs':M.config.basename+'.log.html',
             'endtime':time.strftime("%H:%M:%S", M.endtime),
             'timeZone':M.config.timeZone,
             'ActionItems': ActionItems,
             'ActionItemsPerson': ActionItemsPerson,
             'MeetBotInfoURL':M.config.MeetBotInfoURL,
             'PeoplePresent':PeoplePresent,
             'MeetingItems':MeetingItems,
             }
        #print body
        #from fitz import interactnow
        #osys.exit()
        return body

class HTMLfromRST(object):

    def format(self, M):
        import docutils.core
        rst = RST().format(M)
        rstToHTML = docutils.core.publish_string(rst, writer_name='html')
        return rstToHTML

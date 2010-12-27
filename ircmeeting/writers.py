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
def mw(text):
    """Escapes bad sequences in MediaWiki markup (not implemented yet)"""
    return text


# wraping functions (for RST)
class TextWrapper(textwrap.TextWrapper):
    wordsep_re = re.compile(r'(\s+)')
def wrapList(item, indent=0):
    return TextWrapper(width=72, initial_indent=' '*indent,
                       subsequent_indent= ' '*(indent+2),
                       break_long_words=False).fill(item)
def replaceWRAP(item):
    re_wrap = re.compile(r'sWRAPs(.*)eWRAPe', re.DOTALL)
    def repl(m):
        return TextWrapper(width=72, break_long_words=False).fill(m.group(1))
    return re_wrap.sub(repl, item)

def makeNickRE(nick):
    return re.compile('\\b'+re.escape(nick)+'\\b', re.IGNORECASE)

def MeetBotVersion():
    import meeting
    if hasattr(meeting, '__version__'):
        return ' '+meeting.__version__
    else:
        return ''


class _BaseWriter(object):
    def __init__(self, M, **kwargs):
        self.M = M

    def format(self, extension=None, **kwargs):
        """Override this method to implement the formatting.

        For file output writers, the method should return a unicode
        object containing the contents of the file to write.

        The argument 'extension' is the key from `writer_map`.  For
        file writers, this can (and should) be ignored.  For non-file
        outputs, this can be used to This can be used to pass data,

        **kwargs is a dictionary of keyword arguments which are found
        via parsing the extension to the writer.  If an extension is
        this:
          .txt|arg1=val1|arg2=val2
        then kwargs will be passed as {'arg1':'val1', 'arg2':'val2'}.
        This can be used for extra configuration for writers.
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
                'fullLogsFullURL':self.M.config.filename(url=True)+'.log.html',
                'MeetBotInfoURL':self.M.config.MeetBotInfoURL,
                'MeetBotVersion':MeetBotVersion(),
             }
    def iterNickCounts(self):
        nicks = [ (n,c) for (n,c) in self.M.attendees.iteritems() ]
        nicks.sort(key=lambda x: x[1], reverse=True)
        return nicks

    def iterActionItemsNick(self):
        for nick in sorted(self.M.attendees.keys(), key=lambda x: x.lower()):
            nick_re = makeNickRE(nick)
            def nickitems(nick_re):
                for m in self.M.minutes:
                    # The hack below is needed because of pickling problems
                    if m.itemtype != "ACTION": continue
                    if nick_re.search(m.line) is None: continue
                    m.assigned = True
                    yield m
            yield nick, nickitems(nick_re=nick_re)
    def iterActionItemsUnassigned(self):
        for m in self.M.minutes:
            if m.itemtype != "ACTION": continue
            if getattr(m, 'assigned', False): continue
            yield m

    def get_template(self, escape=lambda s: s):
        M = self.M
        repl = self.replacements()


        MeetingItems = [ ]
        # We can have initial items with NO initial topic.  This
        # messes up the templating, so, have this null topic as a
        # stopgap measure.
        nextTopic = {'topic':{'itemtype':'TOPIC', 'topic':'Prologue',
                              'nick':'',
                              'time':'', 'link':'', 'anchor':''},
                     'items':[] }
        haveTopic = False
        for m in M.minutes:
            if m.itemtype == "TOPIC":
                if nextTopic['topic']['nick'] or nextTopic['items']:
                    MeetingItems.append(nextTopic)
                nextTopic = {'topic':m.template(M, escape), 'items':[] }
                haveTopic = True
            else:
                nextTopic['items'].append(m.template(M, escape))
        MeetingItems.append(nextTopic)
        repl['MeetingItems'] = MeetingItems
        # Format of MeetingItems:
        # [ {'topic': {item_dict},
        #    'items': [item_dict, item_object, item_object, ...]
        #    },
        #   { 'topic':...
        #     'items':...
        #    },
        #   ....
        # ]
        #
        # an item_dict has:
        # item_dict = {'itemtype': TOPIC, ACTION, IDEA, or so on...
        #              'line': the actual line that was said
        #              'nick': nick of who said the line
        #              'time': 10:53:15, for example, the time
        #              'link': ${link}#${anchor} is the URL to link to.
        #                      (page name, and bookmark)
        #              'anchor': see above
        #              'topic': if itemtype is TOPIC, 'line' is not given,
        #                      instead we have 'topic'
        #              'url':  if itemtype is LINK, the line should be created
        #                      by "${link} ${line}", where 'link' is the URL
        #                      to link to, and 'line' is the rest of the line
        #                      (that isn't a URL)
        #              'url_quoteescaped': 'url' but with " escaped for use in
        #                                  <a href="$url_quoteescaped">
        ActionItems = [ ]
        for m in M.minutes:
            if m.itemtype != "ACTION": continue
            ActionItems.append(escape(m.line))
        repl['ActionItems'] = ActionItems
        # Format of ActionItems: It's just a very simple list of lines.
        # [line, line, line, ...]
        # line = (string of what it is)


        ActionItemsPerson = [ ]
        numberAssigned = 0
        for nick, items in self.iterActionItemsNick():
            thisNick = {'nick':escape(nick), 'items':[ ] }
            for m in items:
                numberAssigned += 1
                thisNick['items'].append(escape(m.line))
            if len(thisNick['items']) > 0:
                ActionItemsPerson.append(thisNick)
        # Work on the unassigned nicks.
        thisNick = {'nick':'UNASSIGNED', 'items':[ ] }
        for m in self.iterActionItemsUnassigned():
            thisNick['items'].append(escape(m.line))
        if len(thisNick['items']) > 1:
            ActionItemsPerson.append(thisNick)
        #if numberAssigned == 0:
        #    ActionItemsPerson = None
        repl['ActionItemsPerson'] = ActionItemsPerson
        # Format of ActionItemsPerson
        # ActionItemsPerson =
        #  [ {'nick':nick_of_person,
        #     'items': [item1, item2, item3, ...],
        #    },
        #   ...,
        #   ...,
        #    {'nick':'UNASSIGNED',
        #     'items': [item1, item2, item3, ...],
        #    }
        #  ]


        PeoplePresent = []
        # sort by number of lines spoken
        for nick, count in self.iterNickCounts():
            PeoplePresent.append({'nick':escape(nick),
                                  'count':count})
        repl['PeoplePresent'] = PeoplePresent
        # Format of PeoplePresent
        # [{'nick':the_nick, 'count':count_of_lines_said},
        #  ...,
        #  ...,
        # ]

        return repl

    def get_template2(self, escape=lambda s: s):
        # let's make the data structure easier to use in the template
        repl = self.get_template(escape=escape)
        repl = {
        'time':           { 'start': repl['starttime'], 'end': repl['endtime'], 'timezone': repl['timeZone'] },
        'meeting':        { 'title': repl['pageTitle'], 'owner': repl['owner'], 'logs': repl['fullLogs'], 'logsFullURL': repl['fullLogsFullURL'] },
        'attendees':      [ person for person in repl['PeoplePresent'] ],
        'agenda':         [ { 'topic': item['topic'], 'notes': item['items'] } for item in repl['MeetingItems'] ],
        'actions':        [ action for action in repl['ActionItems'] ],
        'actions_person': [ { 'nick': attendee['nick'], 'actions': attendee['items'] } for attendee in repl['ActionItemsPerson'] ],
        'meetbot':        { 'version': repl['MeetBotVersion'], 'url': repl['MeetBotInfoURL'] },
        }
        return repl


class Template(_BaseWriter):
    """Format a notes file using the genshi templating engine

    Send an argument template=<filename> to specify which template to
    use.  If `template` begins in '+', then it is relative to the
    MeetBot source directory.  Included templates are:
      +template.html
      +template.txt

    Some examples of using these options are:
      writer_map['.txt|template=+template.html'] = writers.Template
      writer_map['.txt|template=/home/you/template.txt] = writers.Template

    If a template ends in .txt, parse with a text-based genshi
    templater.  Otherwise, parse with a HTML-based genshi templater.
    """
    def format(self, extension=None, template='+template.html'):
        repl = self.get_template2()

        # Do we want to use a text template or HTML ?
        import genshi.template
        if template[-4:] in ('.txt', '.rst'):
            Template = genshi.template.NewTextTemplate   # plain text
        else:
            Template = genshi.template.MarkupTemplate    # HTML-like

        template = self.M.config.findFile(template)

        # Do the actual templating work
        try:
            f = open(template, 'r')
            tmpl = Template(f.read())
            stream = tmpl.generate(**repl)
        finally:
            f.close()

        return stream.render()



class _CSSmanager(object):
    _css_head = textwrap.dedent('''\
        <style type="text/css">
        %s
        </style>
        ''')
    def getCSS(self, name):
        cssfile = getattr(self.M.config, 'cssFile_'+name, '')
        if cssfile.lower() == 'none':
            # special string 'None' means no style at all
            return ''
        elif cssfile in ('', 'default'):
            # default CSS file
            css_fname = '+css-'+name+'-default.css'
        else:
            css_fname = cssfile
        css_fname = self.M.config.findFile(css_fname)
        try:
            # Stylesheet specified
            if getattr(self.M.config, 'cssEmbed_'+name, True):
                # external stylesheet
                css = file(css_fname).read()
                return self._css_head%css
            else:
                # linked stylesheet
                css_head = ('''<link rel="stylesheet" type="text/css" '''
                            '''href="%s">'''%cssfile)
                return css_head
        except Exception, exc:
            if not self.M.config.safeMode:
                raise
            import traceback
            traceback.print_exc()
            print "(exception above ignored, continuing)"
            try:
                css_fname = os.path.join(os.path.dirname(__file__),
                                         'css-'+name+'-default.css')
                css = open(css_fname).read()
                return self._css_head%css
            except:
                if not self.M.config.safeMode:
                    raise
                import traceback
                traceback.print_exc()
                return ''


class TextLog(_BaseWriter):
    def format(self, extension=None):
        M = self.M
        """Write raw text logs."""
        return "\n".join(M.lines)
    update_realtime = True



class HTMLlog1(_BaseWriter):
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
                                  outencoding=self.M.config.output_codec)
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
        # Hack it to add "pre { white-space: pre-wrap; }", which make
        # it wrap the pygments html logs.  I think that in a newer
        # version of pygmetns, the "prestyles" HTMLFormatter option
        # would do this, but I want to maintain compatibility with
        # lenny.  Thus, I do these substitution hacks to add the
        # format in.  Thanks to a comment on the blog of Francis
        # Giannaros (http://francis.giannaros.org) for the suggestion
        # and instructions for how.
        out,n = re.subn(r"(\n\s*pre\s*\{[^}]+;\s*)(\})",
                        r"\1\n      white-space: pre-wrap;\2",
                        out, count=1)
        if n == 0:
            out = re.sub(r"(\n\s*</style>)",
                         r"\npre { white-space: pre-wrap; }\1",
                         out, count=1)
        return out

class HTMLlog2(_BaseWriter, _CSSmanager):
    def format(self, extension=None):
        """Write pretty HTML logs."""
        M = self.M
        lines = [ ]
        line_re = re.compile(r"""\s*
            (?P<time> \[?[0-9:\s]*\]?)\s*
            (?P<nick>\s+<[@+\s]?[^>]+>)\s*
            (?P<line>.*)
        """, re.VERBOSE)
        action_re = re.compile(r"""\s*
            (?P<time> \[?[0-9:\s]*\]?)\s*
            (?P<nick>\*\s+[@+\s]?[^\s]+)\s*
            (?P<line>.*)
        """,re.VERBOSE)
        command_re = re.compile(r"(#[^\s]+[ \t\f\v]*)(.*)")
        command_topic_re = re.compile(r"(#topic[ \t\f\v]*)(.*)")
        hilight_re = re.compile(r"([^\s]+:)( .*)")
        lineNumber = 0
        for l in M.lines:
            lineNumber += 1  # starts from 1
            # is it a regular line?
            m = line_re.match(l)
            if m is not None:
                line = m.group('line')
                # Match #topic
                m2 = command_topic_re.match(line)
                if m2 is not None:
                    outline = ('<span class="topic">%s</span>'
                               '<span class="topicline">%s</span>'%
                               (html(m2.group(1)),html(m2.group(2))))
                # Match other #commands
                if m2 is None:
                  m2 = command_re.match(line)
                  if m2 is not None:
                    outline = ('<span class="cmd">%s</span>'
                               '<span class="cmdline">%s</span>'%
                               (html(m2.group(1)),html(m2.group(2))))
                # match hilights
                if m2 is None:
                  m2 = hilight_re.match(line)
                  if m2 is not None:
                    outline = ('<span class="hi">%s</span>'
                               '%s'%
                               (html(m2.group(1)),html(m2.group(2))))
                if m2 is None:
                    outline = html(line)
                lines.append('<a name="l-%(lineno)s"></a>'
                             '<span class="tm">%(time)s</span>'
                             '<span class="nk">%(nick)s</span> '
                             '%(line)s'%{'lineno':lineNumber,
                                         'time':html(m.group('time')),
                                         'nick':html(m.group('nick')),
                                         'line':outline,})
                continue
            m = action_re.match(l)
            # is it a action line?
            if m is not None:
                lines.append('<a name="l-%(lineno)s"></a>'
                             '<span class="tm">%(time)s</span>'
                             '<span class="nka">%(nick)s</span> '
                             '<span class="ac">%(line)s</span>'%
                               {'lineno':lineNumber,
                                'time':html(m.group('time')),
                                'nick':html(m.group('nick')),
                                'line':html(m.group('line')),})
                continue
            print l
            print m.groups()
            print "**error**", l

        css = self.getCSS(name='log')
        return html_template%{'pageTitle':"%s log"%html(M.channel),
                              #'body':"<br>\n".join(lines),
                              'body':"<pre>"+("\n".join(lines))+"</pre>",
                              'headExtra':css,
                              }
HTMLlog = HTMLlog2



html_template = textwrap.dedent('''\
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
    <html>
    <head>
    <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
    <title>%(pageTitle)s</title>
    %(headExtra)s</head>

    <body>
    %(body)s
    </body></html>
    ''')


class HTML1(_BaseWriter):

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



class HTML2(_BaseWriter, _CSSmanager):
    """HTML formatter without tables.
    """
    def meetingItems(self):
        """Return the main 'Meeting minutes' block."""
        M = self.M

        # Add all minute items to the table
        MeetingItems = [ ]
        MeetingItems.append(self.heading('Meeting summary'))
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
                    if not haveTopic:
                        MeetingItems.append('<li>')
                        haveTopic = True
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
        return MeetingItems

    def actionItems(self):
        """Return the 'Action items' block."""
        M = self.M
        # Action Items
        ActionItems = [ ]
        ActionItems.append(self.heading('Action items'))
        ActionItems.append('<ol>')
        numActionItems = 0
        for m in M.minutes:
            # The hack below is needed because of pickling problems
            if m.itemtype != "ACTION": continue
            ActionItems.append("  <li>%s</li>"%html(m.line))
            numActionItems += 1
        if numActionItems == 0:
            ActionItems.append("  <li>(none)</li>")
        ActionItems.append('</ol>')
        ActionItems = "\n".join(ActionItems)
        return ActionItems
    def actionItemsPerson(self):
        """Return the 'Action items, by person' block."""
        M = self.M
        # Action Items, by person (This could be made lots more efficient)
        ActionItemsPerson = [ ]
        ActionItemsPerson.append(self.heading('Action items, by person'))
        ActionItemsPerson.append('<ol>')
        numberAssigned = 0
        for nick, items in self.iterActionItemsNick():
            headerPrinted = False
            for m in items:
                numberAssigned += 1
                if not headerPrinted:
                    ActionItemsPerson.append("  <li> %s <ol>"%html(nick))
                    headerPrinted = True
                ActionItemsPerson.append("    <li>%s</li>"%html(m.line))
            if headerPrinted:
                ActionItemsPerson.append("  </ol></li>")
        # unassigned items:
        if len(ActionItemsPerson) == 0:
            doActionItemsPerson = False
        else:
            doActionItemsPerson = True
        Unassigned = [ ]
        Unassigned.append("  <li><b>UNASSIGNED</b><ol>")
        numberUnassigned = 0
        for m in self.iterActionItemsUnassigned():
            Unassigned.append("    <li>%s</li>"%html(m.line))
            numberUnassigned += 1
        if numberUnassigned == 0:
            Unassigned.append("    <li>(none)</li>")
        Unassigned.append('  </ol>\n</li>')
        if numberUnassigned > 1:
            ActionItemsPerson.extend(Unassigned)
        ActionItemsPerson.append('</ol>')
        ActionItemsPerson = "\n".join(ActionItemsPerson)

        # Only return anything if there are assigned items.
        if numberAssigned == 0:
            return None
        else:
            return ActionItemsPerson
    def peoplePresent(self):
        """Return the 'People present' block."""
        # People Attending
        PeoplePresent = []
        PeoplePresent.append(self.heading('People present (lines said)'))
        PeoplePresent.append('<ol>')
        # sort by number of lines spoken
        for nick, count in self.iterNickCounts():
            PeoplePresent.append('  <li>%s (%s)</li>'%(html(nick), count))
        PeoplePresent.append('</ol>')
        PeoplePresent = "\n".join(PeoplePresent)
        return PeoplePresent
    def heading(self, name):
        return '<h3>%s</h3>'%name

    def format(self, extension=None):
        """Write the minutes summary."""
        M = self.M

        repl = self.replacements()

        body = [ ]
        body.append(textwrap.dedent("""\
            <h1>%(pageTitle)s</h1>
            <span class="details">
            Meeting started by %(owner)s at %(starttime)s %(timeZone)s
            (<a href="%(fullLogs)s">full logs</a>).</span>
            """%repl))
        body.append(self.meetingItems())
        body.append(textwrap.dedent("""\
            <span class="details">
            Meeting ended at %(endtime)s %(timeZone)s
            (<a href="%(fullLogs)s">full logs</a>).</span>
            """%repl))
        body.append(self.actionItems())
        body.append(self.actionItemsPerson())
        body.append(self.peoplePresent())
        body.append("""<span class="details">"""
                    """Generated by <a href="%(MeetBotInfoURL)s">MeetBot</a>"""
                    """%(MeetBotVersion)s.</span>"""%repl)
        body = [ b for b in body if b is not None ]
        body = "\n<br><br>\n\n\n\n".join(body)
        body = replaceWRAP(body)


        css = self.getCSS(name='minutes')
        repl.update({'body': body,
                     'headExtra': css,
                     })
        html = html_template % repl

        return html
HTML = HTML2


class ReST(_BaseWriter):

    body = textwrap.dedent("""\
    %(titleBlock)s
    %(pageTitle)s
    %(titleBlock)s


    sWRAPsMeeting started by %(owner)s at %(starttime)s %(timeZone)s.
    The `full logs`_ are available.eWRAPe

    .. _`full logs`: %(fullLogs)s



    Meeting summary
    ---------------
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
                if haveTopic:
                    MeetingItems.append("")
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
            nick_re = makeNickRE(nick)
            headerPrinted = False
            for m in M.minutes:
                # The hack below is needed because of pickling problems
                if m.itemtype != "ACTION": continue
                if nick_re.search(m.line) is None: continue
                if not headerPrinted:
                    ActionItemsPerson.append("* %s"%rst(nick))
                    headerPrinted = True
                ActionItemsPerson.append(wrapList("* %s"%rst(m.line), 2))
                m.assigned = True
        # unassigned items:
        Unassigned = [ ]
        Unassigned.append("* **UNASSIGNED**")
        numberUnassigned = 0
        for m in M.minutes:
            if m.itemtype != "ACTION": continue
            if getattr(m, 'assigned', False): continue
            Unassigned.append(wrapList("* %s"%rst(m.line), 2))
            numberUnassigned += 1
        if numberUnassigned == 0:
            Unassigned.append("  * (none)")
        if numberUnassigned > 1:
            ActionItemsPerson.extend(Unassigned)
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
        body = body%repl
        body = replaceWRAP(body)
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

    def meetingItems(self):
        M = self.M

        # Agenda items
        MeetingItems = [ ]
        MeetingItems.append(self.heading('Meeting summary'))
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
        return MeetingItems

    def actionItems(self):
        M = self.M
        # Action Items
        ActionItems = [ ]
        numActionItems = 0
        ActionItems.append(self.heading('Action items'))
        for m in M.minutes:
            # The hack below is needed because of pickling problems
            if m.itemtype != "ACTION": continue
            #already escaped
            ActionItems.append(wrapList("* %s"%text(m.line), indent=0))
            numActionItems += 1
        if numActionItems == 0:
            ActionItems.append("* (none)")
        ActionItems = "\n".join(ActionItems)

    def actionItemsPerson(self):
        M = self.M
        # Action Items, by person (This could be made lots more efficient)
        ActionItemsPerson = [ ]
        ActionItemsPerson.append(self.heading('Action items, by person'))
        numberAssigned = 0
        for nick in sorted(M.attendees.keys(), key=lambda x: x.lower()):
            nick_re = makeNickRE(nick)
            headerPrinted = False
            for m in M.minutes:
                # The hack below is needed because of pickling problems
                if m.itemtype != "ACTION": continue
                if nick_re.search(m.line) is None: continue
                if not headerPrinted:
                    ActionItemsPerson.append("* %s"%text(nick))
                    headerPrinted = True
                ActionItemsPerson.append(wrapList("* %s"%text(m.line), 2))
                numberAssigned += 1
                m.assigned = True
        # unassigned items:
        Unassigned = [ ]
        Unassigned.append("* **UNASSIGNED**")
        numberUnassigned = 0
        for m in M.minutes:
            if m.itemtype != "ACTION": continue
            if getattr(m, 'assigned', False): continue
            Unassigned.append(wrapList("* %s"%text(m.line), 2))
            numberUnassigned += 1
        if numberUnassigned == 0:
            Unassigned.append("  * (none)")
        if numberUnassigned > 1:
            ActionItemsPerson.extend(Unassigned)
        ActionItemsPerson = "\n".join(ActionItemsPerson)

        if numberAssigned == 0:
            return None
        else:
            return ActionItemsPerson

    def peoplePresent(self):
        M = self.M
        # People Attending
        PeoplePresent = [ ]
        PeoplePresent.append(self.heading('People present (lines said)'))
        # sort by number of lines spoken
        for nick, count in self.iterNickCounts():
            PeoplePresent.append('* %s (%s)'%(text(nick), count))
        PeoplePresent = "\n".join(PeoplePresent)
        return PeoplePresent

    def heading(self, name):
        return '%s\n%s\n'%(name, '-'*len(name))


    def format(self, extension=None):
        """Return a plain text minutes summary."""
        M = self.M

        # Actual formatting and replacement
        repl = self.replacements()
        repl.update({'titleBlock':('='*len(repl['pageTitle'])),
                     })


        body = [ ]
        body.append(textwrap.dedent("""\
            %(titleBlock)s
            %(pageTitle)s
            %(titleBlock)s


            sWRAPsMeeting started by %(owner)s at %(starttime)s
            %(timeZone)s.  The full logs are available at
            %(fullLogsFullURL)s .eWRAPe"""%repl))
        body.append(self.meetingItems())
        body.append(textwrap.dedent("""\
            Meeting ended at %(endtime)s %(timeZone)s."""%repl))
        body.append(self.actionItems())
        body.append(self.actionItemsPerson())
        body.append(self.peoplePresent())
        body.append(textwrap.dedent("""\
            Generated by `MeetBot`_%(MeetBotVersion)s"""%repl))
        body = [ b for b in body if b is not None ]
        body = "\n\n\n\n".join(body)
        body = replaceWRAP(body)

        return body


class MediaWiki(_BaseWriter):
    """Outputs MediaWiki formats.
    """
    def meetingItems(self):
        M = self.M

        # Agenda items
        MeetingItems = [ ]
        MeetingItems.append(self.heading('Meeting summary'))
        haveTopic = None
        for m in M.minutes:
            item = "* "+m.mw(M)
            if m.itemtype == "TOPIC":
                if haveTopic:
                    MeetingItems.append("") # line break
                haveTopic = True
            else:
                if haveTopic: item = "*"+item
            MeetingItems.append(item)
        MeetingItems = '\n'.join(MeetingItems)
        return MeetingItems

    def actionItems(self):
        M = self.M
        # Action Items
        ActionItems = [ ]
        numActionItems = 0
        ActionItems.append(self.heading('Action items'))
        for m in M.minutes:
            # The hack below is needed because of pickling problems
            if m.itemtype != "ACTION": continue
            #already escaped
            ActionItems.append("* %s"%mw(m.line))
            numActionItems += 1
        if numActionItems == 0:
            ActionItems.append("* (none)")
        ActionItems = "\n".join(ActionItems)
        return ActionItems

    def actionItemsPerson(self):
        M = self.M
        # Action Items, by person (This could be made lots more efficient)
        ActionItemsPerson = [ ]
        ActionItemsPerson.append(self.heading('Action items, by person'))
        numberAssigned = 0
        for nick in sorted(M.attendees.keys(), key=lambda x: x.lower()):
            nick_re = makeNickRE(nick)
            headerPrinted = False
            for m in M.minutes:
                # The hack below is needed because of pickling problems
                if m.itemtype != "ACTION": continue
                if nick_re.search(m.line) is None: continue
                if not headerPrinted:
                    ActionItemsPerson.append("* %s"%mw(nick))
                    headerPrinted = True
                ActionItemsPerson.append("** %s"%mw(m.line))
                numberAssigned += 1
                m.assigned = True
        # unassigned items:
        Unassigned = [ ]
        Unassigned.append("* **UNASSIGNED**")
        numberUnassigned = 0
        for m in M.minutes:
            if m.itemtype != "ACTION": continue
            if getattr(m, 'assigned', False): continue
            Unassigned.append("** %s"%mw(m.line))
            numberUnassigned += 1
        if numberUnassigned == 0:
            Unassigned.append("  * (none)")
        if numberUnassigned > 1:
            ActionItemsPerson.extend(Unassigned)
        ActionItemsPerson = "\n".join(ActionItemsPerson)

        if numberAssigned == 0:
            return None
        else:
            return ActionItemsPerson

    def peoplePresent(self):
        M = self.M
        # People Attending
        PeoplePresent = [ ]
        PeoplePresent.append(self.heading('People present (lines said)'))
        # sort by number of lines spoken
        for nick, count in self.iterNickCounts():
            PeoplePresent.append('* %s (%s)'%(mw(nick), count))
        PeoplePresent = "\n".join(PeoplePresent)
        return PeoplePresent

    def heading(self, name, level=1):
        return '%s %s %s\n'%('='*(level+1), name, '='*(level+1))


    body_start = textwrap.dedent("""\
            %(pageTitleHeading)s

            sWRAPsMeeting started by %(owner)s at %(starttime)s
            %(timeZone)s.  The full logs are available at
            %(fullLogsFullURL)s .eWRAPe""")
    def format(self, extension=None, **kwargs):
        """Return a MediaWiki formatted minutes summary."""
        M = self.M

        # Actual formatting and replacement
        repl = self.replacements()
        repl.update({'titleBlock':('='*len(repl['pageTitle'])),
                     'pageTitleHeading':self.heading(repl['pageTitle'],level=0)
                     })


        body = [ ]
        body.append(self.body_start%repl)
        body.append(self.meetingItems())
        body.append(textwrap.dedent("""\
            Meeting ended at %(endtime)s %(timeZone)s."""%repl))
        body.append(self.actionItems())
        body.append(self.actionItemsPerson())
        body.append(self.peoplePresent())
        body.append(textwrap.dedent("""\
            Generated by MeetBot%(MeetBotVersion)s (%(MeetBotInfoURL)s)"""%repl))
        body = [ b for b in body if b is not None ]
        body = "\n\n\n\n".join(body)
        body = replaceWRAP(body)


        # Do we want to upload?
        if 'mwpath' in kwargs:
            import mwclient
            mwsite = kwargs['mwsite']
            mwpath = kwargs['mwpath']
            mwusername = kwargs.get('mwusername', None)
            mwpassword = kwargs.get('mwpassword', '')
            subpagename = os.path.basename(self.M.config.filename())
            mwfullname = "%s/%s" % (mwpath, subpagename)
            force_login = (mwusername != None)

            site = mwclient.Site(mwsite, force_login=force_login)
            if(force_login):
                site.login(mwusername, mwpassword)
            page = site.Pages[mwfullname]
            some = page.edit()
            page.save(body, summary="Meeting")


        return body

class PmWiki(MediaWiki, object):
    def heading(self, name, level=1):
        return '%s %s\n'%('!'*(level+1), name)
    def replacements(self):
        #repl = super(PmWiki, self).replacements(self) # fails, type checking
        repl = MediaWiki.replacements.im_func(self)
        repl['pageTitleHeading'] = self.heading(repl['pageTitle'],level=0)
        return repl



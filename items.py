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
import time

import writers
#from writers import html, rst
import itertools

def inbase(i, chars='abcdefghijklmnopqrstuvwxyz', place=0):
    """Converts an integer into a postfix in base 26 using ascii chars.

    This is used to make a unique postfix for ReStructured Text URL
    references, which must be unique.  (Yes, this is over-engineering,
    but keeps it short and nicely arranged, and I want practice
    writing recursive functions.)
    """
    div, mod = divmod(i, len(chars)**(place+1))
    if div == 0:
        return chars[mod]
    else:
        return inbase2(div, chars=chars, place=place+1)+chars[mod]



#
# These are objects which we can add to the meeting minutes.  Mainly
# they exist to aid in HTML-formatting.
#
class _BaseItem(object):
    itemtype = None
    starthtml = ''
    endhtml = ''
    startrst = ''
    endrst = ''
    starttext = ''
    endtext = ''
    def get_replacements(self, escapewith):
        replacements = { }
        for name in dir(self):
            if name[0] == "_": continue
            replacements[name] = getattr(self, name)
        replacements['nick'] = escapewith(replacements['nick'])
        if 'line' in replacements:
            replacements['line'] = escapewith(replacements['line'])
        if 'topic' in replacements:
            replacements['topic'] = escapewith(replacements['topic'])
        return replacements
    def makeRSTref(self, M):
        if self.nick[-1] == '_':
            rstref = rstref_orig = "%s%s"%(self.nick, self.time)
        else:
            rstref = rstref_orig = "%s-%s"%(self.nick, self.time)
        count = 0
        while rstref in M.rst_refs:
            rstref = rstref_orig + inbase(count)
            count += 1
        link = self.logURL(M)
        M.rst_urls.append(".. _%s: %s"%(rstref, link+"#"+self.anchor))
        M.rst_refs[rstref] = True
        return rstref
    @property
    def anchor(self):
        return 'l-'+str(self.linenum)
    def logURL(self, M):
        return M.config.basename+'.log.html'

class Topic(_BaseItem):
    itemtype = 'TOPIC'
    html_template = """<tr><td><a href='%(link)s#%(anchor)s'>%(time)s</a></td>
        <th colspan=3>%(starthtml)sTopic: %(topic)s%(endhtml)s</th>
        </tr>"""
    #html2_template = ("""<b>%(starthtml)s%(topic)s%(endhtml)s</b> """
    #                  """(%(nick)s, <a href='%(link)s#%(anchor)s'>%(time)s</a>)""")
    html2_template = ("""%(starthtml)s%(topic)s%(endhtml)s """
                      """<span class="details">"""
                      """(<a href='%(link)s#%(anchor)s'>%(nick)s</a>, """
                      """%(time)s)"""
                      """</span>""")
    rst_template = """%(startrst)s%(topic)s%(endrst)s  (%(rstref)s_)"""
    text_template = """%(starttext)s%(topic)s%(endtext)s  (%(nick)s, %(time)s)"""
    startrst = '**'
    endrst = '**'
    starthtml = '<b class="TOPIC">'
    endhtml = '</b>'
    def __init__(self, nick, line, linenum, time_):
        self.nick = nick ; self.topic = line ; self.linenum = linenum
        self.time = time.strftime("%H:%M:%S", time_)
    def _htmlrepl(self, M):
        repl = self.get_replacements(escapewith=writers.html)
        repl['link'] = self.logURL(M)
        return repl
    def html(self, M):
        return self.html_template%self._htmlrepl(M)
    def html2(self, M):
        return self.html2_template%self._htmlrepl(M)
    def rst(self, M):
        self.rstref = self.makeRSTref(M)
        repl = self.get_replacements(escapewith=writers.rst)
        if repl['topic']=='': repl['topic']=' '
        repl['link'] = self.logURL(M)
        return self.rst_template%repl
    def text(self, M):
        repl = self.get_replacements(escapewith=writers.text)
        repl['link'] = self.logURL(M)
        return self.text_template%repl

class GenericItem(_BaseItem):
    itemtype = ''
    html_template = """<tr><td><a href='%(link)s#%(anchor)s'>%(time)s</a></td>
        <td>%(itemtype)s</td><td>%(nick)s</td><td>%(starthtml)s%(line)s%(endhtml)s</td>
        </tr>"""
    #html2_template = ("""<i>%(itemtype)s</i>: %(starthtml)s%(line)s%(endhtml)s """
    #                  """(%(nick)s, <a href='%(link)s#%(anchor)s'>%(time)s</a>)""")
    html2_template = ("""<i class="itemtype">%(itemtype)s</i>: """
                      """<span class="%(itemtype)s">"""
                      """%(starthtml)s%(line)s%(endhtml)s</span> """
                      """<span class="details">"""
                      """(<a href='%(link)s#%(anchor)s'>%(nick)s</a>, """
                      """%(time)s)"""
                      """</span>""")
    rst_template = """*%(itemtype)s*: %(startrst)s%(line)s%(endrst)s  (%(rstref)s_)"""
    text_template = """%(itemtype)s: %(starttext)s%(line)s%(endtext)s  (%(nick)s, %(time)s)"""
    def __init__(self, nick, line, linenum, time_):
        self.nick = nick ; self.line = line ; self.linenum = linenum
        self.time = time.strftime("%H:%M:%S", time_)
    def _htmlrepl(self, M):
        repl = self.get_replacements(escapewith=writers.html)
        repl['link'] = self.logURL(M)
        return repl
    def html(self, M):
        return self.html_template%self._htmlrepl(M)
    def html2(self, M):
        return self.html2_template%self._htmlrepl(M)
    def rst(self, M):
        self.rstref = self.makeRSTref(M)
        repl = self.get_replacements(escapewith=writers.rst)
        repl['link'] = self.logURL(M)
        return self.rst_template%repl
    def text(self, M):
        repl = self.get_replacements(escapewith=writers.text)
        repl['link'] = self.logURL(M)
        return self.text_template%repl


class Info(GenericItem):
    itemtype = 'INFO'
    html2_template = ("""<span class="%(itemtype)s">"""
                      """%(starthtml)s%(line)s%(endhtml)s</span> """
                      """<span class="details">"""
                      """(<a href='%(link)s#%(anchor)s'>%(nick)s</a>, """
                      """%(time)s)"""
                      """</span>""")
    rst_template = """%(startrst)s%(line)s%(endrst)s  (%(rstref)s_)"""
    text_template = """%(starttext)s%(line)s%(endtext)s  (%(nick)s, %(time)s)"""
class Idea(GenericItem):
    itemtype = 'IDEA'
class Agreed(GenericItem):
    itemtype = 'AGREED'
class Action(GenericItem):
    itemtype = 'ACTION'
class Help(GenericItem):
    itemtype = 'HELP'
class Accepted(GenericItem):
    itemtype = 'ACCEPTED'
    starthtml = '<font color="green">'
    endhtml = '</font>'
class Rejected(GenericItem):
    itemtype = 'REJECTED'
    starthtml = '<font color="red">'
    endhtml = '</font>'
class Link(_BaseItem):
    itemtype = 'LINK'
    html_template = """<tr><td><a href='%(link)s#%(anchor)s'>%(time)s</a></td>
        <td>%(itemtype)s</td><td>%(nick)s</td><td>%(starthtml)s<a href="%(url)s">%(url_readable)s</a> %(line)s%(endhtml)s</td>
        </tr>"""
    #html2_template = ("""<i>%(itemtype)s</i>: %(starthtml)s<a href="%(url)s">%(url_readable)s</a> %(line)s%(endhtml)s """
    #                  """(%(nick)s, <a href='%(link)s#%(anchor)s'>%(time)s</a>)""")
    #html2_template = ("""<i>%(itemtype)s</i>: %(starthtml)s<a href="%(url)s">%(url_readable)s</a> %(line)s%(endhtml)s """
    #                  """(<a href='%(link)s#%(anchor)s'>%(nick)s</a>, %(time)s)""")
    html2_template = ("""%(starthtml)s<a href="%(url)s">%(url_readable)s</a> %(line)s%(endhtml)s """
                      """<span class="details">"""
                      """(<a href='%(link)s#%(anchor)s'>%(nick)s</a>, """
                      """%(time)s)"""
                      """</span>""")
    rst_template = """*%(itemtype)s*: %(startrst)s%(url)s %(line)s%(endrst)s  (%(rstref)s_)"""
    text_template = """%(itemtype)s: %(starttext)s%(url)s %(line)s%(endtext)s  (%(nick)s, %(time)s)"""
    def __init__(self, nick, line, linenum, time_):
        self.nick = nick ; self.linenum = linenum
        self.time = time.strftime("%H:%M:%S", time_)
        self.url, self.line = (line+' ').split(' ', 1)
        # URL-sanitization
        self.url_readable = self.url # readable line version
        self.url = self.url
        self.line = self.line.strip()
    def _htmlrepl(self, M):
        repl = self.get_replacements(escapewith=writers.html)
        # special: replace doublequote only for the URL.
        repl['url'] = writers.html(self.url.replace('"', "%22"))
        repl['url_readable'] = writers.html(self.url)
        repl['link'] = self.logURL(M)
        return repl
    def html(self, M):
        return self.html_template%self._htmlrepl(M)
    def html2(self, M):
        return self.html2_template%self._htmlrepl(M)
    def rst(self, M):
        self.rstref = self.makeRSTref(M)
        repl = self.get_replacements(escapewith=writers.rst)
        repl['link'] = self.logURL(M)
        #repl['url'] = writers.rst(self.url)
        return self.rst_template%repl
    def text(self, M):
        repl = self.get_replacements(escapewith=writers.text)
        repl['link'] = self.logURL(M)
        return self.text_template%repl

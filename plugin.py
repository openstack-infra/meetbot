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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.ircmsgs as ircmsgs

import time
import meeting
import supybotconfig
# Because of the way we override names, we need to reload these in order.
meeting = reload(meeting)
supybotconfig = reload(supybotconfig)

if supybotconfig.is_supybotconfig_enabled(meeting.Config):
    supybotconfig.setup_config(meeting.Config)
    meeting.Config = supybotconfig.get_config_proxy(meeting.Config)

# By doing this, we can not lose all of our meetings across plugin
# reloads.  But, of course, you can't change the source too
# drastically if you do that!
try:               meeting_cache
except NameError:  meeting_cache = {}
try:               recent_meetings
except NameError:  recent_meetings = [ ]


class MeetBot(callbacks.Plugin):
    """Add the help for "@plugin help MeetBot" here
    This should describe *how* to use this plugin."""

    def __init__(self, irc):
        self.__parent = super(MeetBot, self)
        self.__parent.__init__(irc)
                        
    # Instead of using real supybot commands, I just listen to ALL
    # messages coming in and respond to those beginning with our
    # prefix char.  I found this helpful from a not duplicating logic
    # standpoint (as well as other things).  Ask me if you have more
    # questions.

    # This captures all messages coming into the bot.
    def doPrivmsg(self, irc, msg):
        nick = msg.nick
        channel = msg.args[0]
        payload = msg.args[1]

        # The following is for debugging.  It's excellent to get an
        # interactive interperter inside of the live bot.  use
        # code.interact instead of my souped-up version if you aren't
        # on my computer:
        #if payload == 'interact':
        #    from rkddp.interact import interact ; interact()

        # Get our Meeting object, if one exists.  Have to keep track
        # of different servers/channels.
        # (channel, network) tuple is our lookup key.
        Mkey = (channel,irc.msg.tags['receivedOn']) 
        M = meeting_cache.get(Mkey, None)

        # Start meeting if we are requested
        if payload[:13] == '#startmeeting':
            if M is not None:
                irc.error("Can't start another meeting, one is in progress.")
                return
            # This callback is used to send data to the channel:
            def _setTopic(x):
                irc.sendMsg(ircmsgs.topic(channel, x))
            def _sendReply(x):
                irc.sendMsg(ircmsgs.privmsg(channel, x))
            M = meeting.Meeting(channel=channel, owner=nick,
                                oldtopic=irc.state.channels[channel].topic,
                                writeRawLog=True,
                                setTopic = _setTopic, sendReply = _sendReply,
                                getRegistryValue = self.registryValue,
                                safeMode=True
                                )
            meeting_cache[Mkey] = M
            recent_meetings.append(
                (channel, irc.msg.tags['receivedOn'], time.ctime()))
            if len(recent_meetings) > 10:
                del recent_meetings[0]
        # If there is no meeting going on, then we quit
        if M is None: return
        # Add line to our meeting buffer.
        M.addline(nick, payload)
        # End meeting if requested:
        if M._meetingIsOver:
            #M.save()  # now do_endmeeting in M calls the save functions
            del meeting_cache[Mkey]

    def outFilter(self, irc, msg):
        """Log outgoing messages from supybot.
        """
        # Catch supybot's own outgoing messages to log them.  Run the
        # whole thing in a try: block to prevent all output from
        # getting clobbered.
        try:
            if msg.command in ('PRIVMSG'):
                # Note that we have to get our nick and network parameters
                # in a slightly different way here, compared to doPrivmsg.
                nick = irc.nick
                channel = msg.args[0]
                payload = msg.args[1]
                Mkey = (channel,irc.network)
                M = meeting_cache.get(Mkey, None)
                if M is not None:
                    M.addrawline(nick, payload)
        except:
            import traceback
            print traceback.print_exc()
            print "(above exception in outFilter, ignoring)"
        return msg

    # These are admin commands, for use by the bot owner when there
    # are many channels which may need to be independently managed.
    def listmeetings(self, irc, msg, args):
        """

        List all currently-active meetings."""
        reply = ""
        reply = ", ".join(str(x) for x in sorted(meeting_cache.keys()) )
        if reply.strip() == '':
            irc.reply("No currently active meetings.")
        else:
            irc.reply(reply)
    listmeetings = wrap(listmeetings, ['admin'])
    def savemeetings(self, irc, msg, args):
        """

        Save all currently active meetings."""
        numSaved = 0
        for M in meeting_cache.iteritems():
            M.config.save()
        irc.reply("Saved %d meetings."%numSaved)
    savemeetings = wrap(savemeetings, ['admin'])
    def addchair(self, irc, msg, args, channel, network, nick):
        """<channel> <network> <nick>

        Add a nick as a chair to the meeting."""
        Mkey = (channel,network)
        M = meeting_cache.get(Mkey, None)
        if not M:
            irc.reply("Meeting on channel %s, network %s not found"%(
                channel, network))
            return
        M.chairs.setdefault(nick, True)
        irc.reply("Chair added: %s on (%s, %s)."%(nick, channel, network))
    addchair = wrap(addchair, ['admin', "channel", "something", "nick"])
    def deletemeeting(self, irc, msg, args, channel, network, save):
        """<channel> <network> <saveit=True>

        Delete a meeting from the cache.  If save is given, save the
        meeting first, defaults to saving."""
        Mkey = (channel,network)
        if Mkey not in meeting_cache:
            irc.reply("Meeting on channel %s, network %s not found"%(
                channel, network))
            return
        if save:
            M = meeting_cache.get(Mkey, None)
            import time
            M.endtime = time.localtime()
            M.config.save()
        del meeting_cache[Mkey]
        irc.reply("Deleted: meeting on (%s, %s)."%(channel, network))
    deletemeeting = wrap(deletemeeting, ['admin', "channel", "something",
                               optional("boolean", True)])
    def recent(self, irc, msg, args):
        """

        List recent meetings for admin purposes.
        """
        reply = []
        for channel, network, ctime in recent_meetings:
            Mkey = (channel,network)
            if Mkey in meeting_cache:   state = ", running"
            else:                       state = ""
            reply.append("(%s, %s, %s%s)"%(channel, network, ctime, state))
        if reply:
            irc.reply(" ".join(reply))
        else:
            irc.reply("No recent meetings in internal state.")
    recent = wrap(recent, ['admin'])

    def pingall(self, irc, msg, args, message):
        """<text>

        Send a broadcast ping to all users on the channel.

        An message to be sent along with this ping must also be
        supplied for this command to work.
        """
        nick = msg.nick
        channel = msg.args[0]
        payload = msg.args[1]

        # We require a message to go out with the ping, we don't want
        # to waste people's time:
        if channel[0] != '#':
            irc.reply("Not joined to any channel.")
            return
        if message is None:
            irc.reply("You must supply a description with the `pingall` command.  We don't want to go wasting people's times looking for why they are pinged.")
            return

        # Send announcement message
        irc.sendMsg(ircmsgs.privmsg(channel, message))
        # ping all nicks in lines of about 256
        nickline = ''
        nicks = sorted(irc.state.channels[channel].users,
                       key=lambda x: x.lower())
        for nick in nicks:
            nickline = nickline + nick + ' '
            if len(nickline) > 256:
                irc.sendMsg(ircmsgs.privmsg(channel, nickline))
                nickline = ''
        irc.sendMsg(ircmsgs.privmsg(channel, nickline))
        # Send announcement message
        irc.sendMsg(ircmsgs.privmsg(channel, message))

    pingall = wrap(pingall, [optional('text', None)])

    def __getattr__(self, name):
        """Proxy between proper supybot commands and # MeetBot commands.

        This allows you to use MeetBot: <command> <line of the command>
        instead of the typical #command version.  However, it's disabled
        by default as there are some possible unresolved issues with it.

        To enable this, you must comment out a line in the main code.
        It may be enabled in a future version.
        """
        # First, proxy to our parent classes (__parent__ set in __init__)
        try:
            return self.__parent.__getattr__(name)
        except AttributeError:
            pass
        # Disabled for now.  Uncomment this if you want to use this.
        raise AttributeError

        if not hasattr(meeting.Meeting, "do_"+name):
            raise AttributeError

        def wrapped_function(self, irc, msg, args, message):
            channel = msg.args[0]
            payload = msg.args[1]

            #from fitz import interactnow ; reload(interactnow)

            #print type(payload)
            payload = "#%s %s"%(name,message)
            #print payload
            import copy
            msg = copy.copy(msg)
            msg.args = (channel, payload)

            self.doPrivmsg(irc, msg)
        # Give it the signature we need to be a callable supybot
        # command (it does check more than I'd like).  Heavy Wizardry.
        instancemethod = type(self.__getattr__)
        wrapped_function = wrap(wrapped_function, [optional('text', '')])
        return instancemethod(wrapped_function, self, MeetBot)

Class = MeetBot


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

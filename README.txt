USAGE
~~~~~
http://wiki.debian.org/MeetBot

Inspired by the original MeetBot, by Holger Levsen, which was itself a
derivative of Mootbot (https://wiki.ubuntu.com/ScribesTeam/MootBot),
by the Ubuntu Scribes team.

/usr/share/doc/supybot/GETTING_STARTED.gz (on Debian systems) provides
information on configuring supybot the first time, including taking
ownership the first time.


DESIGN DECISIONS
~~~~~~~~~~~~~~~~
The MeetBot plugin doesn't operate like a regular supybot plugin.  It
bypasses the normal command system.  Instead it listens for all lines
(it has to log them all anyway) and if it sees a command, it acts on it.

- Separation of meeting code and plugin code.  This should make it
  easy to port to other bots, and perhaps more importantly make it
  easier to maintain, or rearrange, the structure within supybot.

- Not making users have to register and have capabilities added.  The
  original meetbot ran as a service to many channels not necessarily
  connected to the original owner.

- Makes it easier to replay stored logs.  I don't have to duplicate the
  supybot command parsing logic, such as detecting the bot nick and
  running the proper command.  Also, there might be command overlaps
  with some preexisting plugins.


INSTALLATION
~~~~~~~~~~~~

Requirements: 
* pygments (debian package python-pygments) (for pretty IRC logs).
* docutils (debian package python-docutils) (for restructured text to
            HTML conversion)

* Install supybot.  You can use supybot-wizard to make a bot 
  configuration.

  * Don't use a prefix character.  (disable this:
      supybot.reply.whenAddressedBy.chars: 
    in the config file - leave it blank afterwards.)

* Move the MeetBot directory into your plugins directory of Supybot.

* Make supybot join any channels you are interested in.  The wizard
  handles this for the first part.  After that, I guess you have to
  learn about supybot (I don't know enough yet...).  If the plugin is
  loaded, it is active on ALL channels the bot is on.  You can also
  command the bot after it's online.

* Make sure the plugin is loaded.
    supybot.plugins: Admin Misc User MeetBot Owner Config Channel
  (can also control loading after the bot is started)

Supybot does a lot, but I don't know much about it.  Hopefully Supybot
expert users can enlighten me as to better ways to do things.

In particular, supybot has a large configuration system, which I know
nothing about.  It may be worth hooking MeetBot into that system.



LICENSE
~~~~~~~
The MeetBot plugin is under the same license as supybot is, a 3-clause
BSD.  The license is documented in each code file (and also applies to
this README file).


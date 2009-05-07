USAGE
~~~~~
http://wiki.debian.org/MeetBot

Inspired by the original MeetBot, by Holger Levsen, which was itself a
derivative of Mootbot (https://wiki.ubuntu.com/ScribesTeam/MootBot),
by the Ubuntu Scribes team.

/usr/share/doc/supybot/GETTING_STARTED.gz (on Debian systems) provides
information on configuring supybot the first time, including taking
ownership the first time.



INSTALLATION
~~~~~~~~~~~~

Requirements: 
* pygments (debian package python-pygments) (for pretty IRC logs).

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


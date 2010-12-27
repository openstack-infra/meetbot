ABOUT
~~~~~
http://wiki.debian.org/MeetBot

Inspired by the original MeetBot, by Holger Levsen, which was itself a
derivative of Mootbot (https://wiki.ubuntu.com/ScribesTeam/MootBot),
by the Ubuntu Scribes team.

The Supybot file GETTING_STARTED
(/usr/share/doc/supybot/GETTING_STARTED.gz on Debian systems) provides
hinformation on configuring supybot the first time, including taking
ownership the first time.  You really need to read this if you haven't
used supybot before.



INSTALLATION
~~~~~~~~~~~~

Requirements
------------
* pygments (optional) (debian package python-pygments) (for pretty IRC
  logs).  This package is no longer required (after HTMLlog2 became
  default)


Install Supybot
---------------
* You need to install supybot yourself.  You can use supybot-wizard to
  make a bot configuration.

  * See the file GETTING_STARTED
    (/usr/share/doc/supybot/GETTING_STARTED.gz on a Debian system).
    This tells all about supybot installation, and is an important
    prerequisite to understanding MeetBot configuration.

  * Don't use a prefix character.  (disable this:
      supybot.reply.whenAddressedBy.chars: 
    in the config file - leave it blank afterwards.)  If you do use a
    prefix character, it should be different than the "#" MeetBot
    prefix character.  There are issues here which still need to be
    worked out.

Install the MeetBot plugin
--------------------------

* Move the MeetBot directory into your ``plugins`` directory of
  Supybot.

* You need the ``ircmeeting`` directory to be importable as a python
  module.

  * Easy method:  Copy ``ircmeeting`` into the ``MeetBot`` directory.
    This makes ``ircmeeting`` work as a relative import.  However,
    this will probably stop working with some future Python version.

  * Other method: Copy ``ircmeeting`` somewhere into $PYTHONPATH.

* Make sure the plugin is loaded.  Use the command ``load MeetBot``.
  You can check the command ``config plugins`` to check what is
  loaded.

Configuration
-------------

* Make supybot join any channels you are interested in.  The wizard
  handles this the first time around.  After that, I guess you have to
  learn about supybot.  If the plugin is loaded, it is active on ALL
  channels the bot is on.  You can also command the bot after it's
  online.

* Make a `meetingLocalConfig.py` file and put it somewhere that it can
  be found:
  - in $PYTHONPATH
  - in the ircmeeting/ directory
  - in the current working directory

* Configuration of meetingLocalConfig.py is covered in the manual,
  doc/Manual.txt

Supybot does a lot, far more than this one readme can talk about.  You
need to learn about supybot a bit, too, in order to be able to use
MeetBot properly.



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



LICENSE
~~~~~~~
The MeetBot plugin is under the same license as supybot is, a 3-clause
BSD.  The license is documented in each code file (and also applies to
this README file).


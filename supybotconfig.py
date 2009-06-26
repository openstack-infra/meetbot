# Richard Darst, June 2009

import supybot.conf as conf
import supybot.registry as registry

import meeting
OriginalConfig = meeting.Config

# The plugin group for configuration
MeetBotConfigGroup = conf.registerPlugin('MeetBot')

class SupybotConfig(object):
    def __init__(self, M):
        """Do the regular default configuration, and sta"""
        self.__C = OriginalConfig(M)
    
    def __getattr__(self, attrname):
        """Try to get the value from the supybot registry.  If it's in
        the registry, return it.  If it's not, then proxy it to th.
        """
        if attrname in settable_attributes:
            value = self.__C.M._registryValue(attrname,
                                              #channel=self.__C.M.channel
                                              )
            if value != '.':
                value = value.replace('\\n', '\n')
                return value
        # We don't have this value in the registry.  So, proxy it to
        # the normal config object.  This is also the path that all
        # functions take.
        return getattr(self.__C, attrname)

    #def __getattribute__(self, attrname):
    #    print attrname
    #
    #    from fitz import interact ; interact.interact()
    #    if attrname in settable_attributes:
    #        "getting from registry"
    #        #self.registryValue('enable', channel)
    #        return "blah blah blah"
    #    
    #    raise AttributeError


#conf.registerGlobalValue(MeetBot
use_supybot_config = conf.registerGlobalValue(MeetBotConfigGroup,
                                              'enableSupybotBasedConfig',
                                              registry.Boolean(False, ''))
#from fitz import interactnow
if (use_supybot_config.value and
    not getattr(OriginalConfig, 'dontBotConfig', False)):
    # Set all string variables in the default Config class as supybot
    # registry variables.
    settable_attributes = [ ]
    for attrname in dir(OriginalConfig):
        # Don't configure attributs starting with '_'
        if attrname[0] == '_':
            continue
        attr = getattr(OriginalConfig, attrname)
        # Don't configure attributes that aren't strings.
        if not isinstance(attr, (str, unicode)):
            continue
        attr = attr.replace('\n', '\\n')
        # Use this instead: conf.registerChannelValue
        conf.registerGlobalValue(MeetBotConfigGroup, attrname,
                                 registry.String(attr,""))
        settable_attributes.append(attrname)

    # Here is where the real proxying occurs.
    meeting.Config = SupybotConfig
    meeting.ConfigOriginal = OriginalConfig
    #meeting.Config = type('Config', (Config, meeting.Config), {})

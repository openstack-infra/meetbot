# Richard Darst, June 2009

import types

import supybot.conf as conf
import supybot.registry as registry

import meeting
import writers

OriginalConfig = meeting.Config


# The plugin group for configuration
MeetBotConfigGroup = conf.registerPlugin('MeetBot')

class WriterMap(registry.String):
    """List of output formats to write.  This is a space-separated
    list of 'WriterName:.ext' pairs.  WriterName must be from the
    writers.py module, '.ext' must be a extension ending in a .
    """
    def set(self, s):
        s = s.split()
        writer_map = { }
        for writer in s:
            #from fitz import interact ; interact.interact()
            writer, ext = writer.split(':')
            if not hasattr(writers, writer):
                raise ValueError("Writer name not found: %s"%writer)
            if len(ext) < 2 or ext[0] != '.':
                raise ValueError("Extension must start with '.' and have "
                                 "at least one more character.")
            writer_map[ext] = getattr(writers, writer)
        self.setValue(writer_map)
    def setValue(self, writer_map):
        for e, w in writer_map.iteritems():
            if not hasattr(w, "format"):
                raise ValueError("Writer %s must have method .format()"%
                                 w.__class__.__name__)
            self.value = writer_map
    def __str__(self):
        writers_string = [ ]
        for ext, w in self.value.iteritems():
            name = w.__class__.__name__
            writers_string.append("%s:%s"%(name, ext))
        return " ".join(writers_string)


class SupybotConfigProxy(object):
    def __init__(self, M):
        """Do the regular default configuration, and sta"""
        self.__C = OriginalConfig(M)
    
    def __getattr__(self, attrname):
        """Try to get the value from the supybot registry.  If it's in
        the registry, return it.  If it's not, then proxy it to th.
        """
        if attrname in settable_attributes:
            value = self.__C.M._registryValue(attrname,
                                              channel=self.__C.M.channel)
            if not isinstance(value, (str, unicode)):
                return value
            # '.' is used to mean "this is not set, use the default
            # value from the python config class.
            if value != '.':
                value = value.replace('\\n', '\n')
                return value
        # We don't have this value in the registry.  So, proxy it to
        # the normal config object.  This is also the path that all
        # functions take.
        value = getattr(self.__C, attrname)
        # If the value is an instance method, we need to re-bind it to
        # the new config class so that we will get the data values
        # defined in supydot (otherwise attribute lookups in the
        # method will bypass the supybot proxy and just use default
        # values).  This will slow things down a little bit, but
        # that's just the cost of duing business.
        if hasattr(value, 'im_func'):
            return types.MethodType(value.im_func, self, value.im_class)
        return value



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
        # For a global value: conf.registerGlobalValue and remove the
        # channel= option from registryValue call above.
        conf.registerChannelValue(MeetBotConfigGroup, attrname,
                                  registry.String(attr,""))
        settable_attributes.append(attrname)

    # writer_map
    # (doing the commented out commands below will erase the previously
    # stored value of a config variable)
    #if 'writer_map' in MeetBotConfigGroup._children:
    #    MeetBotConfigGroup.unregister('writer_map')
    conf.registerChannelValue(MeetBotConfigGroup, 'writer_map',
                      WriterMap(OriginalConfig.writer_map, ""))
    settable_attributes.append('writer_map')


    # Here is where the real proxying occurs.
    meeting.Config = SupybotConfigProxy



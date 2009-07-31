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


import types

import supybot.conf as conf
import supybot.registry as registry

import meeting
import writers

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
            #if len(ext) < 2 or ext[0] != '.':
            #    raise ValueError("Extension must start with '.' and have "
            #                     "at least one more character.")
            writer_map[ext] = getattr(writers, writer)
        self.setValue(writer_map)
    def setValue(self, writer_map):
        for e, w in writer_map.iteritems():
            if not hasattr(w, "format"):
                raise ValueError("Writer %s must have method .format()"%
                                 w.__name__)
            self.value = writer_map
    def __str__(self):
        writers_string = [ ]
        for ext, w in self.value.iteritems():
            name = w.__name__
            writers_string.append("%s:%s"%(name, ext))
        return " ".join(writers_string)


class SupybotConfigProxy(object):
    def __init__(self, *args, **kwargs):
        """Do the regular default configuration, and sta"""
        OriginalConfig = self.__OriginalConfig
        self.__C = OriginalConfig(*args, **kwargs)
    
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
def is_supybotconfig_enabled(OriginalConfig):
    return (use_supybot_config.value and
            not getattr(OriginalConfig, 'dontBotConfig', False))

settable_attributes = [ ]
def setup_config(OriginalConfig):
    # Set all string variables in the default Config class as supybot
    # registry variables.
    for attrname in dir(OriginalConfig):
        # Don't configure attributs starting with '_'
        if attrname[0] == '_':
            continue
        attr = getattr(OriginalConfig, attrname)
        # Don't configure attributes that aren't strings.
        if isinstance(attr, (str, unicode)):
            attr = attr.replace('\n', '\\n')
            # For a global value: conf.registerGlobalValue and remove the
            # channel= option from registryValue call above.
            conf.registerChannelValue(MeetBotConfigGroup, attrname,
                                      registry.String(attr,""))
            settable_attributes.append(attrname)
        if isinstance(attr, bool):
            conf.registerChannelValue(MeetBotConfigGroup, attrname,
                                      registry.Boolean(attr,""))
            settable_attributes.append(attrname)

    # writer_map
    # (doing the commented out commands below will erase the previously
    # stored value of a config variable)
    #if 'writer_map' in MeetBotConfigGroup._children:
    #    MeetBotConfigGroup.unregister('writer_map')
    conf.registerChannelValue(MeetBotConfigGroup, 'writer_map',
                      WriterMap(OriginalConfig.writer_map, ""))
    settable_attributes.append('writer_map')

def get_config_proxy(OriginalConfig):
    # Here is where the real proxying occurs.
    SupybotConfigProxy._SupybotConfigProxy__OriginalConfig = OriginalConfig
    return SupybotConfigProxy



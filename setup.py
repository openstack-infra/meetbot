
from distutils.core import setup
setup(name='MeetBot',
      description='IRC Meeting Helper',
      version='0.1.4',
      packages=['supybot.plugins.MeetBot',
                'ircmeeting'],
      package_dir={'supybot.plugins.MeetBot':'MeetBot'},
      package_data={'ircmeeting':['*.html', '*.txt', '*.css']},
      author="Richard Darst",
      author_email="rkd@zgib.net"
      )

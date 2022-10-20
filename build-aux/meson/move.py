from os import environ, path, sys
from shutil import move

destdir = environ.get('DESTDIR', '')
prefix = environ['MESON_INSTALL_PREFIX']
source, dest = sys.argv[1:]
move(destdir + path.join(prefix, source), destdir + path.join(prefix, dest))

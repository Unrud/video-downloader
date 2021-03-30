from os import environ, path
from subprocess import call

destdir = environ.get('DESTDIR', '')
prefix = environ['MESON_INSTALL_PREFIX']
datadir = path.join(prefix, 'share')

# Package managers set this so we don't need to run
if not destdir:
    print('Updating icon cache...')
    call(['gtk-update-icon-cache', '-qtf',
          path.join(datadir, 'icons', 'hicolor')])

    print('Updating desktop database...')
    call(['update-desktop-database', '-q', path.join(datadir, 'applications')])

    print('Compiling GSettings schemas...')
    call(['glib-compile-schemas', path.join(datadir, 'glib-2.0', 'schemas')])

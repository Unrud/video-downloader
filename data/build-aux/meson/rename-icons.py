from os import environ, path, rename

prefix = environ.get('MESON_INSTALL_PREFIX', '/usr/local')
destdir = environ.get('DESTDIR', '')
icon_theme_dir = path.join(destdir + path.sep + prefix if destdir else prefix,
                           'share', 'icons', 'hicolor')
icon_id = 'com.github.unrud.VideoDownloader'

for res in [16, 32, 48, 64, 128, 256, 512]:
    icon_dir = path.join(icon_theme_dir, '{res}x{res}'.format(res=res), 'apps')
    rename(path.join(icon_dir, '{}_{}.png'.format(icon_id, res)),
           path.join(icon_dir, '{}.png'.format(icon_id)))

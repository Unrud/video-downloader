pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'video_downloader'
gnome = import('gnome')

gnome.compile_resources('video-downloader', 'video_downloader.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

conf = configuration_data()
conf.set('PYTHON', python.path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

video_downloader_bin = configure_file(
  input: 'video-downloader.in',
  output: 'video-downloader',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

video_downloader_sources = files([
  '__init__.py',
  'about_dialog.py',
  'authentication_dialog.py',
  'main.py',
  'model.py',
  'playlist_dialog.py',
  'util.py',
  'window.py'
])

if run_command(python, '-m', 'flake8', '--version').returncode() == 0
  test('Lint python files', python,
    args: ['-m', 'flake8', video_downloader_sources, video_downloader_bin]
  )
endif

install_data(video_downloader_sources, install_dir: moduledir)


subdir('downloader')

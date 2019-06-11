pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'video_downloader')

python3 = import('python3')

conf = configuration_data()
conf.set('PYTHON', python3.find_python().path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'video-downloader.in',
  output: 'video-downloader',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

video_downloader_sources = [
  '__init__.py',
  'base_dialog.py',
  'base_window_mixin.py',
  'download_frame.py',
  'error_frame.py',
  'login_dialog.py',
  'main_frame.py',
  'main.py',
  'model.py',
  'platform.py',
  'playlist_dialog.py',
  'resize_label.py',
  'success_frame.py',
  'utils.py',
  'videopassword_dialog.py',
]

install_data(video_downloader_sources, install_dir: moduledir)


subdir('downloader')

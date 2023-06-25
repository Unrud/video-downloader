pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'video_downloader'

release_notes = run_command([
  python, extract_xml_aux, '--escape',
  '..' / 'data' / 'com.github.unrud.VideoDownloader.metainfo-releases.xml.in',
  './/release[@version="' + meson.project_version() + '"]/description/*'],
  check: true,
).stdout()

conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('releasenotes', release_notes)

about_dialog_ui_source = configure_file(
  input: 'about_dialog.ui.in',
  output: 'about_dialog.ui',
  configuration: conf,
)

video_downloader_ui_sources = [
  files([
    'authentication_dialog_login.ui',
    'authentication_dialog_password.ui',
    'shortcuts_dialog.ui',
    'window.ui',
  ]),
  about_dialog_ui_source,
]

video_downloader_gresource_xml = configure_file(
  capture: true,
  command: [python, create_gresource_aux, '/com/github/unrud/VideoDownloader',
            video_downloader_ui_sources],
  output: 'video_downloader.gresource.xml',
)

gnome.compile_resources('video-downloader', video_downloader_gresource_xml,
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

conf = configuration_data()
conf.set('PYTHON', python.full_path())
conf.set_quoted('VERSION', meson.project_version())
conf.set_quoted('localedir', get_option('prefix') / get_option('localedir'))
conf.set_quoted('pkgdatadir', pkgdatadir)

video_downloader_bin = configure_file(
  input: 'video-downloader.in',
  output: 'video-downloader',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x',
)
python_sources_for_linting += video_downloader_bin

video_downloader_sources = files([
  '__init__.py',
  'about_dialog.py',
  'authentication_dialog.py',
  'main.py',
  'model.py',
  'playlist_dialog.py',
  'shortcuts_dialog.py',
  'window.py',
])
python_sources_for_linting += video_downloader_sources

install_data(video_downloader_sources, install_dir: moduledir)


subdir('downloader')
subdir('util')

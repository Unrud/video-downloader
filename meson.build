project('video-downloader',  
  version: '0.7.2',
  meson_version: '>= 0.50.0',
  default_options: ['warning_level=2']
)

i18n = import('i18n')
python = import('python').find_installation('python3')


subdir('data')
subdir('src')
subdir('po')

meson.add_install_script(python,
  meson.current_source_dir() / 'build-aux' / 'meson' / 'postinstall.py'
)

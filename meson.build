project('video-downloader',  
  version: '0.9.8',
  meson_version: '>= 0.50.0',
  default_options: ['warning_level=2']
)

python_sources_for_linting = []
i18n = import('i18n')
python = import('python').find_installation('python3')


subdir('data')
subdir('src')
subdir('po')

post_install_aux = (
  meson.current_source_dir() / 'build-aux' / 'meson' / 'postinstall.py'
)
python_sources_for_linting += post_install_aux
meson.add_install_script(python, post_install_aux)

if (run_command(python, '-m', 'flake8', '--version').returncode() == 0 and
    python_sources_for_linting.length() > 0)
  test('Lint python sources', python,
    args: ['-m', 'flake8', python_sources_for_linting]
  )
endif

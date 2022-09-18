project('video-downloader',  
  version: '0.10.4',
  meson_version: '>= 0.59.0',
  default_options: ['warning_level=2', 'werror=false'],
)

python_sources_for_linting = []
i18n = import('i18n')
gnome = import('gnome')
python = import('python').find_installation('python3')


subdir('data')
subdir('src')
subdir('po')

gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)

if (run_command(python, '-m', 'flake8', '--version',
                check: false).returncode() == 0 and
    python_sources_for_linting.length() > 0)
  test('Lint python sources', python,
    args: ['-m', 'flake8', python_sources_for_linting]
  )
endif

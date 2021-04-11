video_downloader_sources = files([
  '__init__.py',
  '__main__.py',
  'youtube_dl_formats.py',
  'youtube_dl_monkey_patch.py',
  'youtube_dl_slave.py',
])

if run_command(python, '-m', 'flake8', '--version').returncode() == 0
  test('Lint python files', python,
    args: ['-m', 'flake8', video_downloader_sources]
  )
endif

install_data(video_downloader_sources, install_dir: moduledir / 'downloader')

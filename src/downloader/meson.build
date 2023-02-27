video_downloader_sources = files([
  '__init__.py',
  '__main__.py',
  'yt_dlp_monkey_patch.py',
  'yt_dlp_slave.py',
])
python_sources_for_linting += video_downloader_sources

install_data(video_downloader_sources, install_dir: moduledir / 'downloader')

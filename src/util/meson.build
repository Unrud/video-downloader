video_downloader_sources = files([
  'connection.py',
  '__init__.py',
  'path.py',
  'response.py',
  'rpc.py',
])
python_sources_for_linting += video_downloader_sources

install_data(video_downloader_sources, install_dir: moduledir / 'util')

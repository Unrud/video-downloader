pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()

desktop_file = i18n.merge_file(
  input: 'com.github.unrud.VideoDownloader.desktop.in',
  output: 'com.github.unrud.VideoDownloader.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
endif

appstream_file = i18n.merge_file(
  input: 'com.github.unrud.VideoDownloader.appdata.xml.in',
  output: 'com.github.unrud.VideoDownloader.appdata.xml',
  po_dir: '../po',
  install: true,
  install_dir: get_option('datadir') / 'metainfo'
)

appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
    args: ['validate-relax', appstream_file]
  )
endif

install_data('com.github.unrud.VideoDownloader.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

icon_id = 'com.github.unrud.VideoDownloader'
icon_svg = icon_id + '.svg'
install_data(icon_svg,
  install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'scalable' / 'apps'
)
install_data(icon_id + '-symbolic.svg',
  install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'symbolic' / 'apps'
)

rsvg_util = find_program('rsvg-convert')
foreach res : [16, 32, 48, 64, 128, 256, 512]
  icon_png = '@0@_@1@.png'.format(icon_id, res)
  custom_target(icon_png,
    input: icon_svg,
    output: icon_png,
    command: [
      rsvg_util,
      '--height', '@0@'.format(res), '--keep-aspect-ratio',
      '--format', 'png', '--output', '@OUTPUT@', '@INPUT@'
    ],
    install: true,
    install_dir: get_option('datadir') / 'icons' / 'hicolor' / '@0@x@0@'.format(res) / 'apps'
  )
endforeach
meson.add_install_script(python, meson.current_source_dir() / 'build-aux' / 'meson' / 'rename-icons.py')

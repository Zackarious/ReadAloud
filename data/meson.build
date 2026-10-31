# Desktop file configuration
desktop_file = i18n.merge_file(
  input: 'im.zackarious.ReadAloud.desktop.in',
  output: 'im.zackarious.ReadAloud.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

# AppStream metadata installation
appstream_file = i18n.merge_file(
  input: 'im.zackarious.ReadAloud.metainfo.xml.in',
  output: 'im.zackarious.ReadAloud.metainfo.xml',
  po_dir: '../po',
  install: true,
  install_dir: get_option('datadir') / 'metainfo'
)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('Validate appstream file', appstreamcli, args: ['validate', '--no-net', appstream_file])
endif

# Process icon theme assets
subdir('icons')

# Install GSettings schema file properly
install_data(
  'im.zackarious.ReadAloud.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)

# Compile schemas locally for testing environments
gnome.compile_schemas(
  build_by_default: true
)

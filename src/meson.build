pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / meson.project_name()
gnome = import('gnome')

gnome.compile_resources('readaloud',
  'readaloud.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'readaloud.in',
  output: 'readaloud',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

readaloud_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'bubble.py',
  'reader.py',
  'pipervoice.py',
  'vocxpo.py',
  'demos.py',
  'paths.py',
  'audio_backend.py',
  'document_importer.py',
  'wikipedia_importer.py',
]

install_data(readaloud_sources, install_dir: moduledir)

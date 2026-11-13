project('readaloud', ['c', 'cpp'],
  version: '1.8.18',
  meson_version: '>= 0.63.0',
  default_options: ['warning_level=2', 'cpp_std=c++17']
)

i18n = import('i18n')
gnome = import('gnome')

# Translations and resources
subdir('data')
subdir('po')
subdir('src')
subdir('models')

gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: false,
  update_desktop_database: true,
)

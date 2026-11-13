application_id = 'im.zackarious.ReadAloud'

scalable_dir = 'hicolor' / 'scalable' / 'apps'
install_data(
  scalable_dir / ('@0@.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / scalable_dir
)

symbolic_dir = 'hicolor' / 'symbolic' / 'apps'
install_data(
  symbolic_dir / ('@0@-symbolic.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / symbolic_dir
)

# Custom action icons (by Asam Munir via SVGRepo & Flaticon)
actions_dir = 'hicolor' / 'scalable' / 'actions'
install_data(
  actions_dir / ('@0@.disk.svg').format(application_id),
  actions_dir / ('@0@.cd.svg').format(application_id),
  actions_dir / ('@0@.folder-open.svg').format(application_id),
  actions_dir / ('@0@.rewind-15-symbolic.svg').format(application_id),
  actions_dir / ('@0@.forward-15-symbolic.svg').format(application_id),
  actions_dir / ('@0@.stop-symbolic.svg').format(application_id),
  actions_dir / ('@0@.eye-symbolic.svg').format(application_id),
  actions_dir / ('@0@.import-symbolic.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / actions_dir
)

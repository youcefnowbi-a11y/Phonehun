# CASEFILE — durable operational findings

- Target bird: Samsung Galaxy A21s, SM-A217F, screen 720x1600 device coords,
  ADB over USB authorized. Serial seen as R58N647SCPY (verify each session).
- First evidence capture: cortex_shots/screen_capture_1788214231.jpg (7.9 KB, dark
  screen — small bytes = display off; wake before judging).
- Panel: Flask on 127.0.0.1:5000, token in .api_token, header X-API-Token.
- Watcher: hunter must be re-armed after every panel reboot (state is RAM-only).
- Lock: PIN pad is the only gate; identity/battery/storage/SMS/contacts/shell
  all reachable while locked. Siege lockouts follow wrong attempts — watch
  waiting_seconds_left.

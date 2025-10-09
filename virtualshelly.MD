# service

```bash
sudo systemctl daemon-reload

sudo systemctl start virtualshelly.service
sudo systemctl status virtualshelly.service

/etc/systemd/system $ sudo vi virtualshelly.service
[Unit]
Description=Virtual Shelly 3EM Emulator
# Ensure networking is up before starting
After=network-online.target
Wants=network-online.target

[Service]
# Changed type to 'simple' as the script doesn't use systemd notification
Type=simple
Environment=PYTHONUNBUFFERED=true
Restart=always
# --- FIX: Set the working directory separately ---
WorkingDirectory=/home/user/virtualshelly
ExecStart=/usr/bin/python3 virtualshelly.py

[Install]
WantedBy=multi-user.target
```

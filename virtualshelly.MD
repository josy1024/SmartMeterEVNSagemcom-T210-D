# mqtt to shelly 3EM Emulator

## setup
```bash
*  pip install flask paho-mqtt
```

## configure
* create /home/user/virtualshelly/config.json (from config.virtual-shelly.json)
* update config to match your mqtt server
* copy virtualshelly.py to /home/user/virtualshelly

## service config

```bash
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
WorkingDirectory=/home/user/virtualshelly
ExecStart=/usr/bin/python3 virtualshelly.py

[Install]
WantedBy=multi-user.target
```

## service handling

```bash
# reload service config
sudo systemctl daemon-reload

# start service
sudo systemctl start virtualshelly.service
# check service output
sudo systemctl status virtualshelly.service
# enable service (if everything is okay!)
sudo systemctl enable virtualshelly.service
```


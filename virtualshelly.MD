# mqtt to shelly 3EM Emulator

Kurz: `virtualshelly.py` emuliert ein Shelly 3EM‑Gerät und übersetzt Werte aus MQTT‑Topics in Shelly‑artige HTTP‑Antworten.

## setup

```bash
sudo pip install flask paho-mqtt
```

## configure

* create /home/user/virtualshelly/config.json (from config.virtual-shelly.json)
* update config to match your mqtt server
* copy virtualshelly.py to /home/user/virtualshelly

## service config

```bash
python3 virtualshelly.py
```

Systemd-Service (Beispiel)
-------------------------

Falls Sie das Skript als Dienst betreiben möchten, verwenden Sie eine Unit wie diese (passen Sie `WorkingDirectory`/`ExecStart` an):

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

## links

* if you have Node-RED or ESP32 you can also use this shelly3em emulator: <https://github.com/BetaTobi/Shelly3EM-Emulator/wiki>

## Beschreibung von `virtualshelly.py`

Kurz: `virtualshelly.py` emuliert ein Shelly 3EM‑Gerät und übersetzt Werte aus MQTT‑Topics in Shelly‑artige HTTP‑Antworten.

* Globale Variablen:
 	* `mqtt_data`: Dictionay, speichert die letzten MQTT‑Payloads keyed by Topic.
 	* `start_time`: Startzeit des Skripts (für `uptime`, falls kein Topic geliefert wird).
 	* `CONFIG`: geladene Konfiguration aus `config.json`.
 	* `METER_TOPIC_MAP`: Map von Meter‑Index (0..2) zu Phase‑Topics (Spannung/Strom).

* Wichtige Funktionen:
 	* `load_config()`: Liest `config.json` und füllt `CONFIG`. Bei fehlender/ungültiger Datei beendet sich das Programm.
 	* `on_connect(client, userdata, flags, rc)`: Abonniert alle erwarteten Smartmeter‑Topics nach erfolgreicher MQTT‑Verbindung.
 	* `on_message(client, userdata, msg)`: Schreibt empfangene Payloads (decoded) in `mqtt_data`.
 	* `mqtt_thread()`: Baut MQTT‑Client (mit optionaler Auth) auf, verbindet sich mit dem Broker und startet die Loop. Bei Verbindungsfehlern wird mit Backoff neu versucht.
 	* `safe_float(topic_key, default_value)`: Konvertiert Werte aus `mqtt_data` robust in `float` mit Default‑Fallback.
 	* `get_meter_data(meter_index)`: Erzeugt das Shelly‑`emeter` Objekt (power, total, voltage, current, pf, …) für eine Phase anhand der konfigurierten Topics.

* Webendpunkte (Flask):
 	* `GET /emeter/<int:meter_id>`: Gibt die Messwerte für `meter_id` 0–2 zurück.
 	* `GET /status`: Liefert den vollständigen Shelly‑3EM Status (u. a. `emeters` Array, `total_power`, `uptime`, device metadata).

* Verhalten/Hinweise:
 	* Fehlende oder nicht konvertierbare Topic‑Werte werden durch sichere Defaults ersetzt (z. B. 230V, 0A).
 	* Die Phase‑Leistung wird aus `Smartmeter/Wirkleistunggesamt` durch Drittelung berechnet, falls vorhanden.
 	* `Leistungsfaktor` wird als Prozent im Topic erwartet und in Dezimal (z. B. 95 → 0.95) ausgegeben.
 	* Der Flask‑Server wird standardmäßig auf Port `80` gestartet; auf Unix ist dafür Root nötig oder passen Sie den Port an.

Wenn Sie möchten, erweitere ich die Doku um Beispiel‑JSON‑Responses für `/status` und `/emeter/<id>` oder füge ein `config.example.json` hinzu. Welche Option bevorzugen Sie?

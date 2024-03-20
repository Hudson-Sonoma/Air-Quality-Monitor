# Air-Quality-Monitor
Open Source Modular Air Quality Monitor: CO2, particulates, pressure, humidity, temperature


Welcome to the STELLA-AQ modular air quality monitor community. This air quality monitor is modular, repairable, and upgradeable.

## Connect to your Wifi

Connect to your computer. Edit the file /Volumes/CIRCUITPY/settings.toml
STELLA_WIFI_SSID="<network-name>"
STELLA_WIFI_PASSWORD="<password>"

## Connect to your Air Quality Monitor

Touch the touchscreen to select the QR code screen. Navigate to the QR code URL to view historical data.

## Update your air quality monitor software

git clone https://github.com/Hudson-Sonoma/Air-Quality-Monitor
./rsync-CIRCUITPY.sh
git --work-tree /Volumes/CIRCUITPY status

## Purchase spare parts

https://www.digikey.com/short/37vvb2zh

| Quantity | Part Number       | Manufacturer Part Number | Description                      | Unit Price | Extended Price USD |
| -------- | ----------------- | ------------------------ | -------------------------------- | ---------- | ------------------ |
| 1        | 1528-4632-ND      | 4632                     | STEMMA QT PMSA003I AIR QUALITY   | 44.95      | 44.95              |
| 1        | 1528-1359-ND      | 2652                     | SENSOR HUM/PRESS I2C/SPI BME280  | 14.95      | 14.95              |
| 1        | 1528-5190-ND      | 5190                     | STEMMA QT SCD-41 CO2 HUMID TEMP  | 49.95      | 49.95              |
| 1        | 1597-104030087-ND | 104030087                | SEEED STUDIO XIAO ROUND DISPLAY  | 18         | 18                 |
| 1        | 1528-5700-ND      | 5700                     | ADAFRUIT QT PY S3 WITH 2MB PSRAM | 12.5       | 12.5               |
| 3        | 1528-4399-ND      | 4399                     | STEMMA QWIIC JST SH CABLE 50MM   | 0.95       | 2.85               |
| 1        | 1528-5385-ND      | 5385                     | STEMMA QT/QWIIC CABLE 400MM      | 1.5        | 1.5                |

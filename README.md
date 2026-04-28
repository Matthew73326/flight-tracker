# ✈ Flight Tracker

A lightweight Windows app that sends you real-time notifications when military (or any) aircraft fly within a set radius of your location.

Built using the free [ADS-B Exchange](https://globe.adsbexchange.com) data feed via [adsb.lol](https://adsb.lol) — no account or API key needed.

---

## Features

- 🎖 **Military mode** — uses the dedicated `/mil` endpoint, zero civilian false positives
- 🔔 **Windows toast notifications** — click a notification to jump straight to that aircraft on the live map
- 📍 Set any location by latitude/longitude with a custom radius
- 🔍 Monitor all aircraft, military only, specific types, or specific registrations
- ⏱ Configurable poll interval and per-aircraft cooldown
- 🔄 **Auto-updater** — notifies you when a new version is available and updates with one click
- 💾 Settings saved automatically to `config.json`

---

## Requirements

- Windows 10 or 11
- Python 3.8+ → [Download here](https://www.python.org/downloads/) *(tick "Add Python to PATH" during install)*

---

## Installation

1. **Download** the latest files from this repo (click `Code` → `Download ZIP`)
2. Extract the zip somewhere on your PC
3. Run **`setup_install.bat`** — installs all required Python packages
4. Run **`Launch_FlightTracker.vbs`** to start the app (no console window)

---

## Usage

| Setting | Description |
|---------|-------------|
| **Location** | Name, latitude, longitude and radius to monitor |
| **Monitor mode** | Military only / All aircraft / Specific types / Specific registrations |
| **Aircraft types** | Comma separated type codes e.g. `A400, C17, CH47, EUFI` |
| **Registrations** | Comma separated tail numbers e.g. `ZM413, ZZ333` |
| **Poll every (sec)** | How often to query the ADS-B feed (default 60s) |
| **Re-notify cooldown** | How long before alerting about the same aircraft again (default 300s) |

### Monitor Modes

- **Military only** — Queries the ADS-B Exchange `/mil` endpoint which is curated to military aircraft only. Most reliable, no false positives.
- **All aircraft** — Every aircraft in your radius
- **Specific types** — Filter by ICAO type code (e.g. `B737`, `A320`, `C130`)
- **Specific registrations** — Watch for specific tail numbers

### Useful Military Type Codes

| Code | Aircraft |
|------|----------|
| A400 | Airbus A400M Atlas |
| C130 | Hercules |
| C17 | Boeing C-17 Globemaster |
| EUFI | Eurofighter Typhoon |
| HAWK | BAE Hawk T1/T2 |
| CH47 | Chinook |
| AW101 | Merlin |
| RC135 | Rivet Joint |
| P8 | Boeing P-8 Poseidon |
| F35 | F-35 Lightning II |

---

## Updating

The app checks for updates automatically on startup. If a new version is available you'll see a popup with the changelog and a one-click update button. You can also click **Check for Updates** manually at any time.

---

## Data Source

Live ADS-B data from [adsb.lol](https://adsb.lol) — a free community mirror of ADS-B Exchange. Data is sourced from a global network of volunteer-run ground receivers picking up aircraft ADS-B transponder broadcasts.

Note: Military aircraft operating in sensitive roles may not appear as they can disable ADS-B. The `/mil` endpoint covers aircraft that are broadcasting.

---

## Troubleshooting

If the app doesn't open, check `startup_log.txt` in the app folder for error details.

If notifications aren't working, click **Test Notification** inside the app — then run `setup_install.bat` again if needed.

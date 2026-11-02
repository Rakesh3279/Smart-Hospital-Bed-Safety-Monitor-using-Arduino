# Smart Hospital Bed Safety Monitor

An embedded monitoring prototype that estimates bed inclination using an MPU-6500 accelerometer and an Arduino UNO R4 Minima, then streams telemetry to a Python desktop GUI over serial.

> **Project status:** Working engineering prototype. The repository includes the Arduino firmware, Python desktop GUI, wiring/architecture visuals, and supporting documentation. It is not a certified medical device and must not be used for clinical decisions or as the sole means of monitoring patient safety.

## Highlights

- **Embedded platform:** Arduino UNO R4 Minima (Renesas RA4M1, Arm Cortex-M4)
- **Motion sensor:** MPU-6500, I²C address `0x68` (verify the exact breakout-board part number before hardware deployment)
- **Inclination estimate:** accelerometer-based pitch calculation
- **Noise reduction:** first-order software low-pass filter on the firmware (`alpha = 0.15`) and a five-sample median filter in the Python GUI
- **Display stability:** firmware display deadband of `0.5°`
- **Threshold:** configurable inclination threshold, currently `30°`
- **Communications:** serial telemetry at `115200` baud
- **Desktop interface:** Python/Tkinter GUI

## System overview

```text
 MPU-6500 accelerometer
      │ I²C (SDA/SCL)
      ▼
 Arduino UNO R4 Minima
 ├─ Sensor register configuration
 ├─ Motion interrupt handling (INT → digital pin 3)
 ├─ Accelerometer reading and pitch calculation
 ├─ Low-pass filter and threshold evaluation
 └─ Serial telemetry @ 115200 baud
      │ USB serial
      ▼
 Python desktop GUI
 ├─ Serial data reception
 ├─ Five-sample median filter
 └─ Angle/status visualization
```

The current firmware uses the Arduino framework (`setup()` / `loop()`). FreeRTOS and Zephyr are **future evaluation options**, not part of the current baseline. EEPROM fault-event logging is also planned, not yet implemented.

## Repository layout

```text
Smart-Hospital-Bed-Safety-Monitor-using-Arduino/
├── firmware/
│   └── arduino_uno_r4_minima/
│       ├── arduino_uno_r4_minima.ino
│       └── README.md
├── software/
│   └── desktop_gui/
│       ├── bed_monitor_gui.py
│       ├── requirements.txt
│       └── README.md
├── images/
│   ├── Angle Monitor GUI.png
│   ├── Architecture.png
│   └── Smart Hospital Bed Wiring Diagram.png
├── docs/
│   ├── ARCHITECTURE.md
│   ├── HARDWARE.md
│   ├── SERIAL_PROTOCOL.md
│   ├── TEST_PLAN.md
│   └── ROADMAP.md
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── PULL_REQUEST_TEMPLATE.md
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## Hardware

- Arduino UNO R4 Minima
- MPU-6500 accelerometer/gyroscope breakout
- Jumper wires and USB cable
- A computer capable of running Python 3 and the desktop GUI

### Current wiring assumptions

| Sensor signal | Arduino UNO R4 Minima |
|---|---|
| VCC | Use the breakout's documented supported voltage |
| GND | GND |
| SDA | SDA |
| SCL | SCL |
| INT | Digital pin 3 |

**Important:** Check your specific sensor breakout's voltage requirements and pinout. Do not assume every MPU-6500 breakout accepts 5 V logic or power.

## Firmware setup

1. Install the Arduino IDE or Arduino CLI.
2. Install/select the Arduino UNO R4 Boards platform.
3. Open `firmware/arduino_uno_r4_minima/arduino_uno_r4_minima.ino`.
4. Select **Arduino UNO R4 Minima** and the correct serial port.
5. Compile and upload.
6. Open Serial Monitor at `115200` baud and check the initialization diagnostics and framed telemetry after a motion event.

The firmware is configured for an MPU-6500-compatible module at I²C address `0x68`, with its INT output connected to digital pin 3. Verify your exact breakout-board voltage and logic-level requirements before wiring.

## Desktop GUI setup

1. Install Python 3.9 or newer.
2. Change to `software/desktop_gui/`.
3. Create and activate a virtual environment (instructions are in that directory's README).
4. Install dependencies with `python -m pip install -r requirements.txt`.
5. Set `SERIAL_PORT` in `bed_monitor_gui.py` to the Arduino port and run `python bed_monitor_gui.py`.
3. Create and activate a virtual environment.
4. Install the dependencies actually imported by your GUI (for example, `pyserial` if it uses `serial`; Tkinter is included with many Python distributions but may be packaged separately on some systems).
5. Run the GUI script and select the correct serial port.

Example virtual-environment commands:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install pyserial
```

The GUI imports `pyserial`; install the pinned dependency from `software/desktop_gui/requirements.txt` using `python -m pip install -r requirements.txt` from that directory.

## Configuration

Current known values from the project baseline:

| Setting | Current value |
|---|---|
| I²C address | `0x68` |
| Interrupt pin | Digital pin `3` |
| Inclination threshold | `30.0°` |
| Firmware low-pass alpha | `0.15` |
| Display deadband | `0.5°` |
| Serial baud rate | `115200` |
| GUI median filter | 5 samples |
| Firmware framework | Arduino core for UNO R4 Minima |

The actual accelerometer register setup and interrupt behavior should be confirmed against the exact sketch and sensor breakout used.

## Validation checklist

- [ ] Sensor responds at I²C address `0x68`.
- [ ] Firmware identifies/configures the expected sensor registers.
- [ ] Pitch changes in the expected direction when the board is tilted.
- [ ] Low-pass filtering reduces jitter without unacceptable delay.
- [ ] Threshold behavior at, below, and above `30°` is checked.
- [ ] Serial output is parsed correctly by the GUI.
- [ ] Disconnecting the sensor or serial cable is handled safely and visibly.
- [ ] Interrupt behavior is tested under repeated motion and during startup.
- [ ] Tests are repeated after any firmware, wiring, or RTOS change.

See [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md).

## Roadmap

- [x] Accelerometer-based inclination estimate
- [x] Firmware low-pass filtering
- [x] Display deadband
- [x] Python GUI median filtering
- [x] Serial telemetry integration
- [ ] Add EEPROM/non-volatile fault-event logging (event count and last fault angle)
- [ ] Evaluate FreeRTOS task architecture on a separate branch
- [ ] Evaluate a Zephyr RTOS port and build/debug toolchain
- [ ] Add automated or repeatable test procedures and capture validation results

Power optimization is intentionally out of scope for the current roadmap phase.

## Safety and limitations

This is an educational/prototyping project, not a medical device. Inclination alone does not establish patient fall risk, and a prototype's sensor readings, firmware, communications and GUI can fail. Do not rely on this project for clinical decisions or as a replacement for approved monitoring, supervision, alarms, or hospital equipment.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). If you fork or extend the project, document hardware revisions, sensor part numbers, test conditions and known limitations.

## License

Released under the MIT License; see [`LICENSE`](LICENSE). If you prefer another license, change this before making the repository public.


## Wake-on-Motion and GUI idle behaviour

The firmware transmits a framed angle/status message when it handles a Wake-on-Motion event; it does not continuously stream readings while stationary. The GUI therefore treats a quiet, still-connected serial session as **waiting/idle**, not automatically as a sensor failure. A serial exception is handled as a connection problem and triggers reconnection attempts. The displayed angle/status during idle is the last event received, not a live continuously sampled measurement.

## Images

Project visuals are available in [`images/`](images/), including the architecture diagram, wiring diagram, and desktop GUI screenshot.

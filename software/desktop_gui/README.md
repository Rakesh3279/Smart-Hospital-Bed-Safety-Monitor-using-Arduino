
# Desktop GUI – Smart Hospital Bed Safety Monitor

A Python Tkinter application that receives serial data from the Arduino UNO R4 Minima and displays the bed inclination angle and safety status.

## Requirements

- Python 3.9 or newer
- Arduino UNO R4 Minima
- USB serial connection
- pyserial

## Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Configuration

Open `bed_monitor_gui.py` and configure the Arduino serial port:

```python
SERIAL_PORT = "COM5"
BAUD_RATE = 115200
```

Change COM5 to the port assigned to your Arduino.

## Run

```bash
python bed_monitor_gui.py
```

## Serial communication protocol

The GUI expects messages in the following format:

```text
[START]:DEVICE-ID:12.34:STATUS_SAFE:[END]
[START]:DEVICE-ID:35.20:ALARM_FALL_RISK:[END]
```

The Arduino determines the safety status. The Python GUI applies median filtering to the displayed angle and visualizes the received status. Because the firmware uses Wake-on-Motion, it sends data on motion events rather than continuously. After a valid event, a quiet serial session is shown as sensor idle and the GUI retains the last reported angle/status; this is not a fresh live measurement.

## Safety Disclaimer

This is a prototype engineering project, not a certified medical device. It must not be used for clinical decisions or as the sole means of patient monitoring or fall prevention.
s
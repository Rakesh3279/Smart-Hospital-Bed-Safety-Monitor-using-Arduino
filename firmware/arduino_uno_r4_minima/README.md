# Arduino UNO R4 Minima firmware

The current Arduino sketch is `arduino_uno_r4_minima.ino`. Open this file in Arduino IDE with the Arduino UNO R4 Minima board selected.

## Current baseline notes

- Board: Arduino UNO R4 Minima
- MCU: Renesas RA4M1
- Framework: Arduino
- Sensor: MPU-6500, expected I²C address `0x68`
- Interrupt signal: digital pin 3
- Threshold: `30.0°`
- Software low-pass filter alpha: `0.15`
- Display deadband: `0.5°`
- Serial baud: `115200`
- Current code includes `setup()`, `loop()`, I²C register helpers, interrupt handling, pitch calculation and telemetry.

Do not copy an unverified sample or RTOS experiment over the known-working baseline. Keep RTOS experiments on separate branches or in separate directories after they have been built and tested.

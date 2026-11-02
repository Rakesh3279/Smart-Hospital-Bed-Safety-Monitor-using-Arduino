# Architecture

## Current data path

1. The MPU-6500 measures acceleration.
2. The Arduino firmware reads sensor data over I²C.
3. The firmware calculates an inclination estimate from acceleration.
4. A first-order low-pass filter smooths the pitch (`alpha = 0.15`).
5. The firmware compares the filtered pitch against the configured threshold (`30°`).
6. The firmware sends telemetry over USB serial at `115200` baud.
7. The Python/Tkinter GUI parses incoming telemetry and applies a five-sample median filter for display stability.

## Filtering layers

- **Firmware low-pass filter:** reduces rapid changes in the calculated pitch.
- **Display deadband:** updates the displayed value only when the filtered angle differs by at least `0.5°`.
- **GUI median filter:** reduces isolated spikes in the displayed stream.

These layers have different purposes. The display deadband should not be described as sensor filtering, and the GUI median filter should not be described as part of the MCU firmware.

## Interrupt model

The firmware uses a sensor interrupt signal connected to digital pin 3 and an ISR notification flag. The exact event retention and wake-up behavior must be validated on hardware; a Boolean notification can coalesce multiple events. Do not claim lossless event capture without testing and an appropriate event-recording design.

## Future architecture experiments

FreeRTOS and Zephyr are not part of the current baseline. Evaluate them separately and compare build reproducibility, I²C support, interrupt behavior, timing, memory usage and serial GUI compatibility before adopting either.

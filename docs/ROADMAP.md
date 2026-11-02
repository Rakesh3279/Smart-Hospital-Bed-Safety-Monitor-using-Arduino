# Roadmap

## Current baseline

- Arduino framework on UNO R4 Minima
- MPU-6500-compatible sensor over I²C
- Pitch estimation and firmware low-pass filtering
- Display deadband
- Python/Tkinter GUI with five-sample median filtering
- Serial telemetry

## Next: reliability and observability

1. Implement EEPROM/non-volatile fault-event logging: event count and last fault angle.
2. Define and test behavior for sensor read failures, malformed serial packets and restarts.
3. Add repeatable hardware test records and documented limitations.

## RTOS evaluations (separate experiments)

- FreeRTOS: verify a compatible RA4M1/UNO R4 Minima port, Arduino core integration, ISR-safe signaling, stack sizes and build/flash process.
- Zephyr: verify the official board target and supported peripheral/flash/debug workflow; port I²C, GPIO interrupt and UART code using Zephyr APIs.
- Compare the same acceptance tests on the Arduino baseline and each RTOS experiment.

## Deferred

Power optimization is intentionally deferred. RTOS migration and power tuning should not be mixed into the initial repository publication.

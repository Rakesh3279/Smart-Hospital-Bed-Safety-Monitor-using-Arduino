# Verification and test plan

This plan describes suggested prototype tests, not completed test results. Record observed outcomes, firmware revision, hardware revision and test conditions before marking an item as passed.

## Sensor and angle calculation

- [ ] Confirm I²C address and sensor identity.
- [ ] Capture stationary readings at several known orientations.
- [ ] Check pitch sign and magnitude for each orientation.
- [ ] Check behavior near the angle wraparound and near level.
- [ ] Verify sensor read failures do not silently reuse stale values as valid readings.

## Filter and threshold

- [ ] Confirm first reading initializes the filtered and displayed values.
- [ ] Verify the low-pass filter responds smoothly to a step change.
- [ ] Verify the `0.5°` display deadband in both directions.
- [ ] Verify threshold behavior below, exactly at, and above `30°` (the current comparison is `>` if the sketch uses the documented expression).
- [ ] Record response delay and any false threshold transitions.

## Interrupt handling

- [ ] Verify interrupt pin polarity and latch behavior against the exact sensor configuration.
- [ ] Test isolated motion events and repeated events.
- [ ] Test events during sensor reads and serial output.
- [ ] Check how the sensor's read-to-clear status register is handled.
- [ ] Confirm the CPU wakes as expected; do not infer wake behavior from a successful interrupt alone.

## Serial and GUI

- [ ] Confirm baud rate and packet format match.
- [ ] Verify GUI behavior with malformed or incomplete serial lines.
- [ ] Test serial disconnect/reconnect.
- [ ] Check GUI responsiveness during high-rate telemetry.
- [ ] Verify median-filter behavior at startup and after disconnects.

## Fault handling

- [ ] Disconnect the sensor and verify visible error behavior.
- [ ] Test I²C timeout handling.
- [ ] Test reboot and recovery after an error.
- [ ] When non-volatile logging is implemented, test persistence across reset and power loss.

## Reporting results

For each test, record: date, code commit, board, sensor breakout, setup, expected result, actual result, pass/fail and follow-up issue.

# Serial protocol

The firmware streams telemetry over USB serial at `115200` baud. The Python GUI depends on the exact packet format emitted by the current sketch.

Before documenting the protocol as stable:

1. Copy a real sample line from Serial Monitor.
2. Record the delimiter, field order, precision, line ending and status values.
3. Add valid and invalid packet examples.
4. Ensure the GUI can handle partial lines, malformed input, disconnects and reconnects.

Do not invent packet examples here. Add the exact output from the tested firmware and keep this document synchronized with the parser.


## Transmission timing

Telemetry is event-driven: the firmware sends a framed message after it handles a valid Wake-on-Motion interrupt and reads the accelerometer. It does not send a periodic heartbeat in the current low-power design. A stationary sensor can therefore produce no new framed messages for an extended period. The GUI indicates waiting/idle and retains the last event's values; those values must not be interpreted as continuously refreshed measurements.

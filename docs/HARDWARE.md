# Hardware notes

## Known components

- Arduino UNO R4 Minima (Renesas RA4M1, Arm Cortex-M4)
- MPU-6500 breakout, expected I²C address `0x68`
- Interrupt wire from sensor to digital pin 3
- USB serial connection to a host computer

## Wiring

| Sensor pin | Board connection | Notes |
|---|---|---|
| VCC | Board supply appropriate for breakout | Verify the breakout's voltage range |
| GND | GND | Common ground required |
| SDA | SDA | I²C data |
| SCL | SCL | I²C clock |
| INT | D3 | Interrupt signal |

Use the exact pin labels on your board and module. Breakout boards differ in voltage regulation and logic-level compatibility.

## Sensor identity

The project history indicates WHO_AM_I was observed as `0x70` at address `0x68`, suggesting an MPU-6500-compatible device. Confirm the chip and breakout revision from their markings/datasheet before publishing claims about exact sensor identity or relying on register behavior.

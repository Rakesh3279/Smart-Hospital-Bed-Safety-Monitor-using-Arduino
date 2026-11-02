
#include <Arduino.h>
#include <Wire.h>
#include <math.h>

// MPU-6500 I2C configuration
#define MPU_ADDR              0x68

#define REG_SMPLRT_DIV        0x19
#define REG_ACCEL_CONFIG      0x1C
#define REG_ACCEL_CONFIG2     0x1D
#define REG_LP_ACCEL_ODR      0x1E
#define REG_WOM_THR           0x1F
#define REG_MOT_DETECT_CTRL   0x69
#define REG_PWR_MGMT_1        0x6B
#define REG_PWR_MGMT_2        0x6C
#define REG_INT_PIN_CFG       0x37
#define REG_INT_ENABLE        0x38
#define REG_INT_STATUS        0x3A
#define REG_ACCEL_XOUT_H      0x3B
#define REG_WHO_AM_I          0x75

#define INT_PIN               3

// Fall-risk threshold
const float TRG_INCLINE = 30.0f;

// Low-pass filter and display deadband
const float alpha = 0.15f;
const float DISPLAY_DEADBAND = 0.5f;

// WOM threshold: 20 LSB * 4 mg = 80 mg
const uint8_t WOM_THRESHOLD = 0x14;

// Low-power accelerometer sample rate:
// LP_ACCEL_ODR = 0x03 -> approximately 1.95 Hz
const uint8_t WOM_ODR = 0x03;

const char* device_uuid = "MCU-R4-NATIVE-WFI";

// Accelerometer readings
int16_t raw_acc_x = 0;
int16_t raw_acc_y = 0;
int16_t raw_acc_z = 0;

float filtered_pitch = 0.0f;
float displayed_pitch = 0.0f;
bool first_reading = true;

volatile bool motion_detected = false;

// ---------------- Register helpers ----------------

bool writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission(true) == 0;
}

bool readRegister(uint8_t reg, uint8_t &value) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);

  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  if (Wire.requestFrom(MPU_ADDR, (uint8_t)1,
                       (uint8_t)true) != 1) {
    return false;
  }

  value = Wire.read();
  return true;
}

bool readAccelerometer() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(REG_ACCEL_XOUT_H);

  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  if (Wire.requestFrom(MPU_ADDR, (uint8_t)6,
                       (uint8_t)true) != 6) {
    return false;
  }

  uint8_t bytes[6];
  for (int i = 0; i < 6; i++) {
    bytes[i] = Wire.read();
  }

  raw_acc_x = (int16_t)(((uint16_t)bytes[0] << 8) | bytes[1]);
  raw_acc_y = (int16_t)(((uint16_t)bytes[2] << 8) | bytes[3]);
  raw_acc_z = (int16_t)(((uint16_t)bytes[4] << 8) | bytes[5]);

  return !(raw_acc_x == 0 && raw_acc_y == 0 && raw_acc_z == 0);
}

void mpu_interrupt_handler() {
  motion_detected = true;
}

// ---------------- WOM initialization ----------------

bool initializeWOM() {
  uint8_t whoAmI = 0;

  if (!readRegister(REG_WHO_AM_I, whoAmI)) {
    Serial.println("ERROR: Cannot read WHO_AM_I.");
    return false;
  }

  Serial.print("WHO_AM_I: 0x");
  Serial.println(whoAmI, HEX);

  // Reset device
  if (!writeRegister(REG_PWR_MGMT_1, 0x80)) {
    Serial.println("ERROR: Sensor reset failed.");
    return false;
  }

  delay(100);

  // Wake up; CYCLE=0, SLEEP=0, STANDBY=0
  if (!writeRegister(REG_PWR_MGMT_1, 0x00)) {
    Serial.println("ERROR: Sensor wake failed.");
    return false;
  }

  delay(10);

  // Disable gyro axes; keep all accelerometer axes enabled
  if (!writeRegister(REG_PWR_MGMT_2, 0x07)) {
    Serial.println("ERROR: PWR_MGMT_2 configuration failed.");
    return false;
  }

  // Accelerometer full-scale range: +/-2g.
  // Bits 4:3 = 00; reserved bits remain zero.
  if (!writeRegister(REG_ACCEL_CONFIG, 0x00)) {
    Serial.println("ERROR: ACCEL_CONFIG failed.");
    return false;
  }

  // ACCEL_FCHOICE_B=0, A_DLPFCFG=001 (184 Hz bandwidth)
  if (!writeRegister(REG_ACCEL_CONFIG2, 0x01)) {
    Serial.println("ERROR: ACCEL_CONFIG2 failed.");
    return false;
  }

  // Wake-on-motion threshold
  if (!writeRegister(REG_WOM_THR, WOM_THRESHOLD)) {
    Serial.println("ERROR: WOM_THR failed.");
    return false;
  }

  // Low-power accelerometer sampling rate
  if (!writeRegister(REG_LP_ACCEL_ODR, WOM_ODR)) {
    Serial.println("ERROR: LP_ACCEL_ODR failed.");
    return false;
  }

  // Enable accelerometer intelligence and compare mode
  if (!writeRegister(REG_MOT_DETECT_CTRL, 0xC0)) {
    Serial.println("ERROR: MOT_DETECT_CTRL failed.");
    return false;
  }

  // INT_LEVEL=1: active-low interrupt; LATCH_INT_EN=1: latched interrupt.
  // INT_ANYRD_2CLEAR remains 0, so INT_STATUS read clears the latch.
  if (!writeRegister(REG_INT_PIN_CFG, 0xA0)) {
    Serial.println("ERROR: INT_PIN_CFG failed.");
    return false;
  }

  // Enable WOM interrupt only
  if (!writeRegister(REG_INT_ENABLE, 0x40)) {
    Serial.println("ERROR: INT_ENABLE failed.");
    return false;
  }

  // Clear pending status before entering WOM mode
  uint8_t status;
  if (!readRegister(REG_INT_STATUS, status)) {
    Serial.println("ERROR: Cannot clear initial interrupt status.");
    return false;
  }

  // Enable low-power accelerometer cycle mode.
  // CYCLE=1, SLEEP=0, CLKSEL=internal oscillator.
  if (!writeRegister(REG_PWR_MGMT_1, 0x20)) {
    Serial.println("ERROR: Cannot enable cycle mode.");
    return false;
  }

  delay(20);

  // Report configured register values
  const uint8_t regs[] = {
    REG_PWR_MGMT_1,
    REG_PWR_MGMT_2,
    REG_ACCEL_CONFIG,
    REG_ACCEL_CONFIG2,
    REG_LP_ACCEL_ODR,
    REG_WOM_THR,
    REG_MOT_DETECT_CTRL,
    REG_INT_ENABLE
  };

  Serial.println("WOM register readback:");

  for (uint8_t reg : regs) {
    uint8_t value;

    if (readRegister(reg, value)) {
      Serial.print("Register 0x");
      Serial.print(reg, HEX);
      Serial.print(" = 0x");
      Serial.println(value, HEX);
    } else {
      Serial.print("Read failed for register 0x");
      Serial.println(reg, HEX);
    }
  }

  // Reading registers above can clear a latched interrupt.
  if (!readRegister(REG_INT_STATUS, status)) {
    Serial.println("ERROR: Cannot clear status after readback.");
    return false;
  }

  return true;
}

// ---------------- Arduino setup ----------------

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println();
  Serial.println("Smart Hospital Bed Safety Monitor");
  Serial.println("Initializing MPU-6500 WOM...");

  Wire.begin();
  Wire.setWireTimeout(50000, true);

  pinMode(INT_PIN, INPUT_PULLUP);

  if (!initializeWOM()) {
    Serial.println("Initialization failed. Halting.");
    while (true) {
      delay(1000);
    }
  }

  // Attach after initialization and status clearing
  attachInterrupt(
    digitalPinToInterrupt(INT_PIN),
    mpu_interrupt_handler,
    FALLING
  );

  Serial.println("WOM initialized.");
  Serial.println("Waiting for motion...");
  Serial.flush();
}

// ---------------- Arduino loop ----------------

void loop() {
  // Avoid the check-then-sleep race: keep interrupts disabled between the
  // flag check and WFI. A pending external interrupt can wake the Cortex-M4;
  // its ISR runs when interrupts are re-enabled below.
  noInterrupts();
  if (!motion_detected) {
    __WFI();
  }

  bool event = motion_detected;
  motion_detected = false;
  interrupts();

  if (!event) {
    // A pending interrupt may run immediately after interrupts are enabled.
    // In that case the next loop iteration consumes the newly-set flag.
    return;
  }

  // Read status exactly once for this event.
  uint8_t status;

  if (!readRegister(REG_INT_STATUS, status)) {
    Serial.println("ERROR: Failed to read INT_STATUS.");
    return;
  }

  Serial.print("INT_STATUS: 0x");
  Serial.println(status, HEX);

  // Bit 6 = WOM_INT; bit 0 = RAW_DATA_RDY_INT
  if ((status & 0x40) == 0) {
    Serial.println("No WOM status bit set.");
    return;
  }

  Serial.println("WOM event detected.");

  if (!readAccelerometer()) {
    Serial.println("ERROR: Accelerometer read failed.");
    return;
  }

  // +/-2g range: 16384 LSB/g
  float x = (float)raw_acc_x;
  float y = (float)raw_acc_y;
  float z = (float)raw_acc_z;

  float current_pitch =
      fabs(atan2(y, sqrt(x * x + z * z)) * 180.0f / PI);

  if (first_reading) {
    filtered_pitch = current_pitch;
    displayed_pitch = current_pitch;
    first_reading = false;
  } else {
    filtered_pitch =
        alpha * current_pitch +
        (1.0f - alpha) * filtered_pitch;

    if (fabs(filtered_pitch - displayed_pitch)
        >= DISPLAY_DEADBAND) {
      displayed_pitch = filtered_pitch;
    }
  }

  bool threshold_violation = filtered_pitch > TRG_INCLINE;

  Serial.print("[START]:");
  Serial.print(device_uuid);
  Serial.print(":");
  Serial.print(displayed_pitch, 2);
  Serial.print(":");
  Serial.print(threshold_violation
      ? "ALARM_FALL_RISK"
      : "STATUS_SAFE");
  Serial.println(":[END]");

  Serial.flush();
}

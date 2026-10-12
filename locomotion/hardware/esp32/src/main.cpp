#include <Arduino.h>
#include <ArduinoJson.h>
#include <SMS_STS.h>
#include "calibration_profile.h"
#ifndef MIST_MPU6050
#define MIST_MPU6050 0
#endif
#if MIST_MPU6050
#include <Wire.h>
uint8_t mpuAddress = 0;
uint32_t lastImuAt = 0;

bool mpuWrite(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(mpuAddress); Wire.write(reg); Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool mpuRead(uint8_t reg, uint8_t* bytes, uint8_t count) {
  Wire.beginTransmission(mpuAddress); Wire.write(reg);
  if (Wire.endTransmission(false) != 0 || Wire.requestFrom(mpuAddress, count) != count) return false;
  for (uint8_t i = 0; i < count; ++i) bytes[i] = Wire.read();
  return true;
}

void setupImu() {
  Wire.begin(21, 22, 400000); Wire.setTimeOut(4);
  for (uint8_t address : {uint8_t(0x68), uint8_t(0x69)}) {
    mpuAddress = address;
    uint8_t who = 0;
    if (!mpuRead(0x75, &who, 1) || who != 0x68) continue;
    // PLL clock, DLPF=3, 100 Hz hardware sampling, +/-250 deg/s and +/-2g.
    if (mpuWrite(0x6B, 1) && mpuWrite(0x1A, 3) && mpuWrite(0x19, 9) &&
        mpuWrite(0x1B, 0) && mpuWrite(0x1C, 0)) return;
  }
  mpuAddress = 0;
}

void reportImu() {
  if (millis() - lastImuAt < 20) return;
  lastImuAt = millis();
  uint8_t bytes[14];
  StaticJsonDocument<512> doc;
  doc["kind"] = "imu"; doc["source"] = "mpu6050"; doc["t_ms"] = lastImuAt;
  bool valid = mpuAddress != 0 && mpuRead(0x3B, bytes, 14);
  doc["valid"] = valid;
  if (valid) {
    JsonArray accel = doc.createNestedArray("accel_m_s2"), gyro = doc.createNestedArray("gyro_rad_s");
    for (uint8_t i = 0; i < 3; ++i) {
      int16_t a = int16_t((uint16_t(bytes[i*2]) << 8) | bytes[i*2+1]);
      int16_t g = int16_t((uint16_t(bytes[8+i*2]) << 8) | bytes[9+i*2]);
      accel.add(a * (9.80665f / 16384.f)); gyro.add(g * (PI / (180.f * 131.f)));
    }
  }
  serializeJson(doc, Serial); Serial.println();
}
#endif

// WROOM UART2, Waveshare Adapter A, jumper A. Its header uses RX-RX / TX-TX.
constexpr uint8_t BUS_RX = 16, BUS_TX = 17, ESTOP_NC_PIN = 27;
constexpr uint32_t WATCHDOG_MS = 300, ARM_WINDOW_MS = 60000;
constexpr uint32_t MAX_TELEMETRY_AGE_MS = 300;
constexpr float MAX_TICKS_PER_SECOND = 0.5f * 4096 / (2 * PI);
constexpr int CURRENT_RAW_LIMIT = 120;  // Raw units: verify with the owned servo variant.
constexpr int TEMPERATURE_LIMIT_C = 50, RAIL_MIN_DECIVOLT = 90, RAIL_MAX_DECIVOLT = 126;
constexpr uint16_t TORQUE_LIMIT_PER_MILLE = 200, GOAL_SPEED_RAW = 200;
constexpr uint8_t GOAL_ACCELERATION_RAW = 4;
SMS_STS bus;
bool armed = false;
String fault, input;
uint32_t lastSeq = 0, lastHeartbeat = 0, armedAt = 0, lastTargetAt = 0;
uint32_t lastPoll = 0, lastReport = 0;
uint8_t pollIndex = 0;
int16_t targetTicks[12] = {0};
float slewCredit[12] = {0};
uint32_t intentGeneration = 0;
uint16_t speeds[12];
uint8_t accelerations[12], ids[12];
struct Sample { int tick = -1, speed = 0, current = 0, voltage = 0, temperature = 0; uint32_t at = 0; bool valid = false; } samples[12];

void torqueOff() {
  if (PROFILE_CONFIGURED) bus.EnableTorque(0xFE, 0);
  armed = false;
  ++intentGeneration;
}

void trip(const char* reason) {
  torqueOff();
  if (fault.length() == 0) fault = reason;
}

bool physicalStop() { return digitalRead(ESTOP_NC_PIN) == HIGH; }

void watchdog() {
  if (!armed) return;
  uint32_t now = millis();
  if (physicalStop()) trip("physical stop loop open");
  else if (now - lastHeartbeat > WATCHDOG_MS) trip("heartbeat watchdog");
  else if (now - armedAt > ARM_WINDOW_MS) trip("commissioning window expired");
}

bool readJoint(uint8_t i) {
  Sample& s = samples[i];
  if (bus.FeedBack(ids[i]) < 0 || bus.getLastError() != 0 || bus.getState() != 0) { s.valid = false; return false; }
  s.tick = bus.ReadPos(-1);
  s.speed = bus.ReadSpeed(-1);
  s.current = bus.ReadCurrent(-1);
  s.voltage = bus.ReadVoltage(-1);
  s.temperature = bus.ReadTemper(-1);
  s.at = millis();
  s.valid = s.tick >= 0 && s.tick <= 4095;
  return s.valid;
}

bool sampleSafe(uint8_t i) {
  const Sample& s = samples[i];
  return s.valid && millis() - s.at <= MAX_TELEMETRY_AGE_MS &&
         s.tick >= MIN_TICKS[i] && s.tick <= MAX_TICKS[i] &&
         abs(s.current) <= CURRENT_RAW_LIMIT && s.temperature < TEMPERATURE_LIMIT_C &&
         s.voltage >= RAIL_MIN_DECIVOLT && s.voltage <= RAIL_MAX_DECIVOLT;
}

void info(JsonDocument& doc) {
  doc["armed"] = armed;
  doc["intent_generation"] = intentGeneration;
  doc["fault"] = fault.length() ? fault.c_str() : nullptr;
  doc["configured"] = PROFILE_CONFIGURED;
  doc["profile_hash"] = PROFILE_HASH;
  doc["last_seq"] = lastSeq;
  doc["estop_open"] = physicalStop();
  doc["mpu6050_enabled"] = bool(MIST_MPU6050);
  JsonArray joints = doc.createNestedArray("joints");
  JsonArray ticks = doc.createNestedArray("ticks");
  if (!PROFILE_CONFIGURED) return;
  for (uint8_t i = 0; i < 12; ++i) {
    const Sample& s = samples[i];
    JsonObject row = joints.createNestedObject();
    row["id"] = ids[i]; row["tick"] = s.tick; row["speed_raw"] = s.speed;
    row["current_raw"] = s.current; row["voltage_v"] = s.voltage / 10.f;
    row["temperature_c"] = s.temperature; row["valid"] = s.valid;
    row["age_ms"] = millis() - s.at;
    ticks.add(s.tick);
  }
}

void ack(const char* op, uint32_t seq, bool ok, const char* error = nullptr, bool withInfo = false) {
  StaticJsonDocument<4096> doc;
  doc["kind"] = "ack"; doc["op"] = op; doc["seq"] = seq; doc["ok"] = ok;
  if (error) doc["error"] = error;
  if (withInfo) info(doc);
  serializeJson(doc, Serial); Serial.println();
}

void reject(const char* op, uint32_t seq, const char* error) {
  if (armed) trip(error);
  ack(op, seq, false, error);
}

bool armSnapshot() {
  // Read and hold the measured pose before torque is enabled. No neutral-pose jump.
  for (uint8_t i = 0; i < 12; ++i) {
    if (physicalStop() || !readJoint(i) || !sampleSafe(i)) return false;
    if (bus.readByte(ids[i], SMS_STS_MODE) != 0 || bus.getLastError() != 0 || bus.getState() != 0) return false;
    if (bus.readByte(ids[i], SMS_STS_TORQUE_ENABLE) != 0 || bus.getLastError() != 0 || bus.getState() != 0) return false;
    targetTicks[i] = samples[i].tick;
    if (bus.writeWord(ids[i], SMS_STS_TORQUE_LIMIT_L, TORQUE_LIMIT_PER_MILLE) != 1 || bus.getLastError() != 0 || bus.getState() != 0) return false;
  }
  bus.SyncWritePosEx(ids, 12, targetTicks, speeds, accelerations);
  for (uint8_t i = 0; i < 12; ++i) {
    if (physicalStop() || bus.EnableTorque(ids[i], 1) != 1 || bus.getLastError() != 0 || bus.getState() != 0) return false;
    if (bus.readByte(ids[i], SMS_STS_TORQUE_ENABLE) != 1 || bus.getLastError() != 0 || bus.getState() != 0) return false;
  }
  return !physicalStop();
}

void processLine(const String& line) {
  watchdog();
  StaticJsonDocument<2048> doc;
  if (deserializeJson(doc, line)) { reject("parse", 0, "invalid JSON"); return; }
  const char* op = doc["op"] | "";
  uint32_t seq = doc["seq"] | 0U;
  if (strcmp(op, "status") == 0) { ack(op, seq, true, nullptr, true); return; }
  // A stop is accepted even if its sequence is stale.
  if (strcmp(op, "estop") == 0 || strcmp(op, "disarm") == 0) {
    if (seq > lastSeq) lastSeq = seq;
    if (strcmp(op, "estop") == 0) trip("remote estop"); else torqueOff();
    ack(op, seq, true, nullptr, true); return;
  }
  if (!doc["seq"].is<uint32_t>() || seq == 0 || seq <= lastSeq || seq > 0x7FFFFFFF) {
    reject(op, seq, "stale or invalid sequence"); return;
  }
  lastSeq = seq;
  if (strcmp(op, "clear") == 0) {
    if (armed || physicalStop()) { reject(op, seq, "stop loop open or controller armed"); return; }
    fault = ""; ack(op, seq, true); return;
  }
  if (!PROFILE_CONFIGURED) { reject(op, seq, "R7 calibration profile is unconfigured"); return; }
  if (physicalStop()) { trip("physical stop loop open"); reject(op, seq, "physical stop loop open"); return; }
  if (fault.length()) { reject(op, seq, "latched fault: inspect and clear first"); return; }
  if (strcmp(op, "arm") == 0) {
    if (armed || !doc["intent_generation"].is<uint32_t>() || doc["intent_generation"].as<uint32_t>() != intentGeneration) { reject(op, seq, "stale or duplicate arm intent"); return; }
    const char* hash = doc["profile_hash"] | "";
    if (strcmp(hash, PROFILE_HASH) != 0) { reject(op, seq, "host profile hash mismatch"); return; }
    if (!armSnapshot()) { trip("arm telemetry or mode check failed"); reject(op, seq, "arm telemetry or mode check failed"); return; }
    for (uint8_t i=0;i<12;++i) slewCredit[i]=2.f;
    ++intentGeneration;
    armed = true; armedAt = lastHeartbeat = lastTargetAt = millis();
    ack(op, seq, true, nullptr, true); return;
  }
  if (!armed) { reject(op, seq, "disarmed"); return; }
  if (strcmp(op, "heartbeat") == 0) { lastHeartbeat = millis(); ack(op, seq, true); return; }
  if (strcmp(op, "ticks") == 0) {
    JsonArray ticks = doc["ticks"].as<JsonArray>();
    if (ticks.size() != 12) { reject(op, seq, "expected 12 ticks"); return; }
    int16_t next[12];
    float elapsedCredit = MAX_TICKS_PER_SECOND * min(uint32_t(100), uint32_t(millis() - lastTargetAt)) / 1000.f;
    float remaining[12];
    for (uint8_t i = 0; i < 12; ++i) {
      if (!ticks[i].is<int>() || !sampleSafe(i)) { reject(op, seq, "invalid ticks or stale/unsafe telemetry"); return; }
      int tick = ticks[i].as<int>();
      if (tick < MIN_TICKS[i] || tick > MAX_TICKS[i] || abs(tick - targetTicks[i]) > min(MAX_TICKS_PER_SECOND*.1f+2.f,slewCredit[i]+elapsedCredit)) {
        reject(op, seq, "target limit or rate violation"); return;
      }
      remaining[i]=min(MAX_TICKS_PER_SECOND*.1f+2.f,slewCredit[i]+elapsedCredit)-abs(tick-targetTicks[i]);
      next[i] = tick;
    }
    bus.SyncWritePosEx(ids, 12, next, speeds, accelerations);
    memcpy(slewCredit,remaining,sizeof(remaining));
    memcpy(targetTicks, next, sizeof(next)); lastTargetAt = millis();
    ack(op, seq, true); return;
  }
  reject(op, seq, "unknown operation");
}

void setup() {
  Serial.begin(460800);
  Serial2.begin(1000000, SERIAL_8N1, BUS_RX, BUS_TX);
  bus.pSerial = &Serial2; bus.IOTimeOut = 3;
  pinMode(ESTOP_NC_PIN, INPUT_PULLUP);
#if MIST_MPU6050
  setupImu();
#endif
  input.reserve(1024);
  for (uint8_t i = 0; i < 12; ++i) {
    ids[i] = SERVO_IDS[i]; speeds[i] = GOAL_SPEED_RAW; accelerations[i] = GOAL_ACCELERATION_RAW;
  }
  torqueOff();
  ack("boot", 0, true, nullptr, true);
}

void loop() {
  uint32_t now = millis();
  watchdog();
#if MIST_MPU6050
  reportImu();
#endif
  while (Serial.available()) {
    watchdog();
    char c = Serial.read();
    if (c == '\n') { processLine(input); input = ""; }
    else if (c != '\r') {
      if (input.length() >= 1024) { input = ""; trip("host line overflow"); break; }
      input += c;
    }
  }
  if (PROFILE_CONFIGURED && now - lastPoll >= 15) {
    lastPoll = now;
    if ((!readJoint(pollIndex) || !sampleSafe(pollIndex)) && armed) trip("servo telemetry fault");
    pollIndex = (pollIndex + 1) % 12;
  }
  if (now - lastReport >= 250) {
    lastReport = now;
    StaticJsonDocument<4096> doc;
    doc["kind"] = "telemetry"; info(doc);
    serializeJson(doc, Serial); Serial.println();
  }
}

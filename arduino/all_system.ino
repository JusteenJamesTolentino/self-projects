#include <SPI.h>
#include <MFRC522.h>
#include "DHT.h"

// ---------------- Pins ----------------
// RFID (MFRC522)
#define RFID_SS   10
#define RFID_RST  9
// Traffic LEDs (TMS)
#define LED_RED    4
#define LED_YELLOW 5
#define LED_GREEN  6
// DHT11
#define DHTPIN 7
#define DHTTYPE DHT11
// Ultrasonic
#define US_TRIG 2
#define US_ECHO 3

// ---------------- Globals ----------------
MFRC522 rfid(RFID_SS, RFID_RST);
DHT dht(DHTPIN, DHTTYPE);

// Ultrasonic state
unsigned long lastPingMs = 0;
bool ultrasonicStreaming = false;
unsigned long lastStreamMs = 0;
const unsigned long US_PING_MIN_MS = 60;    // ~ >16Hz safe
const unsigned long US_STREAM_INTERVAL_MS = 200; // ~5Hz (align with GUI 200ms loop)

// Helpers
float readDistanceCM() {
  // trigger pulse
  digitalWrite(US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(US_TRIG, LOW);
  // echo width
  unsigned long dur = pulseIn(US_ECHO, HIGH, 30000UL); // timeout ~5m
  if (dur == 0) return -1.0; // OOR
  return dur / 58.2; // cm
}

bool canPing() {
  unsigned long now = millis();
  if (now - lastPingMs >= US_PING_MIN_MS) {
    lastPingMs = now;
    return true;
  }
  return false;
}

void setLeds(bool g, bool y, bool r) {
  digitalWrite(LED_GREEN, g ? HIGH : LOW);
  digitalWrite(LED_YELLOW, y ? HIGH : LOW);
  digitalWrite(LED_RED, r ? HIGH : LOW);
}

void printUID() {
  Serial.print("UID:");
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) Serial.print("0");
    Serial.print(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) Serial.print(":");
  }
  Serial.println();
}

void setup() {
  Serial.begin(9600);
  // RFID + SPI
  SPI.begin();
  rfid.PCD_Init();
  // DHT
  dht.begin();
  // LEDs
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  setLeds(false, false, false);
  // Ultrasonic
  pinMode(US_TRIG, OUTPUT);
  pinMode(US_ECHO, INPUT);

  Serial.println("System ready (RFID + DHT11 + Ultrasonic + LEDs)");
  // Basic pin map and system info
  Serial.print("[SYS] RFID SS="); Serial.print(RFID_SS);
  Serial.print(" RST="); Serial.println(RFID_RST);
  Serial.print("[SYS] LEDs R/Y/G="); Serial.print(LED_RED);
  Serial.print("/"); Serial.print(LED_YELLOW);
  Serial.print("/"); Serial.println(LED_GREEN);
  Serial.print("[SYS] DHT PIN="); Serial.println(DHTPIN);
  Serial.print("[SYS] US TRIG/ECHO="); Serial.print(US_TRIG);
  Serial.print("/"); Serial.println(US_ECHO);
  Serial.print("[SYS] US STREAM ivl ms="); Serial.println(US_STREAM_INTERVAL_MS);
}

void handleReadAllEnv() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) {
    Serial.println("Error: DHT read failed");
    return;
  }
  Serial.print("Humidity: ");
  Serial.print(h);
  Serial.print(" %\t");
  Serial.print("Temperature: ");
  Serial.print(t);
  Serial.println(" °C");
}

void handleHumidity() {
  float h = dht.readHumidity();
  if (isnan(h)) { Serial.println("Error: Humidity read failed"); return; }
  Serial.print("Humidity: "); Serial.print(h); Serial.println(" %");
}

void handleTemperature() {
  float t = dht.readTemperature();
  if (isnan(t)) { Serial.println("Error: Temperature read failed"); return; }
  Serial.print("Temperature: "); Serial.print(t); Serial.println(" °C");
}

void handleUltrasonicSingle() {
  float d = readDistanceCM();
  if (d < 0) {
    Serial.println("Distance: -1 cm");
  } else {
    Serial.print("Distance: "); Serial.print(d, 2); Serial.println(" cm");
  }
}

void loop() {
  // 1) Handle incoming serial commands from Python GUI
  static String cmdBuf;
  static unsigned long lastByteMs = 0;

  // Read all available bytes into buffer
  while (Serial.available() > 0) {
    char c = Serial.read();
    lastByteMs = millis();
    // Normalize CR to newline and ignore other control chars except letters/digits
    if (c == '\r') c = '\n';
    cmdBuf += c;
  }

  auto processToken = [](const String &tokenRaw) {
    String token = tokenRaw;
    token.trim();
    if (token.length() == 0) return;
    String upper = token;
    upper.toUpperCase();

    // Single-char commands
    if (upper.length() == 1) {
      char ch = upper.charAt(0);
      switch (ch) {
        case 'G': setLeds(true, false, false); Serial.println("LED:GREEN"); break;   // GO (green)
        case 'Y': setLeds(false, true, false); Serial.println("LED:YELLOW"); break;   // CAUTION (yellow)
        case 'R':
          setLeds(false, false, true);
          handleReadAllEnv();
          // Log AFTER sending env line to avoid interfering with GUI single-line read
          Serial.println("LED:RED");
          break; // STOP + env read
        case 'C': setLeds(false, false, false); Serial.println("LED:OFF"); break;  // Clear/Off
        case 'H': handleHumidity(); Serial.println("DHT:HUMIDITY SENT"); break;
        case 'T': handleTemperature(); Serial.println("DHT:TEMP SENT"); break;
        case 'U': if (canPing()) { handleUltrasonicSingle(); Serial.println("US:SINGLE"); } break;
        case 'L':
          ultrasonicStreaming = true;
          // reset timers so first sample is immediate
          lastStreamMs = 0;
          lastPingMs = 0;
          // Emit an immediate sample so GUI shows a value right away
          handleUltrasonicSingle();
          Serial.println("US:STREAM ON");
          break; // 'l'
        case 'S': ultrasonicStreaming = false; Serial.println("US:STREAM OFF"); break;
        default: break;
      }
      return;
    }

    // Word tokens (e.g., GREEN/YELLOW/RED/OFF)
    if (upper == "GREEN") { setLeds(true, false, false); Serial.println("LED:GREEN"); }
    else if (upper == "YELLOW") { setLeds(false, true, false); Serial.println("LED:YELLOW"); }
    else if (upper == "RED") { setLeds(false, false, true); Serial.println("LED:RED"); }
    else if (upper == "OFF") { setLeds(false, false, false); Serial.println("LED:OFF"); }
    // extendable: could accept "READ" to trigger handleReadAllEnv()
  };

  // Process complete lines in buffer
  int nlIndex;
  while ((nlIndex = cmdBuf.indexOf('\n')) >= 0) {
    String line = cmdBuf.substring(0, nlIndex);
    cmdBuf.remove(0, nlIndex + 1);
    processToken(line);
  }
  // If there's a single-char token pending and no further data for a short time, process it
  if (cmdBuf.length() == 1) {
    if (millis() - lastByteMs > 20) {
      String one = cmdBuf;
      cmdBuf = "";
      processToken(one);
    }
  }

  // 2) RFID card detection (non-blocking)
  if (rfid.PICC_IsNewCardPresent()) {
    if (rfid.PICC_ReadCardSerial()) {
      // Briefly show yellow to indicate tag detected (doesn't override manual state long-term)
      setLeds(digitalRead(LED_GREEN), true, digitalRead(LED_RED));
      printUID();
      Serial.println("RFID:TAG DETECTED");
      delay(100); // small visual feedback
      setLeds(digitalRead(LED_GREEN), false, digitalRead(LED_RED));
      rfid.PICC_HaltA();
    }
  }

  // 3) Ultrasonic streaming output
  if (ultrasonicStreaming) {
    unsigned long now = millis();
    if (now - lastStreamMs >= US_STREAM_INTERVAL_MS) {
      lastStreamMs = now;
      if (canPing()) {
        handleUltrasonicSingle();
      }
    }
  }

  delay(10);
}

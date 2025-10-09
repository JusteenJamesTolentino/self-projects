// Multi-sensor sketch: DHT11 + Ultrasonic (HC-SR04) support
#include "DHT.h"

#define DHTPIN 7         // DHT11 data pin
#define DHTTYPE DHT11

// Ultrasonic pins (adjust to your wiring)
#define ULTRASONIC_TRIG 8
#define ULTRASONIC_ECHO 9

DHT dht(DHTPIN, DHTTYPE);

unsigned long lastPing = 0;
float lastDistance = -1.0;

float readDistanceCM() {
  // Trigger a pulse
  digitalWrite(ULTRASONIC_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG, LOW);
  // Read echo pulse width
  unsigned long duration = pulseIn(ULTRASONIC_ECHO, HIGH, 30000UL); // 30ms timeout ~5m
  if (duration == 0) {
    return -1.0; // timeout / out of range
  }
  // Speed of sound ~343 m/s => 29.1 us per cm (round trip ~58.2)
  float distanceCm = duration / 58.2; // approximate
  return distanceCm;
}

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(ULTRASONIC_TRIG, OUTPUT);
  pinMode(ULTRASONIC_ECHO, INPUT);
  Serial.println("Multi-sensor (DHT11 + Ultrasonic) ready");
}

void handleReadAll() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Error: DHT read failed");
    return;
  }
  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.print(" %\t");
  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.println(" °C");
}

void handleHumidity() {
  float humidity = dht.readHumidity();
  if (isnan(humidity)) {
    Serial.println("Error: Humidity read failed");
    return;
  }
  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");
}

void handleTemperature() {
  float temperature = dht.readTemperature();
  if (isnan(temperature)) {
    Serial.println("Error: Temperature read failed");
    return;
  }
  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.println(" °C");
}

void handleUltrasonicSingle() {
  float d = readDistanceCM();
  if (d < 0) {
    Serial.println("Distance: -1 cm");
  } else {
    Serial.print("Distance: ");
    Serial.print(d, 2);
    Serial.println(" cm");
  }
}

// Optional simple throttling if user spams 'U'
bool canPing() {
  unsigned long now = millis();
  if (now - lastPing >= 60) { // 60ms min interval
    lastPing = now;
    return true;
  }
  return false;
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    switch (command) {
      case 'R': // read both
        handleReadAll();
        break;
      case 'H':
        handleHumidity();
        break;
      case 'T':
        handleTemperature();
        break;
      case 'U': // ultrasonic one-shot
        if (canPing()) {
          handleUltrasonicSingle();
        }
        break;
      default:
        // ignore unknown commands
        break;
    }
  }
  delay(25); // small loop delay to reduce noise
}

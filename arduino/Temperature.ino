#include "DHT.h"

#define DHTPIN 7       
#define DHTTYPE DHT11 

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();
  Serial.println("DHT11 test started!");
}

void loop() {

  if (Serial.available() > 0) {
    char command = Serial.read(); 

    if (command == 'R') {  
      float humidity = dht.readHumidity();
      float temperature = dht.readTemperature();

      if (isnan(humidity) || isnan(temperature)) {
        Serial.println("Error: Failed to read from DHT sensor!");
        return;
      }

    
      Serial.print("Humidity: ");
      Serial.print(humidity);
      Serial.print(" %\t");
      Serial.print("Temperature: ");
      Serial.print(temperature);
      Serial.println(" °C");
    }
    else if (command == 'H') {
      float humidity = dht.readHumidity();
      Serial.print("Humidity: ");
      Serial.print(humidity);
      Serial.println(" %");
    }
    else if (command == 'T') {
      float temperature = dht.readTemperature();
      Serial.print("Temperature: ");
      Serial.print(temperature);
      Serial.println(" °C");
    }
  }

  delay(200);
}

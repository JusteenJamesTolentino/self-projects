void setup() {
    Serial.begin(115200);
}

void loop() {
    if (Serial.available() > 0) {
        String incomingData = Serial.readStringUntil('\n');
        processIncomingData(incomingData);
    }
}

void processIncomingData(String data) {
    Serial.print("Received: ");
    Serial.println(data);
}
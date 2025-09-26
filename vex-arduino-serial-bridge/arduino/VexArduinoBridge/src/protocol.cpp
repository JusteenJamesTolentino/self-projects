void setup() {
    Serial.begin(115200); // Initialize serial communication at 115200 baud rate
}

void loop() {
    if (Serial.available() > 0) {
        // Read incoming data from the VEX Robot
        String incomingData = Serial.readStringUntil('\n');
        processIncomingData(incomingData);
    }
}

void processIncomingData(String data) {
    // Process the incoming data and respond accordingly
    // Example: Echo the received data back
    Serial.println("Received: " + data);
}
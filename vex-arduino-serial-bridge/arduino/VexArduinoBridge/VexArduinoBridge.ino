void setup() {
    Serial.begin(115200); // Initialize serial communication at 115200 baud rate
}

void loop() {
    if (Serial.available() > 0) {
        String incomingData = Serial.readStringUntil('\n'); // Read incoming data until newline
        processIncomingData(incomingData); // Process the received data
    }
}

void processIncomingData(String data) {
    // Placeholder for processing incoming data from VEX Robot
    // Implement your protocol handling logic here
    Serial.print("Received: ");
    Serial.println(data); // Echo the received data back for debugging
}
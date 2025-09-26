#include "pros/adi.hpp"
#include "pros/serial.hpp"
#include "main.h"
#include "protocol.h"

pros::Serial serial_port("/dev/serial1", 115200); // Adjust the port as necessary

void setup() {
    serial_port.write("VEX Robot Initialized\n");
}

void loop() {
    if (serial_port.available()) {
        char incomingByte = serial_port.read();
        // Process incoming data
        handleIncomingData(incomingByte);
    }

    // Example of sending data to Arduino
    sendDataToArduino("Hello Arduino");
    pros::delay(100); // Delay to prevent flooding the serial port
}

void handleIncomingData(char data) {
    // Implement your data handling logic here
}

void sendDataToArduino(const char* message) {
    serial_port.write(message);
}
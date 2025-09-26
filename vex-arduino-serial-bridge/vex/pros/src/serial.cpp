#include "main.h"
#include "pros/adi.hpp"
#include "pros/serial.hpp"
#include "protocol.h"

pros::Serial serial_port("/dev/serial1", 115200); // Adjust the port and baud rate as necessary

void initialize_serial() {
    serial_port.write("VEX Robot Initialized\n");
}

void send_data(const std::string& data) {
    serial_port.write(data.c_str(), data.size());
}

std::string receive_data() {
    char buffer[256];
    int bytes_read = serial_port.read(buffer, sizeof(buffer) - 1);
    if (bytes_read > 0) {
        buffer[bytes_read] = '\0'; // Null-terminate the string
        return std::string(buffer);
    }
    return "";
}

void process_serial_communication() {
    std::string received_message = receive_data();
    if (!received_message.empty()) {
        // Process the received message
        send_data("Message received: " + received_message);
    }
}
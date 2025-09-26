#ifndef PROTOCOL_H
#define PROTOCOL_H

// Define message types
#define MESSAGE_TYPE_COMMAND 0x01
#define MESSAGE_TYPE_STATUS  0x02

// Define command constants
#define COMMAND_START       0x01
#define COMMAND_STOP        0x02
#define COMMAND_SET_SPEED   0x03

// Define status constants
#define STATUS_OK          0x00
#define STATUS_ERROR       0x01

// Function prototypes
void sendCommand(uint8_t command, uint8_t value);
void receiveMessage();
void processMessage(uint8_t* message, size_t length);

#endif // PROTOCOL_H
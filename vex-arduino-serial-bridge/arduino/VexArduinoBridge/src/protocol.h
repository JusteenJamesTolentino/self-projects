#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>
#include <stddef.h>

#define MESSAGE_TYPE_COMMAND 0x01
#define MESSAGE_TYPE_STATUS  0x02

#define COMMAND_START       0x01
#define COMMAND_STOP        0x02
#define COMMAND_SET_SPEED   0x03

#define STATUS_OK          0x00
#define STATUS_ERROR       0x01

void sendCommand(uint8_t command, uint8_t value);
void receiveMessage();
void processMessage(uint8_t* message, size_t length);

#endif
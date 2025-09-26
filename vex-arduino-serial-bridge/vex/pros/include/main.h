#ifndef MAIN_H
#define MAIN_H

#include "pros/adi.hpp"
#include "pros/adi.hpp"
#include "pros/serial.hpp"

// Function declarations
void initialize();
void autonomous();
void opcontrol();

// Constants
const int SERIAL_PORT = 1; // Adjust based on your setup
const int BAUD_RATE = 115200;

#endif // MAIN_H
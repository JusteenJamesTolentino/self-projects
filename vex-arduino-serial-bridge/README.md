# VEX and Arduino Serial Bridge

This project establishes a communication bridge between a VEX Robot and an Arduino using serial communication. The setup allows for data exchange between the two devices, enabling enhanced functionality and control.

## Project Structure

```
vex-arduino-serial-bridge
├── python
│   ├── VexMain.py          # Main entry point for the Python application
│   ├── serial_client.py     # Functions for serial communication
│   └── requirements.txt     # Python dependencies
├── arduino
│   └── VexArduinoBridge
│       ├── VexArduinoBridge.ino  # Main Arduino sketch
│       └── src
│           ├── protocol.h         # Communication protocol header
│           └── protocol.cpp       # Protocol implementation
├── vex
│   └── pros
│       ├── include
│       │   ├── main.h            # VEX main header
│       │   └── protocol.h        # VEX communication protocol header
│       ├── src
│       │   ├── main.cpp          # VEX main application logic
│       │   └── serial.cpp        # VEX serial communication implementation
│       ├── Makefile              # Build instructions for VEX code
│       └── project.pros          # PROS project configuration
├── .gitignore                   # Files to ignore in version control
└── README.md                    # Project documentation
```

## Setup Instructions

1. **Python Environment**:
   - Ensure you have Python installed on your system.
   - Install the required Python packages by running:
     ```
     pip install -r python/requirements.txt
     ```

2. **Arduino Setup**:
   - Open the `VexArduinoBridge.ino` file in the Arduino IDE.
   - Upload the sketch to your Arduino board.

3. **VEX Robot Setup**:
   - Open the VEX project in the PROS IDE.
   - Compile and upload the VEX code to your robot.

4. **Running the Python Application**:
   - Connect the Arduino to your computer via USB.
   - Run the Python application using:
     ```
     python python/VexMain.py
     ```

## Usage Guidelines

- The Python application will establish a serial connection with the Arduino.
- Use the defined communication protocols in `protocol.h` files for sending and receiving messages.
- Ensure that the baud rate in both the Arduino and Python code matches for successful communication.

## Contributing

Feel free to contribute to this project by submitting issues or pull requests. Your feedback and improvements are welcome!
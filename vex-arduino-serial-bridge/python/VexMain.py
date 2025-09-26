import serial
import time

def main():
    # Set up the serial connection to the Arduino
    arduino_port = '/dev/ttyUSB0'  # Change this to your Arduino's port
    baud_rate = 9600

    try:
        with serial.Serial(arduino_port, baud_rate, timeout=1) as ser:
            print("Connected to Arduino on port:", arduino_port)
            time.sleep(2)  # Wait for the connection to establish

            while True:
                # Example of sending data to Arduino
                message = "Hello Arduino"
                ser.write(message.encode('utf-8'))
                print("Sent:", message)

                # Example of receiving data from Arduino
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8').rstrip()
                    print("Received:", response)

                time.sleep(1)  # Adjust the delay as needed

    except serial.SerialException as e:
        print("Error connecting to Arduino:", e)

if __name__ == "__main__":
    main()
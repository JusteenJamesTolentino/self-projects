import serial
import time

def main():
    arduino_port = '/dev/ttyUSB0'
    baud_rate = 9600

    try:
        with serial.Serial(arduino_port, baud_rate, timeout=1) as ser:
            print("Connected to Arduino on port:", arduino_port)
            time.sleep(2)

            while True:
                message = "Hello Arduino"
                ser.write(message.encode('utf-8'))
                print("Sent:", message)

                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8').rstrip()
                    print("Received:", response)

                time.sleep(1)

    except serial.SerialException as e:
        print("Error connecting to Arduino:", e)

if __name__ == "__main__":
    main()
def initialize_serial(port, baudrate=9600):
    import serial
    try:
        ser = serial.Serial(port, baudrate)
        return ser
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return None

def send_data(ser, data):
    if ser and ser.is_open:
        try:
            if not data.endswith("\n"):
                data += "\n"
            ser.write(data.encode())
        except Exception as e:
            print(f"Error sending data: {e}")

def receive_data(ser):
    if ser and ser.is_open:
        try:
            if ser.in_waiting > 0:
                return ser.readline().decode().strip()
        except Exception as e:
            print(f"Error receiving data: {e}")
    return None

def close_serial(ser):
    if ser:
        ser.close()
from app.controller import AppController

CONFIG = {
    "serial": {
        "port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "timeout": 1
    },
    "durations": {
        "go": 15,
        "caution": 5,
        "stop": 15
    }
}


def main():
    app = AppController(config=CONFIG)
    app.start()


if __name__ == "__main__":
    main()
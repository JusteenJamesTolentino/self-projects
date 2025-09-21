from app.controller import AppController

# Central configuration for the application. Change values here to affect
# serial connection parameters and traffic LED durations.
CONFIG = {
    "serial": {
        "port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "timeout": 1
    },
    "durations": {
        # durations in seconds
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
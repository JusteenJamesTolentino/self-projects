CC = g++
CFLAGS = -Iinclude -std=c++11
SRC = src/main.cpp src/serial.cpp
OBJ = $(SRC:.cpp=.o)
TARGET = vex_robot

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) -o $@ $^

%.o: %.cpp
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(TARGET)
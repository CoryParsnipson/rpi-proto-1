#include <HID-Project.h>
#include <HID-Settings.h>

const int REFRESH_INTERVAL = 1000;
const bool ENABLE_SERIAL = true;

const int NUM_ROWS = 4;
const int NUM_COLS = 4;

const int ROW_PINS[NUM_ROWS] = { 7, 8, 10, 16 };
const int COL_PINS[NUM_COLS] = { 2, 4, 14, 15 };

const int pinLXAxis = A1;
const int pinLYAxis = A0;

void setup() {
  digitalWrite(pinLXAxis, LOW);
  digitalWrite(pinLYAxis, LOW);
    
  reset();
  
  if (ENABLE_SERIAL) {
    Serial.begin(9600);
    Serial.println("Hello World!");  
  }

  Gamepad.begin();
}

void loop() {
  bool is_pressed = false;

  for (int c = 0; c < NUM_COLS; ++c) {
    byte col = COL_PINS[c];
    pinMode(col, OUTPUT);
    digitalWrite(col, LOW);
    
    for (int r = 0; r < NUM_ROWS; ++r) {
      byte row = ROW_PINS[r];
      byte current_button = c * NUM_COLS + r + 1;
      
      pinMode(row, INPUT_PULLUP);
      bool button_state = !digitalRead(row);
      pinMode(row, OUTPUT);
      digitalWrite(row, LOW); // ground potential before disconnecting because of the MOSFET attached
      pinMode(row, INPUT);
      
      if (button_state) {
        Gamepad.press(current_button);
        is_pressed = true;
      } else {
        Gamepad.release(current_button);
      }
    }

    pinMode(col, INPUT);
  }

  // analog axes
  int readX = analogRead(pinLXAxis); // store in temporary variables to use in constrain()
  int readY = analogRead(pinLYAxis);

  const int XMIN = 200, XMAX = 880;
  const int YMIN = 125, YMAX = 835;

  // clamp values to observed joystick values
  readX = constrain(readX, XMIN, XMAX);
  readY = constrain(readY, YMIN, YMAX);
    
  Gamepad.xAxis(map(readX, XMIN, XMAX, -32767, 32767)); 
  Gamepad.yAxis(map(readY, YMIN, YMAX, 32767, -32767)); // flip Y axis because I have it oriented upside-down

  Gamepad.write();

  delayMicroseconds(REFRESH_INTERVAL);
}

void reset() {
  for (int r = 0; r < NUM_ROWS; ++r) {
    pinMode(ROW_PINS[r], INPUT);
  }
  
  for (int c = 0; c < NUM_COLS; ++c) {
    pinMode(COL_PINS[c], INPUT_PULLUP);
  }
}

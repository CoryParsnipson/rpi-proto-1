#include <HID-Project.h>
#include <HID-Settings.h>

const int REFRESH_INTERVAL = 1000;
const bool ENABLE_SERIAL = false;
char* msg = new char[80];

const int NUM_ROWS = 4;
const int NUM_COLS = 4;

const int ROW_PINS[NUM_ROWS] = { 7, 8, 10, 16 };
const int COL_PINS[NUM_COLS] = { 3, 4, 14, 15 };

const int LEFT_THUMBSTICK_BUTTON_PIN = 9;
const int RIGHT_THUMBSTICK_BUTTON_PIN = 2;

// These calibrated values are different per individual thumbstick and need to be obtained
// by reading the value of the analog pins, bringing the thumbstick to the max/min of each axis
// and then using a number that is ~10 smaller/larger than what is observed.
const int R_XMIN_CALIBRATED = 85;
const int R_XMAX_CALIBRATED = 850;
const int R_YMIN_CALIBRATED = 160;
const int R_YMAX_CALIBRATED = 840;

const int L_XMIN_CALIBRATED = 170;
const int L_XMAX_CALIBRATED = 890;
const int L_YMIN_CALIBRATED = 100;
const int L_YMAX_CALIBRATED = 840;

const int pinLXAxis = A0;
const int pinLYAxis = A1;
const int pinRXAxis = A3;
const int pinRYAxis = A2;


void printAnalog(const long& packedVal);
unsigned long readAnalog(int xPin, int yPin, const int XMIN, const int XMAX, const int YMIN, const int YMAX, bool returnRaw = false);

void setup() {
  digitalWrite(pinLXAxis, LOW);
  digitalWrite(pinLYAxis, LOW);
  digitalWrite(pinRXAxis, LOW);
  digitalWrite(pinRYAxis, LOW);

  // thumbstick buttons are not part of key matrix
  pinMode(LEFT_THUMBSTICK_BUTTON_PIN, INPUT_PULLUP);
  pinMode(RIGHT_THUMBSTICK_BUTTON_PIN, INPUT_PULLUP);
    
  reset();
  
  if (ENABLE_SERIAL) {
    Serial.begin(115200);
    while (!Serial) {
      ; // wait for serial port to connect. Needed for native USB
    }
    
    Serial.println("Serial monitor enabled");
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
      digitalWrite(row, LOW); // discharge any potential floating nodes
      pinMode(row, INPUT);

      if (button_state) {
        Gamepad.press(current_button);
        is_pressed = true;

        if (ENABLE_SERIAL) {
          sprintf(msg, "Row %i, Col %i detected\n", row, col);
          Serial.print(msg);
        }
      } else {
        Gamepad.release(current_button);
      }
    }

    pinMode(col, INPUT);
  }

  // left thumbstick button polling
  if (!digitalRead(LEFT_THUMBSTICK_BUTTON_PIN)) {
    Gamepad.press(NUM_ROWS * NUM_COLS + 1);
  } else {
    Gamepad.release(NUM_ROWS * NUM_COLS + 1);
  }

  // right thumbstick button polling
  if (!digitalRead(RIGHT_THUMBSTICK_BUTTON_PIN)) {
    Gamepad.press(NUM_ROWS * NUM_COLS + 2);
  } else {
    Gamepad.release(NUM_ROWS * NUM_COLS + 2);
  } 

  unsigned long LStickVal = readAnalog(
    pinLXAxis,
    pinLYAxis,
    L_XMIN_CALIBRATED,
    L_XMAX_CALIBRATED,
    L_YMIN_CALIBRATED,
    L_YMAX_CALIBRATED
  );
  Gamepad.xAxis(LStickVal >> (sizeof(int) * 8));
  Gamepad.yAxis(LStickVal & 0xFFFFL);
  
  unsigned long RStickVal = readAnalog(
    pinRXAxis,
    pinRYAxis,
    R_XMIN_CALIBRATED,
    R_XMAX_CALIBRATED,
    R_YMIN_CALIBRATED,
    R_YMAX_CALIBRATED
  );
  Gamepad.rxAxis(RStickVal >> (sizeof(int) * 8));
  Gamepad.ryAxis(RStickVal & 0xFFFFL);

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

void printAnalog(const long& packedVal) {
  if (!ENABLE_SERIAL) {
    return;
  }

  int tx = packedVal >> (sizeof(int) * 8);
  int ty = packedVal & 0xFFFFL;
  sprintf(msg, "Raw: %lx, x-axis: %d, y-axis: %d", packedVal, tx, ty);
  Serial.println(msg);
}

unsigned long readAnalog(int xPin, int yPin, const int XMIN, const int XMAX, const int YMIN, const int YMAX, bool returnRaw = false) {
  int readX = analogRead(xPin); // store in temporary variables to use in constrain()
  int readY = analogRead(yPin); 
  
  if (!returnRaw) {
    // clamp values to observed joystick values
    readX = constrain(readX, XMIN, XMAX);
    readY = constrain(readY, YMIN, YMAX);
  
    readX = map(readX, XMIN, XMAX, -32767, 32767);
    readY = map(readY, YMIN, YMAX, 32767, -32767); // flip Y axis because of the physical orientation of thumbstick  
  }

  unsigned long packed = readX;
  packed = (packed << (sizeof(int) * 8)) | (0xFFFF & readY);
  return packed;
}

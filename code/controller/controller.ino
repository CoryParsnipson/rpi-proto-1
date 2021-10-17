#include <HID-Project.h>
#include <HID-Settings.h>

#define MSG_LEN 80

#undef ENABLE_SERIAL // change to #define ENABLE_SERIAL if you want serial turned on

#ifdef ENABLE_SERIAL
  #define PRINT_SERIAL(...) \
    snprintf(msg, MSG_LEN - 1, __VA_ARGS__); /* snprintf to avoid accidental buffer overflow */ \
    Serial.println(msg);
#else
  #define PRINT_SERIAL(...) \
    do {} while(0)
#endif

#ifdef ENABLE_SERIAL
  #define INIT_SERIAL(baudRate) \
    Serial.begin(baudRate); \
    while (!Serial) { \
      ; /* wait for serial port to connect. Needed for native USB */ \
    } \
    PRINT_SERIAL("Serial monitor enabled")
#else
  #define INIT_SERIAL(baudRate) \
    do {} while(0)
#endif

const int refreshInterval = 1000;

char* msg = new char[MSG_LEN];

const int numRows = 4;
const int numCols = 4;

const int rowPins[numRows] = { 7, 8, 10, 16 };
const int colPins[numCols] = { 3, 4, 14, 15 };

const int leftThumbstickButtonPin = 9;
const int rightThumbstickButtonPin = 2;

// These calibrated values are different per individual thumbstick and need to be obtained
// by reading the value of the analog pins, bringing the thumbstick to the max/min of each axis
// and then using a number that is ~10 smaller/larger than what is observed.
const int rXMinCalibrated = 85;
const int rXMaxCalibrated = 850;
const int rYMinCalibrated = 160;
const int rYMaxCalibrated = 840;

const int lXMinCalibrated = 170;
const int lXMaxCalibrated = 890;
const int lYMinCalibrated = 100;
const int lYMaxCalibrated = 840;

const int pinLXAxis = A0;
const int pinLYAxis = A1;
const int pinRXAxis = A3;
const int pinRYAxis = A2;

void reset();
inline void printAnalog(const int16_t xval, const int16_t yval);
int16_t readAxis(int pin, const int min, const int max, boolean returnRaw = false);

void setup() {
  digitalWrite(pinLXAxis, LOW);
  digitalWrite(pinLYAxis, LOW);
  digitalWrite(pinRXAxis, LOW);
  digitalWrite(pinRYAxis, LOW);

  // thumbstick buttons are not part of key matrix
  pinMode(leftThumbstickButtonPin, INPUT_PULLUP);
  pinMode(rightThumbstickButtonPin, INPUT_PULLUP);
    
  reset();

  INIT_SERIAL(115200);

  Gamepad.begin();
}

void loop() {
  static unsigned long now = 0, nextUpdate = 0;
  now = micros();

  if (nextUpdate < now) {
    // TODO: maybe sleep would let us squeeze out extra battery life here
    nextUpdate = now + refreshInterval; 

    for (int c = 0; c < numCols; ++c) {
      byte col = colPins[c];
      pinMode(col, OUTPUT);
      digitalWrite(col, LOW);
  
      for (int r = 0; r < numRows; ++r) {
        byte row = rowPins[r];
        byte current_button = c * numCols + r + 1;

        pinMode(row, INPUT_PULLUP);
        bool button_state = !digitalRead(row);
        pinMode(row, INPUT); // set pin to hi-z
  
        if (button_state) {
          Gamepad.press(current_button);
          PRINT_SERIAL("Row %i, Col %i detected", row, col);
        } else {
          Gamepad.release(current_button);
        }
      }
      pinMode(col, INPUT);
    }

    // left thumbstick button polling
    if (!digitalRead(leftThumbstickButtonPin)) {
      Gamepad.press(numRows * numCols + 1);
    } else {
      Gamepad.release(numRows * numCols + 1);
    }

    // right thumbstick button polling
    if (!digitalRead(rightThumbstickButtonPin)) {
      Gamepad.press(numRows * numCols + 2);
    } else {
      Gamepad.release(numRows * numCols + 2);
    } 

    Gamepad.xAxis(readAxis(pinLXAxis, lXMinCalibrated, lXMaxCalibrated));
    Gamepad.yAxis(-1 * readAxis(pinLYAxis, lYMinCalibrated, lYMaxCalibrated)); // invert y axis
    
    Gamepad.rxAxis(readAxis(pinRXAxis, rXMinCalibrated, rXMaxCalibrated));
    Gamepad.ryAxis(-1 * readAxis(pinRYAxis, rYMinCalibrated, rYMaxCalibrated)); // invert y axis

    Gamepad.write();
  }
}

void reset() {
  for (int r = 0; r < numRows; ++r) {
    pinMode(rowPins[r], INPUT);
  }
  
  for (int c = 0; c < numCols; ++c) {
    pinMode(colPins[c], INPUT_PULLUP);
  }
}

void printAnalog(int16_t xval, int16_t yval) {
  PRINT_SERIAL("x-axis: %d, y-axis: %d", xval, yval);
}

int16_t readAxis(int pin, const int min, const int max, bool returnRaw) {
  uint16_t read = analogRead(pin);
  if (returnRaw) {
    return read;
  }

  return map(constrain(read, min, max), min, max, -32767, 32767);
}

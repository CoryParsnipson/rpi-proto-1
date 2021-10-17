#include <HID-Project.h>
#include <HID-Settings.h>

const int REFRESH_INTERVAL = 1000;
// change to #define ENABLE_SERIAL if you want serial turned on
#undef ENABLE_SERIAL

#define MSG_LEN 80
char* msg = new char[MSG_LEN];

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


inline void printAnalog(const int16_t, const int16_t);
int16_t readAxis(int, const int, const int, boolean);

void setup() {
  digitalWrite(pinLXAxis, LOW);
  digitalWrite(pinLYAxis, LOW);
  digitalWrite(pinRXAxis, LOW);
  digitalWrite(pinRYAxis, LOW);

  // thumbstick buttons are not part of key matrix
  pinMode(LEFT_THUMBSTICK_BUTTON_PIN, INPUT_PULLUP);
  pinMode(RIGHT_THUMBSTICK_BUTTON_PIN, INPUT_PULLUP);
    
  reset();
  
#ifdef ENABLE_SERIAL
    Serial.begin(115200);
    while (!Serial) {
      ; // wait for serial port to connect. Needed for native USB
    }
    
    Serial.println("Serial monitor enabled");
#endif

  Gamepad.begin();
}

void loop() {
  static unsigned long now=0,next_update=0;
  now=micros();
  if (next_update < now) { // time to poll our buttons again!
	next_update=now+REFRESH_INTERVAL;  // no matter how long it takes us to do all the crap here, our next poll will be ASAP after the refresh time expires.
	for (int c = 0; c < NUM_COLS; ++c) {
		byte col = COL_PINS[c];
		pinMode(col, OUTPUT);
		digitalWrite(col, LOW);

		for (int r = 0; r < NUM_ROWS; ++r) {
		  byte row = ROW_PINS[r];
		  byte current_button = c * NUM_COLS + r + 1;
		  
		  pinMode(row, INPUT_PULLUP);
		  bool button_state = !digitalRead(row);

		  pinMode(row, INPUT);    // set pin to hi-z

		  if (button_state) {
			Gamepad.press(current_button);

#ifdef ENABLE_SERIAL
			  snprintf(msg, MSG_LEN-1, "Row %i, Col %i detected\n", row, col);  // snprintf to avoid buffer overflow in case something wiggy happens
			  Serial.print(msg);
#endif
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

	Gamepad.xAxis(readAxis(pinLXAxis,L_XMIN_CALIBRATED,L_XMAX_CALIBRATED);
	Gamepad.yAxis(-readAxis(pinLYAxis,L_YMIN_CALIBRATED,L_YMAX_CALIBRATED);

	Gamepad.rxAxis(readAxis(pinRXAxis,R_XMIN_CALIBRATED,R_XMAX_CALIBRATED);
	Gamepad.ryAxis(-readAxis(pinRYAxis,R_YMIN_CALIBRATED,R_YMAX_CALIBRATED);

	Gamepad.write();
	}
}

void reset() {
  for (int r = 0; r < NUM_ROWS; ++r) {
    pinMode(ROW_PINS[r], INPUT);
  }
  
  for (int c = 0; c < NUM_COLS; ++c) {
    pinMode(COL_PINS[c], INPUT_PULLUP);
  }
}

#ifdef ENABLE_SERIAL
void printAnalog(int16_t xval, int16_t yval) {

  snprintf(msg, MSG_LEN-1, "x-axis: %d, y-axis: %d", xval, yval);
  Serial.println(msg);
}
#else
inline void printAnalog(const int16_t xval, const int16_t yval) {}  // shouldn't need this at all, because all printAnalog() should be wrapped; just in case.
#endif

int16_t readAxis(int pin, const int min, const int max, bool returnRaw=false) {
  int16_t ret=0;
  uint16_t read=0;
  
  read=analogRead(pin);
  if(returnRaw)
	return read;

  read=constrain(read,min,max);
  ret=map(read,min,max,-32767,32767);
  return ret;
}

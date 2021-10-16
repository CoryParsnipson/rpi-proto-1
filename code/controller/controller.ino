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


void printAnalog(const long& packedVal);
uint16_t readAnalog(int pin, const int MIN, const int MAX, bool returnRaw = false);

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
  // bool is_pressed = false;  // unused variable?
  static unsigned long now=0,next_update=0;
  now=micros();
  if (next_update < now+now+REFRESH_INTERVAL) { // time to poll our buttons again!
	next_update=now+REFRESH_INTERVAL;  // no matter how long it takes us to do all the crap here, our next poll will be ASAP after the refresh time expires.
	for (int c = 0; c < NUM_COLS; ++c) {
		byte col = COL_PINS[c];
		pinMode(col, OUTPUT);
		digitalWrite(col, LOW);
		//delayMicroseconds(0);  // perhaps needed to wait for the pin to settle.

		for (int r = 0; r < NUM_ROWS; ++r) {
		  byte row = ROW_PINS[r];
		  byte current_button = c * NUM_COLS + r + 1;
		  
		  pinMode(row, INPUT_PULLUP);
  		  //delayMicroseconds(0);  // perhaps needed to wait for the pin to settle.
		  bool button_state = !digitalRead(row);

		  pinMode(row, INPUT);    // disable the pullup resistor
		  pinMode(row, OUTPUT);   // set pin to output
		  digitalWrite(row, LOW); // discharge any potential floating nodes
		  pinMode(row, INPUT);    // set pin to hi-z

		  if (button_state) {
			Gamepad.press(current_button);
			// is_pressed = true; // unused variable?

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

	Gamepad.xAxis(readAnalog(pinLXAxis,L_XMIN_CALIBRATED,L_XMAX_CALIBRATED);
	Gamepad.yAxis(-readAnalog(pinLYAxis,L_YMIN_CALIBRATED,L_YMAX_CALIBRATED);

	Gamepad.rxAxis(readAnalog(pinRXAxis,R_XMIN_CALIBRATED,R_XMAX_CALIBRATED);
	Gamepad.ryAxis(-readAnalog(pinRYAxis,R_YMIN_CALIBRATED,R_YMAX_CALIBRATED);

	Gamepad.write();
	}

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

#ifdef ENABLE_SERIAL
void printAnalog(int16_t xval, int16_t yval) {

  snprintf(msg, MSG_LEN-1, "x-axis: %d, y-axis: %d", xval, yval);
  Serial.println(msg);
}
#else
inline void printAnalog(const long& packedVal) {}
#endif

int16_t readAnalog(int pin, const int MIN, const int MAX, bool returnRaw=false) {
  int16_t ret=0;
  uint16_t read=0;
  
  read=analogRead(pin);
  
  if(!returnRaw) {
    read=constrain(read,MIN,MAX);
    ret=map(read,MIN,MAX,-32767,32767);
  }
  else {
    ret=read;
  }
  return ret;
}

#include <chrono>
#include <iostream>
#include <thread>

#include <wiringPi.h>

const int PIN_BAT_GPOUT = 5; // GPIO5 is wiringPi pin 21 or BCM pin 5 or hardware pin 29
const int PIN_BAT_POWER = 16;

void handleSOCEvent(void) {
  std::cout << "SOC event detected!" << std::endl;
}

void handlePowerButtonEvent(void) {
  std::cout << "Power button pressed!" << std::endl;
}

int main(int argc, char **argv) {
  wiringPiSetupGpio();

  pinMode(PIN_BAT_GPOUT, INPUT);
  pinMode(PIN_BAT_POWER, INPUT);

  wiringPiISR(PIN_BAT_GPOUT, INT_EDGE_FALLING, &handleSOCEvent);
  wiringPiISR(PIN_BAT_POWER, INT_EDGE_FALLING, &handlePowerButtonEvent);

  while (1) {
    std::cout << "Main thread sleeping..." << std::endl;
    std::this_thread::sleep_for(std::chrono::milliseconds(10000));
  }

  return 0;
}

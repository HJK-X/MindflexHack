#include <SoftwareSerial.h>

SoftwareSerial BTSerial(10, 11); // RX | TX 
// Connect the HC-05 TX to Arduino pin 10 RX.
// Connect the HC-05 RX to Arduino pin 11 TX


void setup() {
  pinMode(9, OUTPUT);
  digitalWrite(9, HIGH);
  Serial.begin(9600);
  Serial.println("NL & CR + 9600 BAUD");
  Serial.println("Enter AT commands:");
  
  // HC-05 default serial speed for AT mode is 38400

  BTSerial.begin(38400);

}

void loop() {

  // Keep reading from HC-05 and send to Arduino Serial Monitor
  if (BTSerial.available())
    Serial.write(BTSerial.read());

  // Keep reading from Arduino Serial Monitor and send to HC-05
  if (Serial.available())
    BTSerial.write(Serial.read());

}

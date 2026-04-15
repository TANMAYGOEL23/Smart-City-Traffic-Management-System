// Define Pins for North-South (NS)
const int NS_RED = 2;
const int NS_YELLOW = 4;
const int NS_GREEN = 5;

// Define Pins for East-West (EW)
const int EW_RED = 18;
const int EW_YELLOW = 19;
const int EW_GREEN = 21;

// Timing Durations (in milliseconds)
const int GREEN_TIME = 5000;  // 5 seconds
const int YELLOW_TIME = 2000; // 2 seconds
const int ALL_RED_TIME = 1500; // 1.5 seconds clearance

void setup() {
  // Set all pins as OUTPUT
  pinMode(NS_RED, OUTPUT);
  pinMode(NS_YELLOW, OUTPUT);
  pinMode(NS_GREEN, OUTPUT);
  
  pinMode(EW_RED, OUTPUT);
  pinMode(EW_YELLOW, OUTPUT);
  pinMode(EW_GREEN, OUTPUT);
}

void resetLights() {
  // Turn everything off helper
  digitalWrite(NS_RED, LOW);
  digitalWrite(NS_YELLOW, LOW);
  digitalWrite(NS_GREEN, LOW);
  digitalWrite(EW_RED, LOW);
  digitalWrite(EW_YELLOW, LOW);
  digitalWrite(EW_GREEN, LOW);
}

void loop() {
  // PHASE 1: NS Green, EW Red
  resetLights();
  digitalWrite(NS_GREEN, HIGH);
  digitalWrite(EW_RED, HIGH);
  delay(GREEN_TIME);

  // PHASE 2: NS Yellow, EW Red
  resetLights();
  digitalWrite(NS_YELLOW, HIGH);
  digitalWrite(EW_RED, HIGH);
  delay(YELLOW_TIME);

  // PHASE 3: All Red (NS Red, EW Red)
  resetLights();
  digitalWrite(NS_RED, HIGH);
  digitalWrite(EW_RED, HIGH);
  delay(ALL_RED_TIME);

  // PHASE 4: NS Red, EW Green
  resetLights();
  digitalWrite(NS_RED, HIGH);
  digitalWrite(EW_GREEN, HIGH);
  delay(GREEN_TIME);

  // PHASE 5: NS Red, EW Yellow
  resetLights();
  digitalWrite(NS_RED, HIGH);
  digitalWrite(EW_YELLOW, HIGH);
  delay(YELLOW_TIME);

  // PHASE 6: All Red (NS Red, EW Red)
  resetLights();
  digitalWrite(NS_RED, HIGH);
  digitalWrite(EW_RED, HIGH);
  delay(ALL_RED_TIME);
}
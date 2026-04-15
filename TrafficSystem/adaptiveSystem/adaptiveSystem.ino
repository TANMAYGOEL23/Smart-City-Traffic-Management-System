//  TRAFFIC LIGHT PINS 
// North-South (NS)
const int NS_RED = 2;
const int NS_YELLOW = 4;
const int NS_GREEN = 5;

// East-West (EW)
const int EW_RED = 18;
const int EW_YELLOW = 19;
const int EW_GREEN = 21;

//  ULTRASONIC PINS 
// TRIG
#define TRIG_N 13
#define TRIG_E 14
#define TRIG_S 25
#define TRIG_W 26

// ECHO
#define ECHO_N 32
#define ECHO_E 33
#define ECHO_S 34
#define ECHO_W 35

//  TIMING 
const int BASE_GREEN = 3000;     // 3 sec minimum
const int FACTOR = 1000;         // +1 sec per score
const int YELLOW_TIME = 2000;
const int ALL_RED_TIME = 1500;
const int MAX_WAIT = 15000;      // max red wait

unsigned long lastNS = 0;
unsigned long lastEW = 0;

//  FUNCTIONS 

// Read distance
long readDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);
  long distance = duration * 0.034 / 2;

  if (distance == 0) return 200; // no object → far
  return distance;
}

// Convert distance → score
int getScore(long d) {
  if (d < 20) return 3;       // heavy
  else if (d < 50) return 2;  // medium
  else if (d < 100) return 1; // light
  else return 0;              // empty
}

// Reset lights
void resetLights() {
  digitalWrite(NS_RED, LOW);
  digitalWrite(NS_YELLOW, LOW);
  digitalWrite(NS_GREEN, LOW);
  digitalWrite(EW_RED, LOW);
  digitalWrite(EW_YELLOW, LOW);
  digitalWrite(EW_GREEN, LOW);
}

//  SETUP 
void setup() {
  Serial.begin(115200);

  // Traffic lights
  pinMode(NS_RED, OUTPUT);
  pinMode(NS_YELLOW, OUTPUT);
  pinMode(NS_GREEN, OUTPUT);

  pinMode(EW_RED, OUTPUT);
  pinMode(EW_YELLOW, OUTPUT);
  pinMode(EW_GREEN, OUTPUT);

  // Ultrasonic
  pinMode(TRIG_N, OUTPUT);
  pinMode(TRIG_E, OUTPUT);
  pinMode(TRIG_S, OUTPUT);
  pinMode(TRIG_W, OUTPUT);

  pinMode(ECHO_N, INPUT);
  pinMode(ECHO_E, INPUT);
  pinMode(ECHO_S, INPUT);
  pinMode(ECHO_W, INPUT);

  delay(1000);
}

//  MAIN LOOP 
void loop() {

  long dN = readDistance(TRIG_N, ECHO_N);
  long dE = readDistance(TRIG_E, ECHO_E);
  long dS = readDistance(TRIG_S, ECHO_S);
  long dW = readDistance(TRIG_W, ECHO_W);

  int NS_score = getScore(dN) + getScore(dS);
  int EW_score = getScore(dE) + getScore(dW);

  Serial.println("---- TRAFFIC STATUS ----");
  Serial.print("NS Score: "); Serial.println(NS_score);
  Serial.print("EW Score: "); Serial.println(EW_score);

  unsigned long now = millis();

  bool NS_priority = (NS_score >= EW_score);

  if (now - lastNS > MAX_WAIT) {
    NS_priority = true;
  }
  if (now - lastEW > MAX_WAIT) {
    NS_priority = false;
  }

  int greenTime;
  if (NS_priority)
    greenTime = BASE_GREEN + (NS_score * FACTOR);
  else
    greenTime = BASE_GREEN + (EW_score * FACTOR);

  Serial.print("Green Time: ");
  Serial.println(greenTime);

  //  NS GREEN 
  if (NS_priority) {
    lastNS = now;

    resetLights();
    digitalWrite(NS_GREEN, HIGH);
    digitalWrite(EW_RED, HIGH);
    delay(greenTime);

    // Yellow
    resetLights();
    digitalWrite(NS_YELLOW, HIGH);
    digitalWrite(EW_RED, HIGH);
    delay(YELLOW_TIME);
  }

  //  EW GREEN 
  else {
    lastEW = now;

    resetLights();
    digitalWrite(NS_RED, HIGH);
    digitalWrite(EW_GREEN, HIGH);
    delay(greenTime);

    // Yellow
    resetLights();
    digitalWrite(NS_RED, HIGH);
    digitalWrite(EW_YELLOW, HIGH);
    delay(YELLOW_TIME);
  }

  //  ALL RED 
  resetLights();
  digitalWrite(NS_RED, HIGH);
  digitalWrite(EW_RED, HIGH);
  delay(ALL_RED_TIME);
}
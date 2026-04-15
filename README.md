# 🚦 Adaptive Smart Traffic Light Control System

An embedded + simulation project that implements and benchmarks an **adaptive traffic signal controller** against a traditional fixed-time baseline. The system uses ultrasonic sensors to measure real-time vehicle density and dynamically adjusts green light durations — reducing wait times and preventing lane starvation.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Hardware](#hardware)
- [Getting Started](#getting-started)
- [Simulation Methods](#simulation-methods)
- [Results](#results)
- [Technologies Used](#technologies-used)
- [Applications](#applications)

---

## Overview

Traditional fixed-time traffic lights operate on a predetermined cycle regardless of actual traffic conditions. This project addresses that inefficiency by:

- **Detecting** vehicle density in four directions using HC-SR04 ultrasonic sensors
- **Dynamically allocating** green light time proportional to detected congestion
- **Preventing starvation** via a max-wait fairness algorithm that guarantees every lane gets a turn
- **Quantifying gains** through three independent Python simulation models

---

## Project Structure

```
├── Default.txt              # Fixed-time traffic controller (baseline)
├── adaptiveSystem.txt       # Adaptive traffic controller with sensor logic
├── simulation_method1.py    # Bursty traffic simulation
├── simulation_method2.py    # Multi-density traffic simulation
├── simulation_method3.py    # Full-scale Poisson simulation + analytics
└── traffic_simulation.png   # Generated performance comparison graphs
```

### File Descriptions

| File | Description |
|------|-------------|
| `Default.txt` | Standard North–South / East–West fixed cycle. Uses hard-coded green, yellow, and all-red durations. Serves as the performance baseline. |
| `adaptiveSystem.txt` | Reads ultrasonic sensor distances to estimate per-lane density. Calculates green time dynamically and enforces a maximum wait threshold to ensure fairness across all lanes. |
| `simulation_method1.py` | Simulates **bursty, irregular traffic arrivals**. Measures queue fluctuation and wait time reduction when switching from fixed to adaptive control. |
| `simulation_method2.py` | Tests three distinct traffic regimes — **Low, Mid, and Heavy** — and compares average wait time savings and queue performance in each. |
| `simulation_method3.py` | Large-scale **Poisson arrival model**. Generates detailed charts covering average wait time, throughput (cars passed), queue length, and green time per cycle. |

---

## Hardware

| Component | Role |
|-----------|------|
| ESP32 / Arduino | Main microcontroller — runs the traffic light FSM and sensor polling loop |
| HC-SR04 Ultrasonic Sensors (×4) | Measure vehicle queue distance per lane (North, South, East, West) |
| LEDs / Traffic Light Module | Visual output for red / yellow / green signals |

### Wiring (per sensor)

```
HC-SR04 VCC  →  5V
HC-SR04 GND  →  GND
HC-SR04 TRIG →  Digital Output Pin
HC-SR04 ECHO →  Digital Input Pin
```

---

## Getting Started

### Embedded Firmware

1. Open `Default.txt` or `adaptiveSystem.txt` in the Arduino IDE (rename to `.ino`).
2. Select your board: **Tools → Board → ESP32 Dev Module** (or your Arduino variant).
3. Upload to the microcontroller.

### Python Simulations

**Requirements**

```bash
pip install numpy matplotlib
```

**Run any simulation**

```bash
python simulation_method1.py   # Bursty traffic model
python simulation_method2.py   # Multi-density comparison
python simulation_method3.py   # Full-scale Poisson + graphs
```

`simulation_method3.py` will save charts to `traffic_simulation.png` automatically.

---

## Simulation Methods

### Method 1 — Bursty Traffic
Simulates real-world scenarios where vehicles arrive in irregular bursts rather than steady streams. Highlights the adaptive system's ability to absorb sudden congestion spikes that would cause excessive queuing under fixed timing.

### Method 2 — Multi-Density Comparison
Runs the fixed and adaptive controllers under three defined load levels:

| Scenario | Arrival Rate | Expected Adaptive Gain |
|----------|-------------|----------------------|
| Low | Sparse | Minimal (both systems perform similarly) |
| Mid | Moderate | Moderate wait-time reduction |
| Heavy | Dense | Significant queue and wait-time improvement |

### Method 3 — Full-Scale Poisson Simulation
Uses a Poisson process (standard model for independent vehicle arrivals) over a large number of cycles. Outputs four comparison panels:

1. Average wait time — adaptive vs. fixed
2. Total cars passed (throughput)
3. Queue length over time
4. Green time allocation per cycle

---

## Results

The adaptive controller consistently outperforms the fixed-time baseline:

-  **Lower average wait time** across all traffic densities
-  **Higher throughput** — more vehicles cleared per cycle under heavy load
-  **Shorter queues** — congestion resolved faster after arrival bursts
-  **Fairer allocation** — no lane is starved indefinitely, even under sustained imbalance

See `traffic_simulation.png` for the full visual comparison generated by Method 3.

---

## Technologies Used

- **ESP32 / Arduino** — embedded microcontroller platform
- **Embedded C++** — firmware for sensor polling and signal FSM
- **Python 3** — simulation and analysis
- **NumPy** — numerical modeling and Poisson arrival generation
- **Matplotlib** — performance graph generation
- **HC-SR04** — ultrasonic ranging sensors

---

## Applications

- 🏙️ **Smart city traffic management** — drop-in upgrade for existing intersections
- 🌐 **IoT transportation automation** — integrates with city-wide sensor networks
- 🔬 **Embedded systems research** — reference design for sensor-driven FSM control
- 📊 **Traffic engineering simulations** — benchmark framework for signal timing algorithms

---

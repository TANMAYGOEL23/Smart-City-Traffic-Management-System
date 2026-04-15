import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from collections import deque

# --- Simulation Parameters ---
SIM_DURATION = 400  # Seconds
TIME_STEP = 0.1
CAR_PASS_TIME = 1.8  # Slightly faster discharge

# Default Timings
DEFAULT_GREEN = 15.0  # Standard fixed light
DEFAULT_YELLOW = 3.0
DEFAULT_ALL_RED = 2.0

# Adaptive Logic Parameters
MIN_GREEN = 4.0  # Minimum safety green
MAX_GREEN = 45.0  # Maximum cap
EXTENSION_UNIT = 2.5  # Seconds added per car detected


class BurstyTraffic:
    """Simulates platoons of cars rather than steady flow."""

    def __init__(self, avg_lambda):
        self.avg_lambda = avg_lambda
        self.state = "IDLE"
        self.timer = 0

    def get_arrivals(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            # Switch states: either a burst or a long silence
            if self.state == "IDLE":
                self.state = "BURST"
                self.timer = np.random.uniform(5, 15)  # Burst lasts 5-15s
            else:
                self.state = "IDLE"
                self.timer = np.random.uniform(15, 40)  # Silence lasts 15-40s

        # If in burst, high probability; if idle, near zero
        rate = self.avg_lambda * 5 if self.state == "BURST" else self.avg_lambda * 0.1
        return np.random.poisson(rate * dt)


class Car:
    def __init__(self, arrival_time):
        self.arrival_time = arrival_time
        self.departure_time = None


class Intersection:
    def __init__(self, lam):
        self.ns_queue = deque()
        self.ew_queue = deque()
        self.traffic_gen = BurstyTraffic(lam)
        self.departed_cars = []
        self.time = 0.0
        self.log = []

    def update_arrivals(self, dt):
        # We simulate bursty traffic on NS, and slightly offset on EW
        for _ in range(self.traffic_gen.get_arrivals(dt)):
            self.ns_queue.append(Car(self.time))
        # EW receives a steady stream to act as the 'base' load
        if np.random.random() < (0.12 * dt):
            self.ew_queue.append(Car(self.time))

    def log_state(self):
        self.log.append((self.time, len(self.ns_queue), len(self.ew_queue)))


class DefaultSystem(Intersection):
    def run(self):
        t = 0.0
        while t < SIM_DURATION:
            # NS Green
            end = t + DEFAULT_GREEN
            while t < end:
                self.time = t
                self.update_arrivals(TIME_STEP)
                if t % CAR_PASS_TIME < TIME_STEP and self.ns_queue:
                    c = self.ns_queue.popleft()
                    c.departure_time = t
                    self.departed_cars.append(c)
                self.log_state()
                t += TIME_STEP
            t += (DEFAULT_YELLOW + DEFAULT_ALL_RED)  # Transition

            # EW Green
            end = t + DEFAULT_GREEN
            while t < end:
                self.time = t
                self.update_arrivals(TIME_STEP)
                if t % CAR_PASS_TIME < TIME_STEP and self.ew_queue:
                    c = self.ew_queue.popleft()
                    c.departure_time = t
                    self.departed_cars.append(c)
                self.log_state()
                t += TIME_STEP
            t += (DEFAULT_YELLOW + DEFAULT_ALL_RED)


class AdaptiveSystem(Intersection):
    def run(self):
        t = 0.0
        current_phase = "NS"

        while t < SIM_DURATION:
            # Determine green time based on current demand
            queue = self.ns_queue if current_phase == "NS" else self.ew_queue
            demand = len(queue)

            # Dynamic Green: Base + extension per car, within bounds
            green_duration = max(MIN_GREEN, min(MAX_GREEN, demand * EXTENSION_UNIT))

            # If no cars at all, skip or use minimum
            if demand == 0: green_duration = MIN_GREEN

            phase_end = t + green_duration
            while t < phase_end:
                self.time = t
                self.update_arrivals(TIME_STEP)

                active_q = self.ns_queue if current_phase == "NS" else self.ew_queue
                if t % CAR_PASS_TIME < TIME_STEP and active_q:
                    c = active_q.popleft()
                    c.departure_time = t
                    self.departed_cars.append(c)

                self.log_state()
                t += TIME_STEP

                # --- EARLY TERMINATION (The "Gap" Logic) ---
                # If queue is empty and we've met the minimum green, end early
                if len(active_q) == 0 and (t > (phase_end - green_duration + MIN_GREEN)):
                    break

            # Adaptive Yellow/Red (shorter if no cross-traffic)
            t += 2.0
            current_phase = "EW" if current_phase == "NS" else "NS"


# --- Analysis & Execution ---
def compare():
    lam = 0.15  # Avg arrivals/sec

    fixed = DefaultSystem(lam)
    fixed.run()

    adapt = AdaptiveSystem(lam)
    adapt.run()

    f_waits = [c.departure_time - c.arrival_time for c in fixed.departed_cars]
    a_waits = [c.departure_time - c.arrival_time for c in adapt.departed_cars]

    print(f"--- RESULTS (Bursty Traffic) ---")
    print(f"Fixed System    | Avg Wait: {np.mean(f_waits):.2f}s | Throughput: {len(f_waits)}")
    print(f"Adaptive System | Avg Wait: {np.mean(a_waits):.2f}s | Throughput: {len(a_waits)}")
    print(
        f"Improvement     | {((np.mean(f_waits) - np.mean(a_waits)) / np.mean(f_waits)) * 100:.1f}% reduction in delay")

    # Plotting
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    f_times, f_ns, f_ew = zip(*fixed.log)
    a_times, a_ns, a_ew = zip(*adapt.log)

    ax1.plot(f_times, np.array(f_ns) + np.array(f_ew), color='cyan', label='Fixed (Total Queue)')
    ax1.set_title("Fixed Timer: Queue Fluctuations")
    ax1.legend()

    ax2.plot(a_times, np.array(a_ns) + np.array(a_ew), color='orange', label='Adaptive (Total Queue)')
    ax2.set_title("Adaptive System: Queue Fluctuations")
    ax2.legend()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    compare()
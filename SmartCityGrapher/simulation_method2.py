import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from collections import deque

# --- Parameters ---
SIM_DURATION = 600  # 10 minutes
TIME_STEP = 0.1
CAR_PASS_TIME = 2.0

# Timings
DEFAULT_GREEN = 15.0
DEFAULT_TRANSITION = 5.0  # Yellow + All Red

ADAPTIVE_MIN_GREEN = 5.0
ADAPTIVE_MAX_GREEN = 45.0
GAP_THRESHOLD = 3.0

TRAFFIC_MODES = {
    "Low": {"avg_lambda": 0.05, "color": "#4CAF50"},
    "Mid": {"avg_lambda": 0.12, "color": "#FF9800"},
    "Heavy": {"avg_lambda": 0.25, "color": "#F44336"},
}


class BurstyTraffic:
    def __init__(self, avg_lambda):
        self.avg_lambda = avg_lambda
        self.state = "IDLE"
        self.timer = 0

    def get_arrivals(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            if self.state == "IDLE":
                self.state = "BURST"
                self.timer = np.random.uniform(8, 20)
            else:
                self.state = "IDLE"
                self.timer = np.random.uniform(15, 40)

        rate = self.avg_lambda * 5 if self.state == "BURST" else self.avg_lambda * 0.1
        return np.random.poisson(rate * dt)


class Car:
    def __init__(self, t): self.arrival = t


class Intersection:
    def __init__(self, lam):
        self.queues = {"NS": deque(), "EW": deque()}
        self.gens = {"NS": BurstyTraffic(lam), "EW": BurstyTraffic(lam)}
        self.departed = []
        self.log = []

    def update(self, t, dt):
        for side in ["NS", "EW"]:
            for _ in range(self.gens[side].get_arrivals(dt)):
                self.queues[side].append(Car(t))
        self.log.append((t, len(self.queues["NS"]), len(self.queues["EW"])))


# --- Simulation Engines ---
def run_fixed(lam):
    sim = Intersection(lam)
    t = 0.0
    while t < SIM_DURATION:
        for phase in ["NS", "EW"]:
            end = t + DEFAULT_GREEN
            while t < end:
                sim.update(t, TIME_STEP)
                if t % CAR_PASS_TIME < TIME_STEP and sim.queues[phase]:
                    c = sim.queues[phase].popleft()
                    sim.departed.append(t - c.arrival)
                t += TIME_STEP
            t += DEFAULT_TRANSITION
    return sim


def run_adaptive(lam):
    sim = Intersection(lam)
    t = 0.0
    phase = "NS"
    while t < SIM_DURATION:
        start_t = t
        last_car_t = t
        limit = t + ADAPTIVE_MAX_GREEN

        while t < limit:
            sim.update(t, TIME_STEP)
            if t % CAR_PASS_TIME < TIME_STEP and sim.queues[phase]:
                c = sim.queues[phase].popleft()
                sim.departed.append(t - c.arrival)
                last_car_t = t

            # GAP ACTUATION: Terminate if empty and no cars seen for GAP_THRESHOLD
            if not sim.queues[phase] and (t - last_car_t) > GAP_THRESHOLD and (t - start_t) > ADAPTIVE_MIN_GREEN:
                break
            t += TIME_STEP

        t += 2.0  # Fast adaptive transition
        phase = "EW" if phase == "NS" else "NS"
    return sim


# --- Visualization ---
results = {m: {"fixed": run_fixed(c["avg_lambda"]), "adaptive": run_adaptive(c["avg_lambda"])}
           for m, c in TRAFFIC_MODES.items()}

modes = list(TRAFFIC_MODES.keys())
f_waits = [np.mean(results[m]["fixed"].departed) for m in modes]
a_waits = [np.mean(results[m]["adaptive"].departed) for m in modes]
savings = [f - a for f, a in zip(f_waits, a_waits)]

plt.style.use('dark_background')
fig = plt.figure(figsize=(14, 10))
gs = gridspec.GridSpec(2, 2, hspace=0.3)

# Bar Comparison
ax1 = fig.add_subplot(gs[0, 0])
x = np.arange(len(modes))
ax1.bar(x - 0.2, f_waits, 0.4, label='Fixed', color='#58a6ff')
ax1.bar(x + 0.2, a_waits, 0.4, label='Adaptive', color='#f78166')
ax1.set_title("Avg Wait Time (s)")
ax1.set_xticks(x);
ax1.set_xticklabels(modes);
ax1.legend()

# Savings Bar
ax2 = fig.add_subplot(gs[0, 1])
ax2.bar(modes, savings, color='#3fb950')
ax2.set_title("Time Saved per Car (Seconds)")
for i, v in enumerate(savings):
    ax2.text(i, v + 0.5, f"{v:.1f}s", ha='center', fontweight='bold')

# Queue Plot (Heavy)
ax3 = fig.add_subplot(gs[1, :])
d_t, d_ns, d_ew = zip(*results["Heavy"]["fixed"].log)
a_t, a_ns, a_ew = zip(*results["Heavy"]["adaptive"].log)
ax3.plot(d_t, np.array(d_ns) + np.array(d_ew), color='#58a6ff', alpha=0.6, label='Fixed Queue')
ax3.plot(a_t, np.array(a_ns) + np.array(a_ew), color='#f78166', label='Adaptive Queue')
ax3.set_title("Total Queue Length (Heavy Traffic Mode)")
ax3.legend()

plt.show()
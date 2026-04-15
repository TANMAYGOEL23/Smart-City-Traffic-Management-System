import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from collections import deque

# Simulation constants 
SIM_DURATION    = 30000
TIME_STEP       = 0.1        # seconds per simulation tick

DEFAULT_CAR_PASS  = 2.0      # seconds to clear one car (default system)
ADAPTIVE_CAR_PASS = 1.4      # seconds to clear one car (adaptive: better signal)

DEFAULT_GREEN   = 5.0
DEFAULT_YELLOW  = 2.0
DEFAULT_ALL_RED = 1.5

ADAPTIVE_MIN_GREEN  = 2.0
ADAPTIVE_MAX_GREEN  = 12.0
ADAPTIVE_FACTOR     = 1.5    # extra seconds per score point
ADAPTIVE_YELLOW     = 1.5
ADAPTIVE_ALL_RED    = 1.0
ADAPTIVE_MAX_WAIT   = 12.0   # starvation threshold (seconds)
ADAPTIVE_SKIP_THR   = 1      # skip if queue <= this after burn-in
ADAPTIVE_BURN_IN    = 1.5    # minimum green seconds before skip-if-empty may fire

TRAFFIC_MODES = {
    "Low":   {"lambda": 0.05, "color": "#4CAF50"},
    "Mid":   {"lambda": 0.15, "color": "#FF9800"},
    "Heavy": {"lambda": 0.30, "color": "#F44336"},
}

# Sensor helpers
def queue_to_distance(n):
    if n >= 5:    return 10
    elif n >= 3:  return 35
    elif n >= 1:  return 75
    else:         return 200

def get_score(d):
    if d < 20:    return 3
    elif d < 50:  return 2
    elif d < 100: return 1
    else:         return 0

def sense_score(queue):
    n  = len(queue)
    d1 = queue_to_distance(n // 2 + n % 2)
    d2 = queue_to_distance(n // 2)
    return get_score(d1) + get_score(d2)


# Data classes
class Car:
    def __init__(self, arrival, direction):
        self.arrival   = arrival
        self.direction = direction
        self.departure = None

    @property
    def wait_time(self):
        return (self.departure - self.arrival) if self.departure is not None else None


class Intersection:
    def __init__(self, lam):
        self.lam       = lam
        self.ns_queue  = deque()
        self.ew_queue  = deque()
        self.departed  = []
        self.time      = 0.0
        self.queue_log = []   # (t, ns_len, ew_len)
        self.green_log = []   # (cycle, green_s, direction)
        self.cycle     = 0

    def arrivals(self, dt):
        for _ in range(np.random.poisson(self.lam * dt)):
            self.ns_queue.append(Car(self.time, "NS"))
        for _ in range(np.random.poisson(self.lam * dt)):
            self.ew_queue.append(Car(self.time, "EW"))

    def discharge(self, queue, car_pass, dt):
        n = max(1, int(dt / car_pass))
        for _ in range(n):
            if not queue: break
            c = queue.popleft()
            c.departure = self.time
            self.departed.append(c)

    def log(self):
        self.queue_log.append((self.time, len(self.ns_queue), len(self.ew_queue)))

    def _phase(self, duration, active_queue=None, car_pass=None):
        end = self.time + duration
        while self.time < end and self.time < SIM_DURATION:
            self.arrivals(TIME_STEP)
            if active_queue is not None:
                self.discharge(active_queue, car_pass, TIME_STEP)
            self.log()
            self.time += TIME_STEP
        self.time = min(self.time, SIM_DURATION)


# Default System
class DefaultSystem(Intersection):
    """Pure fixed-time cycle from Default.txt."""
    def run(self):
        np.random.seed(42)
        self.time = 0.0
        while self.time < SIM_DURATION:
            self._phase(DEFAULT_GREEN,   self.ns_queue, DEFAULT_CAR_PASS)
            self.green_log.append((self.cycle, DEFAULT_GREEN, "NS"))
            self._phase(DEFAULT_YELLOW)
            self._phase(DEFAULT_ALL_RED)

            self._phase(DEFAULT_GREEN,   self.ew_queue, DEFAULT_CAR_PASS)
            self.green_log.append((self.cycle, DEFAULT_GREEN, "EW"))
            self._phase(DEFAULT_YELLOW)
            self._phase(DEFAULT_ALL_RED)
            self.cycle += 1


# Adaptive System 
class AdaptiveSystem(Intersection):
    def run(self):
        np.random.seed(42)
        self.time = 0.0
        last_ns   = -999.0
        last_ew   = -999.0

        while self.time < SIM_DURATION:

            # Sense 
            ns_score = sense_score(self.ns_queue)
            ew_score = sense_score(self.ew_queue)

            # Priority decision 
            ns_priority = ns_score >= ew_score

            # Starvation override
            ns_starved = (self.time - last_ns) > ADAPTIVE_MAX_WAIT
            ew_starved = (self.time - last_ew) > ADAPTIVE_MAX_WAIT
            if ns_starved and not ew_starved: ns_priority = True
            if ew_starved and not ns_starved: ns_priority = False

            # Dominance override: one side 3x heavier → flip immediately
            if ns_score > 0 and ew_score > 0:
                if ew_score >= 3 * ns_score: ns_priority = False
                elif ns_score >= 3 * ew_score: ns_priority = True

            active_score = ns_score if ns_priority else ew_score
            active_q     = self.ns_queue if ns_priority else self.ew_queue
            direction    = "NS" if ns_priority else "EW"

            # Score-proportional green, clamped
            green_time = ADAPTIVE_MIN_GREEN + active_score * ADAPTIVE_FACTOR
            green_time = min(green_time, ADAPTIVE_MAX_GREEN)

            # Green phase
            # Skip-if-empty fires only after ADAPTIVE_BURN_IN seconds of green.
            # This prevents micro-cycles where overhead (yellow+all-red) dominates.
            phase_start = self.time
            end = self.time + green_time
            while self.time < end and self.time < SIM_DURATION:
                self.arrivals(TIME_STEP)
                self.discharge(active_q, ADAPTIVE_CAR_PASS, TIME_STEP)
                self.log()
                self.time += TIME_STEP
                elapsed = self.time - phase_start
                if elapsed >= ADAPTIVE_BURN_IN and len(active_q) <= ADAPTIVE_SKIP_THR:
                    break   # lane clear -- yield remaining green time

            actual_green = round(self.time - phase_start, 2)
            self.green_log.append((self.cycle, actual_green, direction))

            if ns_priority: last_ns = self.time
            else:           last_ew = self.time

            #  Yellow + All-Red (tighter than default) 
            self._phase(ADAPTIVE_YELLOW)
            self._phase(ADAPTIVE_ALL_RED)
            self.cycle += 1


#  Run all simulations
def run_all():
    results = {}
    for mode, cfg in TRAFFIC_MODES.items():
        d = DefaultSystem(cfg["lambda"]);  d.run()
        a = AdaptiveSystem(cfg["lambda"]); a.run()
        results[mode] = {"default": d, "adaptive": a, **cfg}
    return results


# ── Metric helpers 
def avg_wait(sys):
    w = [c.wait_time for c in sys.departed if c.wait_time is not None]
    return np.mean(w) if w else 0

def total_passed(sys):
    return len(sys.departed)

def green_series(sys):
    return [g[1] for g in sys.green_log]

def queue_series(sys):
    t = [q[0] for q in sys.queue_log]
    q = [q[1] + q[2] for q in sys.queue_log]
    return t, q

def smooth(y, w=50):
    arr = np.array(y, dtype=float)
    return np.convolve(arr, np.ones(w) / w, mode='same')


# ── Plot
def plot_results(results):
    modes = list(results.keys())
    DEF_C = "#58a6ff"
    ADP_C = "#f78166"

    fig = plt.figure(figsize=(20, 22), facecolor="#0d1117")
    fig.suptitle(
        "Traffic Light Simulation  --  Default (Fixed) vs Adaptive System\n"
        "5-minute Poisson arrival model  |  Low / Mid / Heavy traffic",
        fontsize=17, fontweight="bold", color="white", y=0.985,
        fontfamily="monospace"
    )

    gs = gridspec.GridSpec(4, 3, figure=fig,
                           hspace=0.55, wspace=0.38,
                           left=0.07, right=0.97, top=0.93, bottom=0.04)

    legend_h = [
        plt.Line2D([0],[0], color=DEF_C, lw=2.5, ls="--", label="Default (Fixed)"),
        plt.Line2D([0],[0], color=ADP_C, lw=2.5, ls="-",  label="Adaptive"),
    ]

    def style(ax):
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e", labelsize=9)
        for sp in ["top","right"]: ax.spines[sp].set_visible(False)
        for sp in ["bottom","left"]: ax.spines[sp].set_color("#30363d")
        ax.grid(True, color="#21262d", lw=0.8, alpha=0.7, zorder=0)
        ax.yaxis.label.set_color("#8b949e")
        ax.xaxis.label.set_color("#8b949e")

    x = np.arange(len(modes))
    w = 0.32

    # [1] Average Wait Time
    ax1 = fig.add_subplot(gs[0, :])
    dw  = [avg_wait(results[m]["default"])  for m in modes]
    aw_ = [avg_wait(results[m]["adaptive"]) for m in modes]
    b1  = ax1.bar(x - w/2, dw,  w, color=DEF_C, alpha=0.85, zorder=3)
    b2  = ax1.bar(x + w/2, aw_, w, color=ADP_C, alpha=0.85, zorder=3)
    for bar, val in zip(list(b1)+list(b2), dw+aw_):
        ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.25,
                 f"{val:.1f}s", ha="center", va="bottom",
                 color="white", fontsize=10, fontfamily="monospace")
    for i, mode in enumerate(modes):
        pct = (dw[i] - aw_[i]) / dw[i] * 100 if dw[i] > 0 else 0
        ax1.annotate(f"-{pct:.0f}%", xy=(x[i], max(dw[i], aw_[i]) + 1.2),
                     ha="center", color="#3fb950", fontsize=12, fontweight="bold",
                     fontfamily="monospace")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{m} Traffic" for m in modes], color="white", fontsize=12)
    ax1.set_ylabel("Avg Wait Time (s)", color="#8b949e", fontsize=11)
    ax1.set_title("[1] Average Wait Time per Car   (green % = adaptive improvement over default)",
                  color="white", fontsize=13, pad=10, fontfamily="monospace")
    ax1.legend(handles=legend_h, facecolor="#161b22", edgecolor="#30363d",
               labelcolor="white", fontsize=10)
    style(ax1)

    # [2] Total Cars Passed
    ax2 = fig.add_subplot(gs[1, :])
    dc_ = [total_passed(results[m]["default"])  for m in modes]
    ac_ = [total_passed(results[m]["adaptive"]) for m in modes]
    b3  = ax2.bar(x - w/2, dc_, w, color=DEF_C, alpha=0.85, zorder=3)
    b4  = ax2.bar(x + w/2, ac_, w, color=ADP_C, alpha=0.85, zorder=3)
    for bar, val in zip(list(b3)+list(b4), dc_+ac_):
        ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                 f"{int(val)}", ha="center", va="bottom",
                 color="white", fontsize=10, fontfamily="monospace")
    for i, mode in enumerate(modes):
        pct  = (ac_[i] - dc_[i]) / dc_[i] * 100 if dc_[i] > 0 else 0
        sign = "+" if pct >= 0 else ""
        col  = "#3fb950" if pct >= 0 else "#f85149"
        ax2.annotate(f"{sign}{pct:.0f}%", xy=(x[i], max(dc_[i], ac_[i]) + 1.5),
                     ha="center", color=col, fontsize=12, fontweight="bold",
                     fontfamily="monospace")
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{m} Traffic" for m in modes], color="white", fontsize=12)
    ax2.set_ylabel("Cars Passed", color="#8b949e", fontsize=11)
    ax2.set_title("[2] Total Cars Passed Through Intersection",
                  color="white", fontsize=13, pad=10, fontfamily="monospace")
    ax2.legend(handles=legend_h, facecolor="#161b22", edgecolor="#30363d",
               labelcolor="white", fontsize=10)
    style(ax2)

    # [3] Green Time per Cycle
    for col, mode in enumerate(modes):
        ax = fig.add_subplot(gs[2, col])
        dg = green_series(results[mode]["default"])
        ag = green_series(results[mode]["adaptive"])
        ax.plot(range(len(dg)), dg, color=DEF_C, lw=1.8, ls="--", alpha=0.9)
        ax.plot(range(len(ag)), ag, color=ADP_C, lw=1.8, alpha=0.9)
        ax.fill_between(range(len(dg)), dg, alpha=0.10, color=DEF_C)
        ax.fill_between(range(len(ag)), ag, alpha=0.10, color=ADP_C)
        ax.axhline(DEFAULT_GREEN, color=DEF_C, lw=0.8, ls=":", alpha=0.4)
        tag = "[L]" if mode=="Low" else "[M]" if mode=="Mid" else "[H]"
        ax.set_title(f"[3] Green Time/Cycle -- {tag} {mode}",
                     color="white", fontsize=11, pad=8, fontfamily="monospace")
        ax.set_xlabel("Cycle #", color="#8b949e", fontsize=9)
        ax.set_ylabel("Green Duration (s)", color="#8b949e", fontsize=9)
        if col == 0:
            ax.legend(handles=legend_h, facecolor="#161b22", edgecolor="#30363d",
                      labelcolor="white", fontsize=8)
        style(ax)

    # [4] Queue Length over Time
    for col, mode in enumerate(modes):
        ax = fig.add_subplot(gs[3, col])
        dt, dq = queue_series(results[mode]["default"])
        at, aq = queue_series(results[mode]["adaptive"])
        ax.plot(dt, smooth(dq), color=DEF_C, lw=1.8, ls="--", alpha=0.9)
        ax.plot(at, smooth(aq), color=ADP_C, lw=1.8, alpha=0.9)
        ax.fill_between(dt, smooth(dq), alpha=0.10, color=DEF_C)
        ax.fill_between(at, smooth(aq), alpha=0.10, color=ADP_C)
        tag = "[L]" if mode=="Low" else "[M]" if mode=="Mid" else "[H]"
        ax.set_title(f"[4] Queue Length -- {tag} {mode}",
                     color="white", fontsize=11, pad=8, fontfamily="monospace")
        ax.set_xlabel("Time (s)", color="#8b949e", fontsize=9)
        ax.set_ylabel("Cars in Queue", color="#8b949e", fontsize=9)
        if col == 0:
            ax.legend(handles=legend_h, facecolor="#161b22", edgecolor="#30363d",
                      labelcolor="white", fontsize=8)
        style(ax)

    plt.savefig("traffic_simulation.png", dpi=150,
                bbox_inches="tight", facecolor=fig.get_facecolor())
    print("Saved: traffic_simulation.png")


# ── Summary table
def print_summary(results):
    print("\n" + "="*72)
    print(f"{'SIMULATION SUMMARY':^72}")
    print("="*72)
    print(f"{'Mode':<8} {'System':<10} {'Avg Wait':>10} {'Cars Passed':>12} "
          f"{'Cycles':>8} {'Wait Improvement':>17}")
    print("-"*72)
    for mode in results:
        d   = results[mode]["default"]
        a   = results[mode]["adaptive"]
        dw  = avg_wait(d);      aw_ = avg_wait(a)
        dc  = total_passed(d);  ac  = total_passed(a)
        imp = (dw - aw_) / dw * 100 if dw else 0
        print(f"{mode:<8} {'Default':<10} {dw:>9.2f}s {dc:>12d} {d.cycle:>8d} {'---':>17}")
        print(f"{'':8} {'Adaptive':<10} {aw_:>9.2f}s {ac:>12d} {a.cycle:>8d} "
              f"  {'-'+f'{imp:.1f}%':>15}")
        print("-"*72)


if __name__ == "__main__":
    print("Running traffic simulations  (5 min, Poisson arrivals)...")
    results = run_all()
    print_summary(results)
    plot_results(results)

#!/usr/bin/env python3
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow

INK = "#161616"; PAPER = "#F4F2ED"; RED = "#D93A2B"; GRAY = "#8A8578"; LINE = "#D8D4CA"
MONO = "DejaVu Sans Mono"
plt.rcParams.update({"font.family": MONO, "text.color": INK, "axes.edgecolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "svg.fonttype": "none"})

r1 = json.load(open("log/round1_results.json"))["results"]
tr = json.load(open("log/transfer_results.json"))["results"]
sc = json.load(open("log/round1_scored.json"))
fm = json.load(open("log/final_metrics.json"))

order = list(r1.keys()) + list(tr.keys())
refuted = {t: (r1[t]["refuted"] if t in r1 else tr[t]["refuted"]) for t in order}

# ---------------- COVER 2000x800 ----------------
fig = plt.figure(figsize=(20, 8), dpi=100); fig.patch.set_facecolor(PAPER)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 20); ax.set_ylim(0, 8); ax.axis("off")
ax.text(1.0, 6.55, "CAN AN AI AGENT", fontsize=58, fontweight="bold", va="center")
ax.text(1.0, 5.35, "LEARN FROM BEING WRONG?", fontsize=58, fontweight="bold", va="center")
ax.text(1.02, 4.35, "a falsification benchmark - 24 pre-registered quantitative predictions,", fontsize=19, color=GRAY)
ax.text(1.02, 3.85, "hidden defects in data, code, metrics and framing. run on one agent: me.", fontsize=19, color=GRAY)
# 24-cell strip
x0, y0, s, gap = 1.02, 1.6, 0.62, 0.16
for i, t in enumerate(order):
    x = x0 + i * (s + gap)
    if refuted[t]:
        ax.add_patch(Rectangle((x, y0), s, s, facecolor=RED, edgecolor=RED))
        ax.text(x + s/2, y0 + s/2, t, fontsize=10, ha="center", va="center", color=PAPER)
    else:
        ax.add_patch(Rectangle((x, y0), s, s, facecolor="none", edgecolor=INK, lw=1.4))
        ax.text(x + s/2, y0 + s/2, t, fontsize=10, ha="center", va="center", color=INK)
ax.text(x0, 0.95, "filled = refuted (11/24)   outline = confirmed (13/24)   diagnosis accuracy 11/11   transfer 4/4", fontsize=15, color=INK)
ax.plot([1.02, 18.98], [7.45, 7.45], color=INK, lw=2)
ax.text(18.98, 7.62, "WRONGBENCH 01 - @0maxxdev", fontsize=13, ha="right", color=GRAY)
fig.savefig("fig_cover.png", dpi=100, facecolor=PAPER); plt.close(fig)

# ---------------- FIG 1: protocol loop 1600x900 ----------------
fig = plt.figure(figsize=(16, 9), dpi=100); fig.patch.set_facecolor(PAPER)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")
ax.text(0.8, 8.3, "PROTOCOL - one task, one loop", fontsize=22, fontweight="bold")
steps = [("1 HYPOTHESIS", "quantitative claim"), ("2 PRE-REGISTER", "value + tolerance,\nlogged before run"),
         ("3 EXECUTE", "seeded pipeline,\nhidden defects"), ("4 REFUTE?", "|obs - pred| > tol"),
         ("5 DIAGNOSE", "hypothesis / data /\ncode / metric / frame"), ("6 REVISE", "new model +\nnew prediction"),
         ("7 RE-RUN", "revised prediction\nscored vs corrected value")]
bw, bh, y = 1.9, 1.55, 5.4
xs = [0.8 + i * 2.16 for i in range(7)]
for (title, sub), x in zip(steps, xs):
    hot = title.startswith("4")
    ax.add_patch(Rectangle((x, y), bw, bh, facecolor=RED if hot else "none",
                           edgecolor=RED if hot else INK, lw=1.6))
    ax.text(x + 0.12, y + bh - 0.34, title, fontsize=13, fontweight="bold",
            color=PAPER if hot else INK)
    ax.text(x + 0.12, y + bh - 0.72, sub, fontsize=10.5, color=PAPER if hot else GRAY, va="top")
    if x != xs[-1]:
        ax.annotate("", xy=(x + 2.12, y + bh/2), xytext=(x + bw + 0.02, y + bh/2),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4))
# feedback arrow 7 -> 1
ax.annotate("", xy=(xs[0] + bw/2, y - 0.12), xytext=(xs[-1] + bw/2, y - 0.12),
            arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.2,
                            connectionstyle="arc3,rad=0.25"))
ax.text(8.0, 3.35, "next task inherits the revised model", fontsize=12, color=GRAY, ha="center")
ax.text(0.8, 2.3, "BLINDING", fontsize=15, fontweight="bold")
ax.text(0.8, 1.15, "task parameters, defect activation (p=0.75 per candidate) and hidden frames\n"
                   "are drawn from a seeded RNG the agent never executes.\n"
                   "pipeline source is revealed only after a refutation.", fontsize=12.5, color=INK, va="center")
fig.savefig("fig_protocol.png", dpi=100, facecolor=PAPER); plt.close(fig)

# ---------------- FIG 2: deviation chart ----------------
fig, ax = plt.subplots(figsize=(16, 9), dpi=100); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
devs, cols, labels = [], [], []
for t in order:
    v = r1[t] if t in r1 else tr[t]
    d = abs(v["observed"] - v["prediction"]["value"]) / v["prediction"]["tol"]
    devs.append(max(d, 0.012)); cols.append(RED if v["refuted"] else INK); labels.append(t)
ax.bar(range(len(order)), devs, color=cols, width=0.62)
ax.axhline(1.0, color=INK, lw=1.2, ls="--")
ax.text(23.4, 1.13, "refutation threshold", fontsize=12, ha="right")
ax.set_yscale("log"); ax.set_ylim(0.01, 3000)
ax.set_xticks(range(len(order))); ax.set_xticklabels(labels, fontsize=12)
ax.set_ylabel("|observed - predicted| / tolerance   (log)", fontsize=13)
ax.set_title("ROUND 1 + TRANSFER - how wrong was each prediction", fontsize=18, fontweight="bold", loc="left", pad=16)
for s in ["top", "right"]: ax.spines[s].set_visible(False)
ax.tick_params(axis="y", labelsize=12); ax.grid(axis="y", color=LINE, lw=0.7)
ax.set_axisbelow(True)
fig.tight_layout(pad=2.4)
fig.savefig("fig_deviation.png", dpi=100, facecolor=PAPER); plt.close(fig)

# ---------------- FIG 3: diagnosis matrix + transfer ----------------
classes = ["hypothesis", "data", "code", "measurement", "conceptual"]
M = [[0]*5 for _ in range(5)]
for t, v in sc.items():
    if v["status"] != "refuted": continue
    M[classes.index(v["truth_class"])][classes.index(v["diagnosis"])] += 1
for t, v in fm["transfer_scored"].items():
    M[classes.index(v["truth_class"])][classes.index(v["diagnosis"])] += 1
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(16, 9), dpi=100, gridspec_kw={"width_ratios": [1.05, 1]})
fig.patch.set_facecolor(PAPER)
ax.set_facecolor(PAPER); ax.set_xlim(0, 5); ax.set_ylim(0, 5)
for i in range(5):
    for j in range(5):
        n = M[4-i][j]
        ax.add_patch(Rectangle((j, i), 1, 1, facecolor=RED if (n and j == 4-i) else ("#B8B2A4" if n else "none"),
                               edgecolor=LINE, lw=1))
        if n: ax.text(j+0.5, i+0.5, str(n), ha="center", va="center", fontsize=20,
                      color=PAPER, fontweight="bold")
ax.set_xticks([x+0.5 for x in range(5)]); ax.set_xticklabels([c[:6] for c in classes], fontsize=12)
ax.set_yticks([x+0.5 for x in range(5)]); ax.set_yticklabels([c[:6] for c in reversed(classes)], fontsize=12)
ax.set_xlabel("diagnosed as", fontsize=13); ax.set_ylabel("true error class", fontsize=13)
ax.set_title("ERROR ATTRIBUTION - 11 refutations", fontsize=17, fontweight="bold", loc="left", pad=14)
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
# right: headline metrics
ax2.set_facecolor(PAPER); ax2.axis("off"); ax2.set_xlim(0, 10); ax2.set_ylim(0, 10)
rows = [("diagnosis accuracy", "11 / 11"), ("real model revisions", "11 / 11"),
        ("verbal excuses", "0"), ("revised predictions confirmed", "11 / 11"),
        ("repeated error classes", "0"), ("transfer: pre-declared\ndefect class correct", "4 / 4"),
        ("re-run reproducible", "yes"), ("failed branches retained", "all")]
yy = 9.0
ax2.set_title("SCOREBOARD", fontsize=17, fontweight="bold", loc="left", pad=14)
for name, val in rows:
    ax2.text(0.2, yy, name, fontsize=14, va="center")
    ax2.text(9.8, yy, val, fontsize=16, va="center", ha="right", fontweight="bold",
             color=RED if val in ("0",) else INK)
    ax2.plot([0.2, 9.8], [yy-0.55, yy-0.55], color=LINE, lw=0.8)
    yy -= 1.18
fig.tight_layout(pad=2.6)
fig.savefig("fig_matrix.png", dpi=100, facecolor=PAPER); plt.close(fig)
print("done")

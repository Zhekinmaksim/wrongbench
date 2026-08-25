#!/usr/bin/env python3
"""WRONGBENCH - can an agent learn from being wrong?
Phases: gen -> (agent predictions.json) -> run -> (agent revisions.json)
        -> score -> transfer -> (agent transfer_predictions.json) -> transfer_run
        -> (agent transfer_revisions.json) -> final
All hidden state derives from SEED. Agent never executes hidden branches.
"""
import json, math, sys, random, statistics, hashlib, time, os

SEED = "BUILD-NOTHING-IS-WRONG-01"
LOG = "log"
os.makedirs(LOG, exist_ok=True)

def rng_for(tag):
    h = int(hashlib.sha256((SEED + "::" + tag).encode()).hexdigest(), 16) % (2**63)
    return random.Random(h)

def save(name, obj):
    with open(f"{LOG}/{name}", "w") as f:
        json.dump(obj, f, indent=1)

def load(name):
    with open(name) as f:
        return json.load(f)

# ---------------- hidden config ----------------
def hidden():
    r = rng_for("config")
    cfg = {}
    # defect candidates: activated with p=0.75 each (agent does not know which)
    for tid in ["b1","b2","b3","c1","c2","c3","d1","d2","d3"]:
        cfg[tid+"_active"] = (r.random() < 0.75)
    # task params
    cfg["b1_scale"] = round(r.uniform(1.5, 3.0), 2)
    cfg["b2_frac_inch"] = round(r.uniform(0.15, 0.35), 2)
    cfg["b3_dupfrac"] = round(r.uniform(0.4, 0.6), 2)
    cfg["c3_mu"] = round(r.uniform(0.0008, 0.0015), 5)
    cfg["d1_mu"], cfg["d1_sig"] = round(r.uniform(0.8, 1.2), 2), round(r.uniform(0.7, 1.0), 2)
    cfg["d2_alpha"] = round(r.uniform(2.2, 3.0), 2)
    cfg["e1_equal"] = r.choice(["distance", "time"])   # hidden frame
    cfg["e1_v1"], cfg["e1_v2"] = r.choice([(30,60),(40,80),(20,60)])
    cfg["e2_sizes"] = [r.randint(100,900) for _ in range(4)]  # hidden strata weights
    cfg["e3_prev"] = round(r.uniform(0.005, 0.05), 3)          # hidden prevalence
    # transfer
    cfg["t1_frac_lb"] = round(r.uniform(0.1, 0.4), 2)
    cfg["t4_equal"] = r.choice(["distance", "fuel"])
    return cfg

# ---------------- task statements (public) ----------------
def statements(cfg):
    return {
 "a1": "20000 simulated rooms; people enter one by one with uniform random birthdays (365 days). Report the MEAN index (1-based) of the first person whose birthday repeats an earlier one.",
 "a2": "Coupon collector, 50 distinct coupons, uniform draws, 20000 trials. Report MEAN number of draws to complete the set.",
 "a3": "Simple symmetric +/-1 random walk from 0, 100 steps, 200000 walks. Report P(walk returns to 0 at least once within the 100 steps).",
 "a4": "Monte-Carlo pi: each estimate uses n=10000 uniform points in the unit square; 2000 independent estimates. Report the STANDARD DEVIATION of the 2000 estimates.",
 "a5": "First 5000 Fibonacci numbers (F1=1). Report fraction whose leading digit is 1.",
 "a6": "100-prisoners problem, cycle-following strategy, 100000 trials. Report success probability (all prisoners find their number in <=50 box openings).",
 "a7": "Secretary problem, n=100 candidates, classic 'observe first 37 then take first better' rule, 100000 trials. Report P(best candidate selected).",
 "a8": "Truncated St. Petersburg: fair coin, payoff 2^k where k is the flip index of the first head, k capped at 20 (if no head by 20, payoff 2^20). 200000 trials. Report the MEAN payoff.",
 "b1": f"Dataset D_b1: 5000 samples generated as Exponential(scale={cfg['b1_scale']}), then passed through the lab's standard ingestion step. Report the sample MEAN of the ingested dataset.",
 "b2": "Dataset D_b2: 4000 adult height records, generated as Normal(mean=175, sd=7) centimeters, then passed through the lab's standard ingestion step. Report the sample MEAN of the ingested dataset.",
 "b3": "Dataset D_b3: 2000 daily returns generated as Normal(0, sd=0.02), then passed through the lab's standard ingestion step. Report the STANDARD ERROR OF THE MEAN as computed by the standard estimator sd/sqrt(n) on the ingested dataset.",
 "c1": "E[max of 5 iid U(0,1)] estimated by the lab's trial runner: 1000 trials, each trial averages 100 sampled maxima. Report the STANDARD DEVIATION of the 1000 per-trial estimates.",
 "c2": "Dataset: 5000 samples U(10,11). The lab's mean() implementation computes the mean. Report the computed mean.",
 "c3": f"Log-price series: 4000 steps, each step log-return Normal(mu={cfg['c3_mu']}, sd=0.0004). The lab's total_return() sums per-step log-returns over the series. Report the computed total log-return.",
 "d1": f"Dataset: 6000 samples LogNormal(mu={cfg['d1_mu']}, sigma={cfg['d1_sig']}). Report the value of the lab metric central_tendency_mean() on this dataset.",
 "d2": f"Dataset: 8000 samples Pareto(alpha={cfg['d2_alpha']}, xm=1). Report the value of the lab metric robust_mean() on this dataset.",
 "d3": "Dataset: 6000 samples Exponential(scale=2.0). Report the value of the lab metric average() on this dataset.",
 "e1": f"A logged two-segment trip. Segment speeds: {cfg['e1_v1']} km/h and {cfg['e1_v2']} km/h. Segment metadata (lengths/durations) is in the data file. Report the trip's overall average speed (total distance / total time).",
 "e2": "A/B outcome log with four strata (two per arm). Per-stratum success rates: A1=0.93, A2=0.73, B1=0.87, B2=0.69. Stratum sizes are in the data file. Report the OVERALL pooled success rate of arm A minus arm B (pooled_A - pooled_B).",
 "e3": "Diagnostic test: sensitivity 0.95, specificity 0.95. A screened population sample is in the data file. Report P(disease | positive test) in that population.",
    }

def transfer_statements(cfg):
    return {
 "t1": "Dataset D_t1: 3000 bodyweight records generated as Normal(mean=82, sd=9) kilograms, then passed through the lab's standard ingestion step. Report the sample MEAN.",
 "t2": "Bootstrap CI for the mean of 1000 samples N(50, sd=5): the lab's bootstrap runner draws 2000 resamples and reports the WIDTH of the 95% percentile CI. Report that width.",
 "t3": "Dataset: 6000 request latencies, LogNormal(mu=3.0, sigma=0.8) ms. Report the lab metric mean_latency() on this dataset.",
 "t4": "A logged two-segment drive. Segment fuel efficiencies: 20 mpg and 40 mpg. Segment metadata is in the data file. Report overall trip efficiency (total miles / total gallons).",
    }

# ---------------- pipelines (defective where active) ----------------
def observed_value(tid, cfg):
    r = rng_for("task-" + tid)
    if tid == "a1":
        tot = 0
        for _ in range(20000):
            seen, i = set(), 0
            while True:
                i += 1
                b = r.randrange(365)
                if b in seen: break
                seen.add(b)
            tot += i
        return tot / 20000
    if tid == "a2":
        tot = 0
        for _ in range(20000):
            seen, d = set(), 0
            while len(seen) < 50:
                seen.add(r.randrange(50)); d += 1
            tot += d
        return tot / 20000
    if tid == "a3":
        hit = 0
        for _ in range(200000):
            p, ret = 0, False
            for _ in range(100):
                p += r.choice((-1, 1))
                if p == 0: ret = True; break
            hit += ret
        return hit / 200000
    if tid == "a4":
        ests = []
        for _ in range(2000):
            c = sum(1 for _ in range(10000) if r.random()**2 + r.random()**2 <= 1)
            ests.append(4 * c / 10000)
        return statistics.pstdev(ests)
    if tid == "a5":
        a, b, cnt = 1, 1, 0
        for _ in range(5000):
            if str(a)[0] == "1": cnt += 1
            a, b = b, a + b
        return cnt / 5000
    if tid == "a6":
        ok = 0
        for _ in range(100000):
            boxes = list(range(100)); r.shuffle(boxes)
            good = True
            seen = [False]*100
            for s in range(100):
                if seen[s]: continue
                ln, cur = 0, s
                while True:
                    ln += 1; seen[cur] = True; cur = boxes[cur]
                    if cur == s: break
                if ln > 50: good = False; break
            ok += good
        return ok / 100000
    if tid == "a7":
        ok = 0
        for _ in range(100000):
            v = list(range(100)); r.shuffle(v)
            best37 = max(v[:37]); pick = None
            for x in v[37:]:
                if x > best37: pick = x; break
            ok += (pick == 99)
        return ok / 100000
    if tid == "a8":
        tot = 0
        for _ in range(200000):
            k = 1
            while k < 20 and r.random() < 0.5:
                k += 1
            tot += 2 ** k
        return tot / 200000
    if tid == "b1":
        xs = [r.expovariate(1 / cfg["b1_scale"]) for _ in range(5000)]
        if cfg["b1_active"]:
            q = sorted(xs)[int(0.95 * len(xs))]
            xs = [x for x in xs if x <= q]          # silent top-5% censoring
        return sum(xs) / len(xs)
    if tid == "b2":
        xs = [r.gauss(175, 7) for _ in range(4000)]
        if cfg["b2_active"]:
            k = int(cfg["b2_frac_inch"] * len(xs))
            xs = [x / 2.54 for x in xs[:k]] + xs[k:]  # silent cm->inch mix
        return sum(xs) / len(xs)
    if tid == "b3":
        xs = [r.gauss(0, 0.02) for _ in range(2000)]
        if cfg["b3_active"]:
            k = int(cfg["b3_dupfrac"] * len(xs))
            xs = xs + xs[:k]                          # silent row duplication
        m = sum(xs) / len(xs)
        sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
        return sd / math.sqrt(len(xs))
    if tid == "c1":
        ests = []
        for t in range(1000):
            rr = random.Random(12345 if cfg["c1_active"] else r.random())  # bug: fixed reseed
            ests.append(sum(max(rr.random() for _ in range(5)) for _ in range(100)) / 100)
        return statistics.pstdev(ests)
    if tid == "c2":
        xs = [r.uniform(10, 11) for _ in range(5000)]
        s = sum(xs)
        return (s // len(xs)) if cfg["c2_active"] else (s / len(xs))       # bug: int division
    if tid == "c3":
        xs = [r.gauss(cfg["c3_mu"], 0.0004) for _ in range(4000)]
        n = len(xs) // 2 if cfg["c3_active"] else len(xs)                  # bug: half loop
        return sum(xs[:n])
    if tid == "d1":
        xs = [r.lognormvariate(cfg["d1_mu"], cfg["d1_sig"]) for _ in range(6000)]
        if cfg["d1_active"]:
            return statistics.median(xs)                                   # claims mean, is median
        return sum(xs) / len(xs)
    if tid == "d2":
        a = cfg["d2_alpha"]
        xs = [(1.0 / (1 - r.random())) ** (1 / a) for _ in range(8000)]
        if cfg["d2_active"]:
            xs = [min(x, 20.0) for x in xs]                                # silent clip at 20
        return sum(xs) / len(xs)
    if tid == "d3":
        xs = [r.expovariate(0.5) for _ in range(6000)]
        if cfg["d3_active"]:
            xs = sorted(xs)[int(0.1 * len(xs)): int(0.9 * len(xs))]        # silent 10% trim
        return sum(xs) / len(xs)
    if tid == "e1":
        v1, v2 = cfg["e1_v1"], cfg["e1_v2"]
        if cfg["e1_equal"] == "distance":
            return 2 * v1 * v2 / (v1 + v2)      # harmonic
        return (v1 + v2) / 2                     # arithmetic (equal time)
    if tid == "e2":
        n1, n2, n3, n4 = cfg["e2_sizes"]
        pa = (0.93 * n1 + 0.73 * n2) / (n1 + n2)
        pb = (0.87 * n3 + 0.69 * n4) / (n3 + n4)
        return pa - pb
    if tid == "e3":
        p = cfg["e3_prev"]
        return 0.95 * p / (0.95 * p + 0.05 * (1 - p))
    # transfer
    if tid == "t1":
        xs = [r.gauss(82, 9) for _ in range(3000)]
        k = int(cfg["t1_frac_lb"] * len(xs))
        xs = [x * 2.20462 for x in xs[:k]] + xs[k:]                        # kg->lb mix (active)
        return sum(xs) / len(xs)
    if tid == "t2":
        xs = [r.gauss(50, 5) for _ in range(1000)]
        means = []
        for b in range(2000):
            rr = random.Random(999)                                        # bug: fixed reseed (active)
            means.append(sum(rr.choice(xs) for _ in range(1000)) / 1000)
        means.sort()
        return means[int(0.975 * 2000)] - means[int(0.025 * 2000)]
    if tid == "t3":
        xs = [r.lognormvariate(3.0, 0.8) for _ in range(6000)]
        xs = sorted(xs)[: int(0.9 * len(xs))]                              # drops top decile (active)
        return sum(xs) / len(xs)
    if tid == "t4":
        if cfg["t4_equal"] == "distance":
            return 2 * 20 * 40 / (20 + 40)      # harmonic
        return (20 + 40) / 2                     # equal fuel -> arithmetic
    raise KeyError(tid)

TRUTH_CLASS = {  # ground-truth error class when refuted
 **{t: "hypothesis" for t in ["a1","a2","a3","a4","a5","a6","a7","a8"]},
 "b1": "data", "b2": "data", "b3": "data",
 "c1": "code", "c2": "code", "c3": "code",
 "d1": "measurement", "d2": "measurement", "d3": "measurement",
 "e1": "conceptual", "e2": "conceptual", "e3": "conceptual",
 "t1": "data", "t2": "code", "t3": "measurement", "t4": "conceptual",
}

# pipeline source snippets revealed at diagnosis time (as-shipped, incl. bugs if active)
def source_reveal(tid, cfg):
    src = {
 "b1": "def ingest(xs):\n    q = quantile(xs, 0.95)\n    return [x for x in xs if x <= q]   # 'outlier guard'",
 "b2": "def ingest(xs):\n    # merges two collection sheets\n    return sheetA_values + sheetB_values",
 "b3": "def ingest(xs):\n    return xs + xs[:k]   # 'backfill from mirror'",
 "c1": "for t in range(1000):\n    rr = random.Random(12345)\n    est = mean(max5_uniform(rr) for _ in range(100))",
 "c2": "def mean(xs):\n    return sum(xs) // len(xs)",
 "c3": "def total_return(xs):\n    return sum(xs[: len(xs)//2 ])",
 "d1": "def central_tendency_mean(xs):\n    return median(xs)",
 "d2": "def robust_mean(xs):\n    return mean(min(x, 20.0) for x in xs)",
 "d3": "def average(xs):\n    s = sorted(xs)\n    return mean(s[len(s)//10 : -len(s)//10])",
 "e1": "segments: [{'mode': 'equal-" + cfg["e1_equal"] + "'}]",
 "e2": "strata sizes: " + str(cfg["e2_sizes"]),
 "e3": "population prevalence (from data file): " + str(cfg["e3_prev"]),
 "t1": "def ingest(xs):\n    return sheet_metric + sheet_imperial",
 "t2": "for b in range(2000):\n    rr = random.Random(999)\n    means.append(mean(resample(xs, rr)))",
 "t3": "def mean_latency(xs):\n    s = sorted(xs)\n    return mean(s[: int(0.9*len(s))])   # 'excludes outlier spikes'",
 "t4": "segments: [{'mode': 'equal-" + cfg["t4_equal"] + "'}]",
    }
    active = {"b1","b2","b3","c1","c2","c3","d1","d2","d3"}
    if tid in active and not cfg.get(tid + "_active", True):
        return "(pipeline ran in clean reference mode for this task)"
    return src.get(tid, "(no lab pipeline: direct simulation, code is the reference implementation)")

def corrected_value(tid, cfg):
    """value with the defect removed (for scoring revised predictions)"""
    cfg2 = dict(cfg)
    for k in list(cfg2):
        if k.endswith("_active"):
            cfg2[k] = False
    if tid == "t1":
        r = rng_for("task-t1"); xs = [r.gauss(82, 9) for _ in range(3000)]
        return sum(xs) / len(xs)
    if tid == "t2":
        r = rng_for("task-t2"); xs = [r.gauss(50, 5) for _ in range(1000)]
        rr = random.Random(777); means = []
        for b in range(2000):
            means.append(sum(rr.choice(xs) for _ in range(1000)) / 1000)
        means.sort()
        return means[int(0.975 * 2000)] - means[int(0.025 * 2000)]
    if tid == "t3":
        r = rng_for("task-t3"); xs = [r.lognormvariate(3.0, 0.8) for _ in range(6000)]
        return sum(xs) / len(xs)
    if tid == "t4":
        return observed_value(tid, cfg)
    return observed_value(tid, cfg2)

# ---------------- phases ----------------
def phase_gen():
    cfg = hidden()
    save("hidden_cfg.json", cfg)
    st = statements(cfg)
    save("tasks_public.json", st)
    print(json.dumps(st, indent=1))

def phase_run():
    cfg = load(f"{LOG}/hidden_cfg.json")
    preds = load("predictions.json")
    out = {}
    for tid, st in statements(cfg).items():
        obs = observed_value(tid, cfg)
        p = preds[tid]
        refuted = abs(obs - p["value"]) > p["tol"]
        out[tid] = {"prediction": p, "observed": round(obs, 6), "refuted": refuted,
                    "reveal": source_reveal(tid, cfg) if refuted else None}
    save("round1_results.json", {"ts": time.time(), "results": out})
    print(json.dumps(out, indent=1))

def phase_score():
    cfg = load(f"{LOG}/hidden_cfg.json")
    res = load(f"{LOG}/round1_results.json")["results"]
    revs = load("revisions.json")
    scored = {}
    for tid, r1 in res.items():
        if not r1["refuted"]:
            scored[tid] = {"status": "confirmed"}
            continue
        rv = revs[tid]
        truth = TRUTH_CLASS[tid]
        # if defect candidate was inactive, truth class is 'hypothesis'
        if tid + "_active" in cfg and not cfg[tid + "_active"]:
            truth = "hypothesis"
        corr = corrected_value(tid, cfg)
        target = r1["observed"] if rv["diagnosis"] == "hypothesis" else corr
        rev_ok = abs(target - rv["value"]) <= rv["tol"]
        same_pred = abs(rv["value"] - r1["prediction"]["value"]) <= 0.01 * max(1e-9, abs(r1["prediction"]["value"]))
        # real revision: revised target hit AND a concrete model change:
        #  - hypothesis/conceptual classes must move the number
        #  - data/code/measurement classes fix the pipeline (number may legitimately return to the prior)
        pipeline_fix = rv["diagnosis"] in ("data", "code", "measurement")
        real = rev_ok and bool(rv.get("model_change")) and (pipeline_fix or not same_pred)
        scored[tid] = {"status": "refuted",
                       "diagnosis": rv["diagnosis"], "truth_class": truth,
                       "diagnosis_correct": rv["diagnosis"] == truth,
                       "observed": r1["observed"], "corrected": round(corr, 6),
                       "revised_prediction": rv["value"], "revised_ok": rev_ok,
                       "real_revision": real,
                       "verbal_only": (not rev_ok) or not rv.get("model_change")}
    save("round1_scored.json", scored)
    print(json.dumps(scored, indent=1))

def phase_transfer():
    cfg = load(f"{LOG}/hidden_cfg.json")
    st = transfer_statements(cfg)
    save("transfer_public.json", st)
    print(json.dumps(st, indent=1))

def phase_transfer_run():
    cfg = load(f"{LOG}/hidden_cfg.json")
    preds = load("transfer_predictions.json")
    out = {}
    for tid in transfer_statements(cfg):
        obs = observed_value(tid, cfg)
        p = preds[tid]
        refuted = abs(obs - p["value"]) > p["tol"]
        out[tid] = {"prediction": p, "observed": round(obs, 6), "refuted": refuted,
                    "reveal": source_reveal(tid, cfg) if refuted else None,
                    "pre_diagnosis": p.get("suspected_class")}
    save("transfer_results.json", {"ts": time.time(), "results": out})
    print(json.dumps(out, indent=1))

def phase_final():
    cfg = load(f"{LOG}/hidden_cfg.json")
    s1 = load(f"{LOG}/round1_scored.json")
    tr = load(f"{LOG}/transfer_results.json")["results"]
    trev = load("transfer_revisions.json") if os.path.exists("transfer_revisions.json") else {}
    tscored = {}
    for tid, r in tr.items():
        truth = TRUTH_CLASS[tid]
        pre = r.get("pre_diagnosis")
        entry = {"refuted": r["refuted"], "truth_class": truth,
                 "pre_diagnosis": pre, "pre_diagnosis_correct": pre == truth}
        if r["refuted"] and tid in trev:
            rv = trev[tid]
            corr = corrected_value(tid, cfg)
            target = r["observed"] if rv["diagnosis"] == "hypothesis" else corr
            entry.update({"diagnosis": rv["diagnosis"],
                          "diagnosis_correct": rv["diagnosis"] == truth,
                          "corrected": round(corr, 6),
                          "revised_ok": abs(target - rv["value"]) <= rv["tol"]})
        tscored[tid] = entry
    # reproducibility: recompute all observed values
    repro = all(abs(observed_value(t, cfg) -
                    (load(f"{LOG}/round1_results.json")["results"][t]["observed"]
                     if t in load(f"{LOG}/round1_results.json")["results"] else tr[t]["observed"])) < 1e-6
                for t in list(statements(cfg)) + list(transfer_statements(cfg)))
    ref = [t for t, v in s1.items() if v["status"] == "refuted"]
    metrics = {
        "n_tasks_main": 20, "n_tasks_transfer": 4,
        "refuted_main": len(ref),
        "confirmed_main": 20 - len(ref),
        "diagnosis_accuracy_main": round(sum(s1[t]["diagnosis_correct"] for t in ref) / max(1, len(ref)), 3),
        "real_revision_rate": round(sum(bool(s1[t]["real_revision"]) for t in ref) / max(1, len(ref)), 3),
        "verbal_only_rate": round(sum(s1[t]["verbal_only"] for t in ref) / max(1, len(ref)), 3),
        "revised_prediction_ok": round(sum(s1[t]["revised_ok"] for t in ref) / max(1, len(ref)), 3),
        "repeat_error_classes": sorted({s1[t]["truth_class"] for t in ref if not s1[t]["diagnosis_correct"]}
                                       & {tscored[t]["truth_class"] for t in tscored
                                          if tscored[t].get("diagnosis") and not tscored[t]["diagnosis_correct"]}),
        "transfer_pre_diagnosis_acc": round(sum(v["pre_diagnosis_correct"] for v in tscored.values()) / 4, 3),
        "transfer_scored": tscored,
        "reproducible": repro,
        "branches_retained": sorted(os.listdir(LOG)),
    }
    save("final_metrics.json", metrics)
    print(json.dumps(metrics, indent=1))

if __name__ == "__main__":
    {"gen": phase_gen, "run": phase_run, "score": phase_score,
     "transfer": phase_transfer, "transfer_run": phase_transfer_run,
     "final": phase_final}[sys.argv[1]]()

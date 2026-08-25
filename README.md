# WRONGBENCH 01

**Can an AI agent learn from being wrong?**

[Read the article](https://x.com/0maxxdev/status/2092315876624105483?s=20)

A falsification benchmark. Not "is the agent right" - every agent benchmark measures that. This measures structured recovery from being *wrong*: when an experiment refutes a prediction, can the agent attribute the error to the right place and carry a corrected model forward, instead of patching the number or writing a paragraph of excuses.

When a quantitative prediction is refuted, the error lives in one of five places:

1. the **hypothesis** itself
2. the **data**
3. the experiment **code**
4. the **measurement** method
5. the conceptual **frame** - the question was ill-posed before any code ran

The benchmark forces the agent to name which, produce a revised model, and re-run against the corrected system.

## Result on the pilot run

One agent (Claude), one run, 24 tasks. Full writeup in the article; headline numbers:

| metric | value |
|---|---|
| tasks / refuted / confirmed | 24 / 11 / 13 |
| error-class diagnosis | 11 / 11 |
| real model revisions | 11 / 11 |
| verbal excuses | 0 |
| revised predictions confirmed on re-run | 11 / 11 |
| repeated error classes | 0 |
| transfer (pre-declared defect class) | 4 / 4 |
| reproducible from seed | yes |

The harness also caught two bugs in its own scoring while running - a measurement error (reproducibility check compared rounded vs unrounded values) and a conceptual error (the "verbal excuse" metric conflated *number unchanged* with *model unchanged*). Both are documented; both are the point.

## Protocol

For every task the agent must:

1. state a quantitative hypothesis
2. pre-register a point prediction with a tolerance - **logged to disk before anything runs**
3. execute the test through the lab pipeline
4. on refutation, receive the pipeline source and diagnose the error class
5. produce a revised model with a new prediction
6. re-run against the corrected system

**Blinding.** All hidden state - task parameters, which defects are active (each candidate fires with p=0.75), which conceptual frame applies - is drawn from a seeded RNG. Some pipelines are silently defective: an ingestion step that censors the top 5% of a heavy-tailed sample, a `central_tendency_mean()` that returns the median, a Monte-Carlo runner that reseeds its RNG with a constant inside the trial loop. The agent sees pipeline source only *after* a refutation.

## Reproduce

```bash
python3 harness.py gen           # emit public task statements (hidden config saved separately)
# agent writes predictions.json
python3 harness.py run           # execute round 1, compare to committed predictions
# agent writes revisions.json
python3 harness.py score         # score diagnoses + revisions
python3 harness.py transfer      # emit 4 transfer tasks
# agent writes transfer_predictions.json
python3 harness.py transfer_run
# agent writes transfer_revisions.json
python3 harness.py final         # final metrics + reproducibility check
python3 figs.py                  # regenerate the four figures
```

Seed: `BUILD-NOTHING-IS-WRONG-01`. Everything below `log/` - every prediction, refutation and revision - is retained, nothing overwritten.

## Files

```text
harness.py                  benchmark harness (task gen, pipelines, scoring, all 6 phases)
figs.py                     figure generation
predictions.json            round-1 predictions, committed before run
revisions.json              round-1 diagnoses + revised models
transfer_predictions.json   transfer predictions (with pre-declared suspected class)
transfer_revisions.json     transfer diagnoses + revised models
log/                        hidden config, per-round results, scored output, final metrics
```

## Limits

Honesty section. One model, one run, N=24. The harness author designed the tasks, so blinding rests entirely on the seeded RNG - a stronger version has one agent generate hidden defects for another. The five error classes are announced up front, which real science does not do. Tasks have crisp ground truth; wet-lab ambiguity does not. This is a pilot, not a leaderboard.

## Credit

Inspired by the autonomous-science line of work from Markus Buehler's lab at MIT. Agent under test: Claude by Anthropic.

Built by [@0maxxdev](https://x.com/0maxxdev).

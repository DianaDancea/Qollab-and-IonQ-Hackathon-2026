# Quantum Music

Quantum Music is a synth whose sound comes from quantum interference. The tone has six overtones, and each overtone gets its own tiny interferometer: one qubit, sent through H, a phase gate P(φ) and H again, then measured. The chance of reading 1 is sin²(φ/2), and that number is the overtone's volume.

A second qubit, the "marker", can keep a record of which path the first qubit took. A crossfader, θ, sets how good that record is. The better the record, the weaker the interference, and the less the sound moves. Then a quantum eraser brings the movement back without running anything new. It only sorts the shots you already have.

Demo video: (link to come)

Made for the Qollab x IonQ hackathon, Quantum Playground track.

## What you'll hear

Quantum physics doesn't let you have it both ways: once something records which path a particle took, its interference pattern goes away. In this synth the interference pattern is what makes the sound move, so you can hear it go.

There are three modes.

In `plain` mode there is no marker. Each overtone's phase is a little ahead of the one below it, so the six volumes trace out a wave pattern (loud, quiet, loud). Every frame the phases shift and the pattern slides along, which sounds a lot like a phaser pedal. θ does nothing in this mode.

In `marker` mode the marker qubit is switched on. A controlled rotation (CRY by 2θ) copies path information onto it. The pattern flattens: its visibility V drops to cos θ, while the marker's knowledge of the path, K, rises to sin θ, and V² + K² stays at 1. At θ = 90° the marker knows the path exactly, every overtone sits at 50%, and the tone holds still.

In `eraser` mode the circuit is the same, but the marker gets an extra H gate before it's measured, so its result can no longer tell the two paths apart. If you ignore the marker result, nothing changes and you hear the same thing as marker mode. If you split the shots into two piles by the marker result, each pile has its own moving pattern. At θ = 90° the two piles are exact opposites (sin²(φ/2) and cos²(φ/2)), so together they average out to the flat, still tone. The data never changed, only the way it was sorted.

After every run the console prints V for each voice next to what theory predicts, and checks V² + K² = 1 using the measured numbers.

## How to run it

1. Open this page in Chrome, Edge, Brave, Opera or Firefox 153 or newer. Safari, iPhone and iPad can't run Qollab projects.
2. Press **Run on Qollab** (top right). You don't need to sign in to use the free local simulators.
3. In **Run settings**, keep the defaults or change them. `shots` is how many times each circuit runs (1000). `theta_deg` is the crossfader in degrees: 0 means no marker, 90 means the marker knows the path exactly (90). `mode` is `plain`, `marker` or `eraser` (`eraser`). `frames` is how many steps the sweep takes, at 0.3 s each (8).
4. Pick **Built-in simulator (24q)** under *Locally Run Simulators* and press **Run**.
5. The console shows one table per voice. Each row is a frame, each column is an overtone, and the numbers are volumes in percent, with a small bar chart at the end of the row. Below the tables you get V for each voice and the V² + K² check, and then one WAV file per voice.
6. To try IonQ's simulator, run again and pick an IonQ simulator under *Remotely Run Simulators*. The whole run is a single job, which is what IonQ allows. IonQ's simulator adds noise and slows down with more shots, so try `shots` = 200 and `frames` = 6, and see how V compares with the noise-free run.

A good order to try: `plain`, then `marker` at θ = 45 and θ = 90, then `eraser` at 90. Play the three eraser files one after another. The "mixed" one holds still and the other two move.

## How it works

Each overtone at each frame is one small circuit, with one qubit in plain mode and two when there's a marker. Overtone k has phase φ = k × 60° + sweep, and the sweep goes once round the circle over the frames. With 8 frames and 6 overtones that's 48 circuits. They all go to the simulator in one `backend.run` call, because IonQ accepts only one job per run.

The measured P(1) becomes volume. Overtone k plays at P(1)/k, so higher overtones are a bit quieter, as on a plucked string, and the volume is blended smoothly from one frame to the next so there are no clicks.

To get V, the program fits the curve a − c·cos φ − s·sin φ to each overtone's volumes and takes V = √(c² + s²) / a. Using a fit means no frame has to land exactly on the loudest or quietest point.

The code is in four files:

- `main.py` is what Qollab runs. It reads the Run settings, runs the job and prints the results.
- `quantum/fringe.py` builds the circuits, holds the theory formulas, and runs a list of phases as one job.
- `quantum/synth.py` lays out the overtones and frames, works out V, writes the WAV files, and can export the numbers as JSON.
- `quantum/checks.py` has the tests. `run_all(backend)` runs all of them.

## What's new here

Complementarity and the quantum eraser are usually shown as a single curve on a plot. Here they are controls on an instrument: the crossfader is the amount of which-path information, and the eraser is a way of sorting shots that turns one still tone into two moving ones. In the hackathon's terms, we claim a novel application context and an educational contribution. Each run also tests V² + K² = 1 on its own data.

## Make it yours

The sound settings are at the top of `quantum/synth.py`: `F0` (the pitch, 220 Hz), `N_OVERTONES` (6), `SPREAD` (the phase step between overtones, which changes the timbre), `FRAME_SECONDS` and `SAMPLE_RATE`. The default Run settings are in the `main(...)` line of `main.py`, and `MAX_CIRCUITS` there caps how big one job can get. For a web front end, `spectrum_json(...)` in `quantum/synth.py` returns the measured volumes as JSON, ready for Web Audio.

## Built during the hackathon / prior work

Nothing here existed before the build window. All the code was written during it, and the first commit is from 2026-10-09 at 21:56 ET (see the git history). The only libraries used are Qiskit, NumPy and the Python standard library.

## Accessibility

You don't need to hear the sound to follow the project. Every voice is also printed as numbers (the volume of each overtone in each frame, in percent) with a bar chart next to them, and V is given as a number with a one-line explanation. Nothing depends on colour. The settings use Qollab's own Run settings form, and the project adds no custom controls.

## Local development

The local repo is the source of truth; the project runs on Qollab in the browser (Pyodide, built-in Qiskit simulator). uv is local tooling only.

No additional external imports should be added.

```sh
uv sync
uv run python -c "from main import main; main()"  # run as Qollab would (writes WAVs here)
uv run python -m pytest quantum/checks.py  # run tests
uv run ruff check . && uv run ruff format --check .  # lint + format check
```

## License

MIT (see `LICENSE`). Source: https://github.com/DianaDancea/Qollab-and-IonQ-Hackathon-2026

This effort is supported by Qollab & IonQ

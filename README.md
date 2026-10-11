# Quantum Music

A synth where every overtone is a quantum interferometer. Each overtone's volume is the measured P(1) of a one-qubit Mach-Zehnder interferometer, so the timbre of the tone is an interference pattern you can hear. A second "marker" qubit records which path was taken, and a crossfader θ sets how much it knows: the more it knows, the flatter every fringe and the stiller the sound. A quantum eraser (reading the marker in the X basis and sorting the shots by the marker bit) brings the moving sound back, as two voices in antiphase.

Demo video: (link to come)

Built for the Qollab x IonQ hackathon, Quantum Playground track.

## What it shows

Wave-particle complementarity, made audible. Interference only happens when nothing records which path was taken. In this synth, interference is what moves the sound, so you can hear the which-path record kill it.

- **Plain (θ unused):** each overtone k has phase φ_k = k · spread + sweep, so the spectrum is a comb of fringes (the shape a phaser pedal makes), and the sweep slides it. You hear a phaser.
- **Marker:** the marker qubit is entangled with the path by a controlled-RY(2θ). The fringe visibility drops to V = cos θ, while the which-path knowledge is K = sin θ, so V² + K² = 1. At θ = 90° every overtone sits at 1/2 and the tone stops moving.
- **Eraser:** the same circuit, with the marker read in the X basis. Ignoring the marker bit, it sounds exactly like marker mode (at θ = 90°, a still tone). Sorting the very same shots by the marker bit gives two voices whose combs are in antiphase (sin²(φ/2) and cos²(φ/2) at θ = 90°). Each one moves again, and together they add back to the still tone. Erasing never changes the data, only how you sort it.

Every run measures V for every voice, prints it next to theory, and checks V² + K² = 1 from the data.

## How to run it

1. Open this page in Chrome, Edge, Brave, Opera or Firefox 153+. Safari and iPhone/iPad cannot run Qollab projects.
2. Press **Run on Qollab** (top right). No sign-in is needed for the free local simulators.
3. Under **Run settings**, keep the defaults or change them: **shots** per circuit (1000), **theta_deg**, the crossfader in degrees (0 = no marker, 90 = full which-path record), **mode** (`plain`, `marker` or `eraser`) and **frames**, the number of sweep steps (8, at 0.3 s each).
4. Pick **Built-in simulator (24q)** under *Locally Run Simulators* and press **Run**.
5. The console prints, for each voice, a table of P(1) per overtone per frame, with a bar graph of the spectrum. Then it prints the measured visibility V of each voice next to theory, and V² + K². Last come the WAV files, one per voice.
6. To use IonQ's simulator, run again and pick an IonQ simulator under *Remotely Run Simulators*. The project sends exactly one job per run (all frames and overtones in one `backend.run`). IonQ's noise simulation is slower with more shots, so try **shots** = 200 and **frames** = 6 there, and compare V with the ideal run.

Try this sequence: `plain`, then `marker` at θ = 45 and 90, then `eraser` at 90. Listen to the three eraser files back to back.

## How it works

| concept | circuit | what you hear |
|---|---|---|
| Interference | H, P(φ), H, measure on the path qubit; P(1) = sin²(φ/2) | an overtone's volume |
| A timbre | one interferometer per overtone k, φ_k = k · spread + sweep | a comb-shaped spectrum |
| Movement | the sweep advances every frame | a phaser sweep |
| Which-path record | CRY(2θ) from the path qubit onto the marker | the sweep fades as θ grows |
| Quantum eraser | H on the marker before measuring, shots sorted by the marker bit | two moving voices in antiphase |

The volume of overtone k is P(1) / k (the 1/k roll-off of a plucked string), interpolated between frames so nothing clicks. Visibility is fitted per overtone by least squares (P = a − c cos φ − s sin φ, V = √(c² + s²) / a), so it does not depend on a frame landing on the exact peak.

Everything goes into one job: frames × overtones circuits (48 by default), each with 1 or 2 qubits, in a single `backend.run`. IonQ backends allow only one job per run.

Files:

- `main.py`: the entry point Qollab runs (`main()` and its Run settings form).
- `quantum/fringe.py`: the interferometer circuits, the closed-form theory, and the one-job phase sweep.
- `quantum/synth.py`: the overtone grid, the one-job spectrum measurement, visibility, the WAV renderer and a JSON export.
- `quantum/checks.py`: exact (statevector) and shot-based checks; `run_all(backend)` runs them all.

## What's new here

We claim a **novel application context** and an **original educational contribution**. Complementarity and the quantum eraser are usually shown as one fringe on a plot. Here they are a playable synthesizer parameter: the crossfader is literally which-path knowledge, and the eraser is a way of sorting shots that turns one still tone into two moving ones. Each run also measures the complementarity relation V² + K² = 1 from its own data.

## Make it yours

- `quantum/synth.py`: `F0` (the pitch), `N_OVERTONES`, `SPREAD` (the comb spacing, i.e. the timbre), `FRAME_SECONDS` and `SAMPLE_RATE`.
- `main.py`: the Run settings defaults in the `main(...)` signature, and `MAX_CIRCUITS`.
- `quantum/synth.py` `spectrum_json(...)` returns the measured spectrum as JSON, ready for a Web Audio front end.

## Built during the hackathon / prior work

Nothing existed before the build window: all code in this repository was written during it (first commit 2026-10-09 21:56 ET; see the git history). It uses only Qiskit, NumPy and the Python standard library.

## Accessibility

Every sound has a text alternative: the console prints each voice's spectrum as numbers (P(1) in %, per overtone and frame) with a bar graph beside them, and states the visibility of each voice in words and numbers. Nothing depends on colour. The settings are Qollab's own Run settings form; the project adds no custom controls. Audio is optional: the physics can be read entirely from the text.

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

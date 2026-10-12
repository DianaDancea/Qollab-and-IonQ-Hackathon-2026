# Quantum Music

A synth where each overtone's volume is P(1) from a one-qubit interferometer. A marker qubit records which path was taken (crossfader θ): the more it knows, the stiller the sound. The quantum eraser sorts the shots by the marker bit and the movement comes back.

Demo video: (link to come)

Built for the Qollab x IonQ hackathon (Quantum Playground).

## Run it

Press **Run on Qollab**, pick **Built-in simulator**, press **Run** (Chrome, Edge or Firefox; not Safari). Settings: `shots`, `theta_deg` (0 = no marker, 90 = full marker), `mode` (`plain`, `marker`, `eraser`), `frames`.

The console prints each voice's overtone volumes, the fringe visibility V against theory, and a WAV per voice. Try `eraser` at 90: "All shots" stays flat, the two marker halves move.

On IonQ's simulator the whole run is one job; try `shots` = 200.

## What's new

Complementarity (V² + K² = 1) and the quantum eraser as something you can hear and play with, checked against theory on every run.

## Notes

Written during the hackathon window. Uses only Qiskit, NumPy and the standard library. Every sound is also printed as numbers, so nothing needs hearing.

## Local development

```sh
uv sync
uv run python -c "from main import main; main()"
uv run python -m pytest quantum/checks.py
uv run ruff check . && uv run ruff format --check .
```

No additional external imports should be added.

## License

MIT (see `LICENSE`).

This effort is supported by Qollab & IonQ

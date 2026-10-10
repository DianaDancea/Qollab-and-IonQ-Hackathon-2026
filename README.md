# Quantum Music

Starting Idea: 
A synth where each overtone is a one-qubit Mach-Zehnder interferometer
($H$, P($\phi$), $H$, measure). P(1) = $\sin^2(\phi/2)$ sets that overtone's volume.
A second "marker" qubit records which path was taken; a crossfader $\theta$ sets
how much, and a quantum eraser (marker read in the X basis, shots sorted by
marker bit) brings the fringe back.

Built for the Qollab x IonQ hackathon ("Quantum Playground").

This effort is supported by Qollab & IonQ

## Local development

The local repo is the source of truth; the project runs on Qollab in the
browser (Pyodide, built-in Qiskit simulator). uv is local tooling only.

No additional external imports should be added.

```sh
uv sync
uv run python -m pytest quantum/checks.py # run tests
uv run ruff check . && uv run ruff format --check . # lint + format check.py
```

## TODO

- ...

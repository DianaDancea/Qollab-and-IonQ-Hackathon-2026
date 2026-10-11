"""Quantum Music. Qollab calls main() with the values from the Run settings form.

Each overtone's volume is the measured P(1) of its own one-qubit interferometer.
A marker qubit (crossfader theta) can record which path the qubit took. The more
it knows, the flatter the pattern and the stiller the sound. The eraser splits
the same shots by the marker result, and each half can move again.

The whole run is one backend.run call, because IonQ allows only one job per run.
"""

import numpy as np

from quantum.fringe import MODES
from quantum.synth import (
    F0,
    FRAME_SECONDS,
    N_OVERTONES,
    fringe_visibility,
    measure_spectrum,
    render_wav,
    voices,
)

VOICE_NAMES = {
    "mixed": "All shots",
    "m0": "Marker read 0",
    "m1": "Marker read 1",
}
MAX_CIRCUITS = 400  # frames * overtones; keeps an IonQ simulator run reasonable
BARS = " ▁▂▃▄▅▆▇█"


def _backend():
    """Qollab's pre-created `backend` (the Select QPU choice); a local simulator elsewhere."""
    try:
        return backend  # a global Qollab defines before running main
    except NameError:
        from qiskit.providers.basic_provider import BasicSimulator

        return BasicSimulator()


def _bar(levels):
    return "".join(" " if np.isnan(x) else BARS[round(x * (len(BARS) - 1))] for x in levels)


def _print_voice(name, levels):
    """The sound as text: one row per frame, one column per overtone."""
    print(
        f"\n{VOICE_NAMES[name]}: volume of each overtone in %, one row per frame "
        f"(overtones 1 to {levels.shape[1]}, left to right)"
    )
    for i, row in enumerate(levels):
        cells = " ".join("  -" if np.isnan(x) else f"{100 * x:3.0f}" for x in row)
        print(f"  frame {i + 1:2d} | {cells} | {_bar(row)}")


def _offer_file(name, data):
    """Write a file and hand it to the Qollab console if it can take it."""
    with open(name, "wb") as f:
        f.write(data)
    try:
        from js import sendFile  # Qollab console download (absent off Qollab)
    except ImportError:
        print(f"  saved {name} ({len(data) // 1024} KB)")
        return
    try:
        sendFile(name)
        print(f"  {name} is in the console above ({len(data) // 1024} KB)")
    except Exception as err:  # noqa: BLE001  (a JS error must not lose the results)
        print(f"  {name} was saved, but the console couldn't show it ({err})")


def main(shots: int = 1000, theta_deg: float = 90.0, mode: str = "eraser", frames: int = 8):
    mode = mode.strip().lower()
    if mode not in MODES:
        print(f"Unknown mode {mode!r}. Use plain, marker or eraser. Running eraser instead.")
        mode = "eraser"
    shots = max(1, int(shots))
    frames = min(max(3, int(frames)), MAX_CIRCUITS // N_OVERTONES)
    theta = np.radians(theta_deg)

    print("Quantum Music: each overtone's volume is the P(1) of its own small interferometer.")
    crossfader = "" if mode == "plain" else f", crossfader theta = {theta_deg:g} degrees"
    print(
        f"Mode: {mode}{crossfader}. Running {frames * N_OVERTONES} circuits "
        f"({frames} frames x {N_OVERTONES} overtones), {shots} shots each, as one job."
    )

    spectrum = measure_spectrum(_backend(), frames, theta, mode, shots)

    played = voices(spectrum)
    for name, levels in played.items():
        _print_voice(name, levels)

    print("\nHow much each voice moves. V = 1 is a full sweep, V = 0 means the tone holds still.")
    theory = {"mixed": "expected_mixed", "m0": "expected_m0", "m1": "expected_m1"}
    for name, levels in played.items():
        got = fringe_visibility(levels, spectrum["phi"])
        want = fringe_visibility(spectrum[theory[name]], spectrum["phi"])
        print(f"  {VOICE_NAMES[name]:14s} V = {got:.2f}  (theory says {want:.2f})")
    if mode != "plain":
        v = fringe_visibility(spectrum["mixed"], spectrum["phi"])
        k = abs(np.sin(theta))
        print(
            f"  The marker's knowledge of the path is K = {k:.2f}. "
            f"For all shots, V² + K² = {v**2 + k**2:.2f} (theory says 1)."
        )
    if mode == "eraser":
        print(
            "  Splitting the shots by the marker result can bring the movement back. "
            "At theta = 90 degrees both halves move fully, in opposite directions. "
            "Put back together, the two halves always give the all-shots tone."
        )

    print(
        f"\nSound: a {F0:g} Hz tone, {frames * FRAME_SECONDS:.1f} seconds per voice, as WAV files"
    )
    for name, levels in played.items():
        _offer_file(f"quantum_music_{mode}_{name}.wav", render_wav(levels))

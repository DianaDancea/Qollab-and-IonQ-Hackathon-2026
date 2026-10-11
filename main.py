"""Quantum Music: hear complementarity. Qollab runs main() with the Run settings form.

Each overtone of a tone is a one-qubit Mach-Zehnder interferometer, and the
measured P(1) is its volume. The marker qubit (crossfader theta) records which
path was taken; the more it knows, the flatter every fringe and the stiller the
sound. The quantum eraser sorts the same shots by the marker bit and the
moving sound comes back, as two voices in antiphase.

The whole run is ONE backend.run call, as IonQ's simulators require.
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
    "mixed": "all shots (marker ignored)",
    "m0": "eraser, marker = 0",
    "m1": "eraser, marker = 1",
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
    """The text form of the sound: one line per frame, one column per overtone."""
    print(f"\n{VOICE_NAMES[name]}: P(1) in % per overtone (columns 1..{levels.shape[1]})")
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
        print(f"  {name}: in the console above ({len(data) // 1024} KB)")
    except Exception as err:  # noqa: BLE001  (a JS error must not lose the results)
        print(f"  {name}: saved, but the console could not take it ({err})")


def main(shots: int = 1000, theta_deg: float = 90.0, mode: str = "eraser", frames: int = 8):
    mode = mode.strip().lower()
    if mode not in MODES:
        print(f"mode must be one of {', '.join(MODES)}; got {mode!r}. Using eraser.")
        mode = "eraser"
    shots = max(1, int(shots))
    frames = min(max(3, int(frames)), MAX_CIRCUITS // N_OVERTONES)
    theta = np.radians(theta_deg)

    print("Quantum Music: each overtone is a Mach-Zehnder interferometer, volume = P(1).")
    crossfader = "" if mode == "plain" else f", crossfader theta = {theta_deg:g} deg"
    print(
        f"mode = {mode}{crossfader}, {frames} frames x {N_OVERTONES} overtones = "
        f"{frames * N_OVERTONES} circuits, {shots} shots each, in one job."
    )

    spectrum = measure_spectrum(_backend(), frames, theta, mode, shots)

    played = voices(spectrum)
    for name, levels in played.items():
        _print_voice(name, levels)

    print("\nHow much the sound moves: fringe visibility V (1 = full sweep, 0 = still tone)")
    theory = {"mixed": "expected_mixed", "m0": "expected_m0", "m1": "expected_m1"}
    for name, levels in played.items():
        got = fringe_visibility(levels, spectrum["phi"])
        want = fringe_visibility(spectrum[theory[name]], spectrum["phi"])
        print(f"  {VOICE_NAMES[name]:28s} V = {got:.2f} (theory {want:.2f})")
    if mode != "plain":
        v = fringe_visibility(spectrum["mixed"], spectrum["phi"])
        k = abs(np.sin(theta))
        print(
            f"  Which-path knowledge K = |sin(theta)| = {k:.2f}. Complementarity: "
            f"V^2 + K^2 = {v**2 + k**2:.2f} (theory 1)."
        )
    if mode == "eraser":
        print(
            "  The eraser reads the marker in a basis that cannot tell the paths apart. "
            "At theta = 90 deg both halves move fully again, in antiphase; at any theta "
            "the halves add back to the unsorted tone."
        )

    print(f"\nAudio: {F0:g} Hz tone, {frames * FRAME_SECONDS:.1f} s per voice, 16-bit WAV")
    for name, levels in played.items():
        _offer_file(f"quantum_music_{mode}_{name}.wav", render_wav(levels))

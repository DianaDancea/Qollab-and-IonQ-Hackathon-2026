"""Quantum Music. Qollab calls main() with the Run settings."""

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

VOICE_NAMES = {"mixed": "All shots", "m0": "Marker read 0", "m1": "Marker read 1"}
MAX_CIRCUITS = 400  # cap so IonQ runs stay sane
BARS = " ▁▂▃▄▅▆▇█"


def _backend():
    """Qollab's backend, or BasicSimulator locally."""
    try:
        return backend  # set by Qollab
    except NameError:
        from qiskit.providers.basic_provider import BasicSimulator

        return BasicSimulator()


def _bar(levels):
    return "".join(" " if np.isnan(x) else BARS[round(x * (len(BARS) - 1))] for x in levels)


def _print_voice(name, levels):
    print(f"\n{VOICE_NAMES[name]} (volume %, rows = frames, cols = overtones)")
    for i, row in enumerate(levels):
        cells = " ".join("  -" if np.isnan(x) else f"{100 * x:3.0f}" for x in row)
        print(f"  {i + 1:2d} | {cells} | {_bar(row)}")


def _offer_file(name, data):
    with open(name, "wb") as f:
        f.write(data)
    try:
        from js import sendFile  # Qollab only
    except ImportError:
        print(f"  saved {name}")
        return
    try:
        sendFile(name)
        print(f"  {name}")
    except Exception as err:  # noqa: BLE001
        print(f"  {name}: download failed ({err})")


def main(shots: int = 1000, theta_deg: float = 90.0, mode: str = "eraser", frames: int = 8):
    mode = mode.strip().lower()
    if mode not in MODES:
        print(f"unknown mode {mode!r}, using eraser")
        mode = "eraser"
    shots = max(1, int(shots))
    frames = min(max(3, int(frames)), MAX_CIRCUITS // N_OVERTONES)
    theta = np.radians(theta_deg)

    crossfader = "" if mode == "plain" else f", theta {theta_deg:g} deg"
    print(f"Quantum Music: {mode}{crossfader}, {frames * N_OVERTONES} circuits, {shots} shots")

    spectrum = measure_spectrum(_backend(), frames, theta, mode, shots)  # one job
    played = voices(spectrum)
    for name, levels in played.items():
        _print_voice(name, levels)

    print("\nVisibility (1 = moving, 0 = still)")
    theory = {"mixed": "expected_mixed", "m0": "expected_m0", "m1": "expected_m1"}
    for name, levels in played.items():
        got = fringe_visibility(levels, spectrum["phi"])
        want = fringe_visibility(spectrum[theory[name]], spectrum["phi"])
        print(f"  {VOICE_NAMES[name]:14s} V = {got:.2f}  (theory {want:.2f})")
    if mode != "plain":
        v = fringe_visibility(spectrum["mixed"], spectrum["phi"])
        k = abs(np.sin(theta))
        print(f"  K = {k:.2f}, V² + K² = {v**2 + k**2:.2f} (theory 1)")

    print(f"\nWAVs ({F0:g} Hz, {frames * FRAME_SECONDS:.1f} s each)")
    for name, levels in played.items():
        _offer_file(f"quantum_music_{mode}_{name}.wav", render_wav(levels))

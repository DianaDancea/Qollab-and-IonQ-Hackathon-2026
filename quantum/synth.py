"""Turn interference patterns into sound, one pattern per overtone.

Overtone k (frequency k * F0) has its own interferometer with phase
phi_k = k * spread + sweep, and plays at volume P(1). Read across the
overtones, the volumes go up and down like a wave, much like the notches a
phaser pedal puts in a sound. Each frame moves the sweep along, and you hear
the pattern slide.

The marker qubit is the crossfader. At theta = 0 nothing records the path,
the patterns are full size and the sound moves. At theta = pi/2 the marker
knows the path, every overtone sits at 1/2 and the sound stops moving. The
eraser splits the same shots by the marker result into two voices that are
opposites of each other: each one moves, and together they average back to the
still tone.

Only numpy, qiskit (through fringe.py) and the standard library are used, so
this runs in Pyodide on Qollab. Every frame and overtone goes into ONE
backend.run call.
"""

import io
import json
import wave

import numpy as np

from .fringe import _check_mode, run_phases

F0 = 220.0  # fundamental, Hz (A3)
N_OVERTONES = 6
SPREAD = np.pi / 3  # phase step between neighbouring overtones
SAMPLE_RATE = 22050
FRAME_SECONDS = 0.3
FADE_SECONDS = 0.01


def phase_grid(n_frames, n_overtones=N_OVERTONES, spread=SPREAD):
    """Phases, shape (n_frames, n_overtones): phi = k * spread + sweep.

    The sweep runs once round [0, 2*pi) over the frames, so every overtone
    passes through a whole fringe.
    """
    sweeps = np.linspace(0.0, 2 * np.pi, n_frames, endpoint=False)
    k = np.arange(1, n_overtones + 1)
    return (k[None, :] * spread + sweeps[:, None]) % (2 * np.pi)


def measure_spectrum(
    backend, n_frames=8, theta=0.0, mode="plain", shots=1000, n_overtones=N_OVERTONES
):
    """Measure every overtone's volume at every frame with ONE backend.run.

    Returns a dict of arrays shaped (n_frames, n_overtones):
    "phi", "mixed" (P(1) ignoring the marker) and "expected_mixed".
    Eraser mode adds "m0" and "m1" (P(1) given marker bit 0 or 1, NaN for an
    empty subset), "n_m0" and "n_m1" (shots in each subset) and their theory
    "expected_m0" and "expected_m1".
    """
    _check_mode(mode)
    phis = phase_grid(n_frames, n_overtones)
    rows = run_phases(backend, phis.ravel(), shots, theta, mode)
    shape = phis.shape

    def grid(key):
        values = [np.nan if row[key] is None else row[key] for row in rows]
        return np.array(values, dtype=float).reshape(shape)

    out = {
        "mode": mode,
        "theta": float(theta),
        "shots": shots,
        "phi": phis,
        "mixed": grid("measured"),
        "expected_mixed": grid("expected"),
    }
    if mode == "eraser":
        out["m0"] = grid("measured_p1_m0")
        out["m1"] = grid("measured_p1_m1")
        out["n_m0"] = grid("measured_n_m0")
        out["n_m1"] = grid("measured_n_m1")
        out["expected_m0"] = grid("expected_m0")
        out["expected_m1"] = grid("expected_m1")
    return out


def voices(spectrum):
    """The voices a spectrum can play: name -> volumes (n_frames, n_overtones)."""
    names = ["mixed", "m0", "m1"] if spectrum["mode"] == "eraser" else ["mixed"]
    return {name: spectrum[name] for name in names}


def fringe_visibility(levels, phis):
    """Fringe visibility V, from a least-squares fit, averaged over the overtones.

    Every fringe here (unsorted or marker-sorted) has the form
    P = a - c cos(phi) - s sin(phi), so fitting a, c, s per overtone gives
    V = sqrt(c^2 + s^2) / a without needing a frame at the exact peak or dip.
    NaN entries (empty marker subsets) are left out; an overtone needs three
    points for the fit.
    """
    levels = np.asarray(levels, dtype=float)
    vs = []
    for col in range(levels.shape[1]):
        ok = ~np.isnan(levels[:, col])
        if ok.sum() < 3:
            continue
        phi = phis[ok, col]
        design = np.column_stack([np.ones(len(phi)), np.cos(phi), np.sin(phi)])
        a, c, s = np.linalg.lstsq(design, levels[ok, col], rcond=None)[0]
        vs.append(min(1.0, float(np.hypot(c, s) / a)) if a > 0 else 0.0)
    return float(np.mean(vs)) if vs else float("nan")


def render_wav(levels, f0=F0, frame_seconds=FRAME_SECONDS, sample_rate=SAMPLE_RATE):
    """Additive synthesis: overtone k at k * f0 with volume levels[:, k-1] / k.

    levels has shape (n_frames, n_overtones) with values in [0, 1]; NaN plays
    as silence. Volumes are interpolated between frame centres so nothing
    clicks, and the 1/k roll-off is the natural one of a plucked string.
    Returns the bytes of a 16-bit mono WAV file.
    """
    levels = np.nan_to_num(np.asarray(levels, dtype=float), nan=0.0).clip(0.0, 1.0)
    n_frames, n_overtones = levels.shape
    n_samples = round(n_frames * frame_seconds * sample_rate)
    t = np.arange(n_samples) / sample_rate
    centres = (np.arange(n_frames) + 0.5) * frame_seconds

    k = np.arange(1, n_overtones + 1)
    signal = np.zeros(n_samples)
    for i, harmonic in enumerate(k):
        if harmonic * f0 >= sample_rate / 2:  # above Nyquist: would alias
            continue
        volume = np.interp(t, centres, levels[:, i]) / harmonic
        signal += volume * np.sin(2 * np.pi * harmonic * f0 * t)
    # Fixed scale (not per file) so voices keep their relative loudness.
    signal /= np.sum(1.0 / k)

    fade = min(int(FADE_SECONDS * sample_rate), n_samples // 2)
    if fade:
        ramp = np.linspace(0.0, 1.0, fade)
        signal[:fade] *= ramp
        signal[-fade:] *= ramp[::-1]

    pcm = (signal * 32767 * 0.9).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return buffer.getvalue()


def spectrum_json(spectrum):
    """The spectrum as a JSON string (NaN -> null), e.g. for a Web Audio front end."""

    def plain(value):
        if isinstance(value, np.ndarray):
            return [[None if np.isnan(x) else float(x) for x in row] for row in value]
        return value

    return json.dumps(
        {
            "f0": F0,
            "frame_seconds": FRAME_SECONDS,
            **{key: plain(value) for key, value in spectrum.items()},
        }
    )

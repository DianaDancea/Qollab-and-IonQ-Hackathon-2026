"""Fringes -> sound. Overtone k has phase k*spread + sweep, volume = P(1).

One backend.run for everything (IonQ rule).
"""

import io
import json
import wave

import numpy as np

from .fringe import _check_mode, run_phases

F0 = 220.0  # Hz
N_OVERTONES = 6
SPREAD = np.pi / 3  # phase step per overtone
SAMPLE_RATE = 22050
FRAME_SECONDS = 0.3
FADE_SECONDS = 0.01


def phase_grid(n_frames, n_overtones=N_OVERTONES, spread=SPREAD):
    """(frames, overtones) phases; sweep does one lap over the frames."""
    sweeps = np.linspace(0.0, 2 * np.pi, n_frames, endpoint=False)
    k = np.arange(1, n_overtones + 1)
    return (k[None, :] * spread + sweeps[:, None]) % (2 * np.pi)


def measure_spectrum(
    backend, n_frames=8, theta=0.0, mode="plain", shots=1000, n_overtones=N_OVERTONES
):
    """P(1) for every frame x overtone, one job. Eraser adds m0/m1 (NaN if empty)."""
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
    """name -> volumes."""
    names = ["mixed", "m0", "m1"] if spectrum["mode"] == "eraser" else ["mixed"]
    return {name: spectrum[name] for name in names}


def fringe_visibility(levels, phis):
    """Mean V over overtones, from a fit P = a - c cos(phi) - s sin(phi)."""
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
    """Additive synth -> 16-bit mono WAV bytes. Volume = level / k, NaN = silent."""
    levels = np.nan_to_num(np.asarray(levels, dtype=float), nan=0.0).clip(0.0, 1.0)
    n_frames, n_overtones = levels.shape
    n_samples = round(n_frames * frame_seconds * sample_rate)
    t = np.arange(n_samples) / sample_rate
    centres = (np.arange(n_frames) + 0.5) * frame_seconds

    k = np.arange(1, n_overtones + 1)
    signal = np.zeros(n_samples)
    for i, harmonic in enumerate(k):
        if harmonic * f0 >= sample_rate / 2:  # aliasing
            continue
        volume = np.interp(t, centres, levels[:, i]) / harmonic
        signal += volume * np.sin(2 * np.pi * harmonic * f0 * t)
    # fixed scale so voices stay comparable
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
    """Spectrum as JSON (NaN -> null), for a web front end."""

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

"""Checks for quantum/fringe.py and quantum/synth.py: exact and statistical.

The exact tests have no randomness and pin the physics: they compare the
circuits' exact probabilities to the closed-form theory. The shot tests check
the parts exact tests cannot: backend.run, the counts parsing and bit order,
and the rows that run_sweep returns.

Run locally from the project root:  python -m pytest quantum/checks.py
On Qollab, the Self-check button calls run_all(backend).
"""

import io
import json
import wave
from math import pi

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from .fringe import (
    expected_p1,
    expected_p1_given_marker,
    fringe_circuit,
    p1_by_marker,
    p1_from_counts,
    run_sweep,
)
from .synth import (
    FRAME_SECONDS,
    N_OVERTONES,
    SAMPLE_RATE,
    fringe_visibility,
    measure_spectrum,
    phase_grid,
    render_wav,
    spectrum_json,
)

PHIS = [2 * pi * k / 12 for k in range(13)]
THETAS = [0.0, pi / 8, pi / 4, 3 * pi / 8, pi / 2]
EXACT_TOL = 1e-9
SHOT_TOL = 0.03  # about 4 sigma at 4000 shots (sigma <= sqrt(0.25 / 4000) = 0.008)


# ---------- exact helpers (statevector, no shots) ----------


def _probabilities(phi, theta, mode):
    """Exact joint probabilities. Index = marker * 2 + qubit0 (qubit 0 is the low bit)."""
    qc = fringe_circuit(phi, theta, mode)
    qc.remove_final_measurements()
    return Statevector(qc).probabilities()


def exact_p1(phi, theta=0.0, mode="plain"):
    """Exact P(qubit 0 = 1), ignoring the marker."""
    qc = fringe_circuit(phi, theta, mode)
    qc.remove_final_measurements()
    return float(Statevector(qc).probabilities([0])[1])


def exact_p1_given_marker(phi, theta, marker_bit):
    """Exact P(qubit 0 = 1 | eraser marker = marker_bit) and P(marker = marker_bit)."""
    probs = _probabilities(phi, theta, "eraser")
    p_marker = probs[2 * marker_bit] + probs[2 * marker_bit + 1]
    return float(probs[2 * marker_bit + 1] / p_marker), float(p_marker)


def exact_path_knowledge(theta):
    """K = sqrt(P(marker = 1 | path 1)): how well the marker tells the path."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cry(2 * theta, 0, 1)
    probs = Statevector(qc).probabilities()  # index = marker * 2 + qubit0
    p_path1 = probs[1] + probs[3]
    return float(np.sqrt(probs[3] / p_path1))


# ---------- exact tests ----------


def test_plain_fringe_matches_theory():
    for phi in PHIS:
        assert abs(exact_p1(phi) - expected_p1(phi)) < EXACT_TOL
        assert abs(exact_p1(phi) - np.sin(phi / 2) ** 2) < EXACT_TOL


def test_fringe_endpoints():
    assert abs(exact_p1(0.0)) < EXACT_TOL  # silent at phi = 0
    assert abs(exact_p1(pi) - 1.0) < EXACT_TOL  # loudest at phi = pi


def test_full_marker_flattens_fringe():
    for phi in PHIS:
        assert abs(exact_p1(phi, pi / 2, "marker") - 0.5) < EXACT_TOL


def test_crossfader_formula():
    for theta in THETAS:
        for phi in PHIS:
            want = 0.5 * (1 - np.cos(theta) * np.cos(phi))
            assert abs(exact_p1(phi, theta, "marker") - want) < EXACT_TOL
            assert abs(expected_p1(phi, theta, "marker") - want) < EXACT_TOL


def test_zero_theta_marker_is_plain_fringe():
    for phi in PHIS:
        assert abs(exact_p1(phi, 0.0, "marker") - exact_p1(phi)) < EXACT_TOL


def test_duality_relation():
    """V^2 + K^2 = 1 at every crossfader position."""
    for theta in THETAS:
        p = [exact_p1(phi, theta, "marker") for phi in PHIS]
        visibility = (max(p) - min(p)) / (max(p) + min(p))
        knowledge = exact_path_knowledge(theta)
        assert abs(visibility**2 + knowledge**2 - 1.0) < 1e-9


def test_unsorted_eraser_matches_marker():
    for theta in THETAS:
        for phi in PHIS:
            assert abs(exact_p1(phi, theta, "eraser") - exact_p1(phi, theta, "marker")) < EXACT_TOL


def test_eraser_sorted_fringes_at_full_marker():
    """At theta = pi/2: sin^2(phi/2) for marker 0, cos^2(phi/2) for marker 1."""
    for phi in PHIS:
        p0, _ = exact_p1_given_marker(phi, pi / 2, 0)
        p1, _ = exact_p1_given_marker(phi, pi / 2, 1)
        assert abs(p0 - np.sin(phi / 2) ** 2) < EXACT_TOL
        assert abs(p1 - np.cos(phi / 2) ** 2) < EXACT_TOL


def test_eraser_sorted_formula_all_theta():
    for theta in THETAS:
        for phi in PHIS:
            for m in (0, 1):
                got, _ = exact_p1_given_marker(phi, theta, m)
                assert abs(got - expected_p1_given_marker(phi, m, theta)) < EXACT_TOL


def test_eraser_halves_recombine_to_unsorted():
    """Sorting loses nothing: the weighted halves sum to the unsorted fringe."""
    for theta in THETAS:
        for phi in PHIS:
            total = 0.0
            weight = 0.0
            for m in (0, 1):
                p, w = exact_p1_given_marker(phi, theta, m)
                total += w * p
                weight += w
            assert abs(weight - 1.0) < EXACT_TOL
            assert abs(total - expected_p1(phi, theta, "eraser")) < EXACT_TOL


def test_full_marker_eraser_halves_are_antiphase():
    for phi in PHIS:
        p0, _ = exact_p1_given_marker(phi, pi / 2, 0)
        p1, _ = exact_p1_given_marker(phi, pi / 2, 1)
        assert abs(p0 + p1 - 1.0) < EXACT_TOL  # sin^2 + cos^2


# ---------- parsing and validation tests (no simulator needed) ----------


def test_p1_from_counts_bit_order():
    # Keys read right to left: the last character is qubit 0.
    assert p1_from_counts({"01": 100}, 100) == 1.0
    assert p1_from_counts({"10": 100}, 100) == 0.0
    assert p1_from_counts({"1": 30, "0": 70}, 100) == 0.3
    assert p1_from_counts({"1 1": 100}, 100) == 1.0  # spaces between registers


def test_p1_by_marker_sorting():
    # Key is "marker qubit0": the first character is the marker.
    out = p1_by_marker({"00": 10, "01": 20, "10": 30, "11": 40})
    assert out["n_m0"] == 30 and out["n_m1"] == 70
    assert abs(out["p1_m0"] - 20 / 30) < 1e-12
    assert abs(out["p1_m1"] - 40 / 70) < 1e-12


def test_p1_by_marker_empty_subset():
    out = p1_by_marker({"00": 5, "01": 5})
    assert out["p1_m1"] is None and out["n_m1"] == 0


def test_bad_mode_and_marker_bit_raise():
    for bad in (
        lambda: fringe_circuit(0.0, 0.0, "nope"),
        lambda: expected_p1(0.0, 0.0, "nope"),
        lambda: expected_p1_given_marker(0.0, 2),
    ):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


# ---------- synth tests (no simulator needed) ----------


def test_phase_grid_shape_and_range():
    phis = phase_grid(8)
    assert phis.shape == (8, N_OVERTONES)
    assert phis.min() >= 0.0 and phis.max() < 2 * pi


def test_visibility_of_theory_follows_crossfader():
    phis = phase_grid(4)  # the fit needs no frame at the exact peak or dip
    for theta in THETAS:
        levels = np.vectorize(lambda phi, t=theta: expected_p1(phi, t, "marker"))(phis)
        assert abs(fringe_visibility(levels, phis) - np.cos(theta)) < EXACT_TOL


def test_render_wav_is_valid_and_silent_at_zero():
    for levels in (np.zeros((4, N_OVERTONES)), np.full((4, N_OVERTONES), 0.5)):
        with wave.open(io.BytesIO(render_wav(levels))) as wav:
            assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
            assert wav.getframerate() == SAMPLE_RATE
            assert wav.getnframes() == round(4 * FRAME_SECONDS * SAMPLE_RATE)
            pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
        loud = np.abs(pcm).max()
        assert loud == 0 if not levels.any() else 0 < loud < 32767


def test_render_wav_treats_nan_as_silence():
    with wave.open(io.BytesIO(render_wav(np.full((3, N_OVERTONES), np.nan)))) as wav:
        assert not np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").any()


# ---------- statistical test (shots on a backend) ----------


def _rows(raw):
    """run_sweep returns a JSON string: a list of rows, or {"rows": [...]}."""
    data = json.loads(raw)
    return data["rows"] if isinstance(data, dict) else data


def test_shots_match_theory(backend=None, shots=4000):
    if backend is None:  # local pytest run: no Qollab backend global
        from qiskit.providers.basic_provider import BasicSimulator

        backend = BasicSimulator()
    for mode, theta in (
        ("plain", 0.0),
        ("marker", pi / 4),
        ("marker", pi / 2),
        ("eraser", pi / 2),
    ):
        rows = _rows(run_sweep(backend, n_points=13, shots=shots, theta=theta, mode=mode))
        assert len(rows) == 13
        for row in rows:
            assert abs(row["measured"] - row["expected"]) < SHOT_TOL, (mode, theta, row)
            if mode == "eraser":
                for m in (0, 1):
                    n = row[f"measured_n_m{m}"]
                    if n >= 200:  # skip tiny subsets; tolerance is 4 sigma for n shots
                        tol = 4 * (0.25 / n) ** 0.5
                        assert abs(row[f"measured_p1_m{m}"] - row[f"expected_m{m}"]) < tol, row


class _CountingBackend:
    """Wraps a backend and counts backend.run calls (IonQ allows one per run)."""

    def __init__(self, backend):
        self.backend = backend
        self.runs = 0

    def __getattr__(self, name):
        return getattr(self.backend, name)

    def run(self, *args, **kwargs):
        self.runs += 1
        return self.backend.run(*args, **kwargs)


def test_spectrum_is_one_job_and_matches_theory(backend=None, shots=4000):
    if backend is None:
        from qiskit.providers.basic_provider import BasicSimulator

        backend = BasicSimulator()
    counting = _CountingBackend(backend)
    spectrum = measure_spectrum(counting, n_frames=4, theta=pi / 2, mode="eraser", shots=shots)
    assert counting.runs == 1
    assert spectrum["mixed"].shape == (4, N_OVERTONES)
    assert np.abs(spectrum["mixed"] - spectrum["expected_mixed"]).max() < SHOT_TOL
    for m in ("m0", "m1"):
        tol = 4 * (0.25 / spectrum[f"n_{m}"].min()) ** 0.5
        assert np.abs(spectrum[m] - spectrum[f"expected_{m}"]).max() < tol
    assert len(json.loads(spectrum_json(spectrum))["m0"]) == 4


SHOT_TESTS = ("test_shots_match_theory", "test_spectrum_is_one_job_and_matches_theory")


def run_all(backend=None):
    """Run every check; return a message for the Self-check button."""
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and name not in SHOT_TESTS and callable(fn):
            fn()
    for name in SHOT_TESTS:
        globals()[name](backend)
    return "all checks passed"

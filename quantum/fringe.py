"""Mach-Zehnder fringe circuits, theory curves, and a one-job phase sweep.

Each overtone is a one-qubit interferometer: H, P(phi), H, measure, so
P(1) = sin^2(phi/2). A second "marker" qubit records which path was taken
(how much is set by theta), and the quantum eraser reads the marker in the
X basis so sorting shots by the marker bit brings the fringe back.

Only qiskit and numpy are imported here: this file runs in Pyodide on Qollab.
The backend is always passed in by the caller and never created here.
"""

import json

import numpy as np
from qiskit import QuantumCircuit, transpile

MODES = ("plain", "marker", "eraser")


def _check_mode(mode):
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")


def fringe_circuit(phi, theta=0.0, mode="plain"):
    """Build the interferometer circuit for one phase.

    plain:  1 qubit.  H, P(phi), H, measure.
    marker: 2 qubits. H_0, P(phi)_0, CRY(2*theta) 0->1, H_0, measure both.
            theta = pi/2 is a full marker (equivalent to CX).
    eraser: as marker, plus H on the marker just before measuring.
    """
    _check_mode(mode)
    phi = float(phi)
    theta = float(theta)

    if mode == "plain":
        qc = QuantumCircuit(1, 1, name=f"fringe_plain_{phi:.4f}")
        qc.h(0)
        qc.p(phi, 0)
        qc.h(0)
        qc.measure(0, 0)
        return qc

    qc = QuantumCircuit(2, 2, name=f"fringe_{mode}_{phi:.4f}_{theta:.4f}")
    qc.h(0)
    qc.p(phi, 0)
    qc.cry(2 * theta, 0, 1)
    qc.h(0)
    if mode == "eraser":
        qc.h(1)
    qc.measure([0, 1], [0, 1])
    return qc


def expected_p1(phi, theta=0.0, mode="plain"):
    """Theory for P(qubit 0 = 1), ignoring the marker bit.

    With a marker, visibility V = cos(theta) and which-path knowledge
    K = sin(theta), so V^2 + K^2 = 1. The unsorted eraser matches marker.
    """
    _check_mode(mode)
    if mode == "plain":
        return float(np.sin(phi / 2) ** 2)
    return float(0.5 * (1 - np.cos(theta) * np.cos(phi)))


def expected_p1_given_marker(phi, marker_bit, theta=np.pi / 2):
    if marker_bit not in (0, 1):
        raise ValueError(f"marker_bit must be 0 or 1, got {marker_bit!r}")
    k = np.cos(theta) + (-1) ** marker_bit * np.sin(theta)
    return float((1 + k**2 - 2 * k * np.cos(phi)) / (2 * (1 + k**2)))
    

def _bits(key):
    # Count keys may contain spaces between classical registers.
    return key.replace(" ", "")


def p1_from_counts(counts, shots):
    """Fraction of shots where qubit 0 reads 1.

    Qiskit count keys read right to left, so bits[-1] is qubit 0.
    """
    if shots <= 0:
        return 0.0
    ones = sum(n for key, n in counts.items() if _bits(key)[-1] == "1")
    return ones / shots


def p1_by_marker(counts):
    """Sort eraser counts by the marker bit (bits[0]).

    Returns {"p1_m0", "p1_m1", "n_m0", "n_m1"}: P(q0 = 1 | marker = m) and the
    number of shots with that marker value. An empty subset gives p1 = None.
    """
    n = {0: 0, 1: 0}
    ones = {0: 0, 1: 0}
    for key, count in counts.items():
        bits = _bits(key)
        marker = int(bits[0])
        n[marker] += count
        if bits[-1] == "1":
            ones[marker] += count
    return {
        "p1_m0": ones[0] / n[0] if n[0] else None,
        "p1_m1": ones[1] / n[1] if n[1] else None,
        "n_m0": n[0],
        "n_m1": n[1],
    }


def run_sweep(backend, n_points=13, shots=1000, theta=0.0, mode="plain"):
    """Sweep phi over [0, 2*pi] with ONE backend.run call for all phases.

    Returns a JSON string: a list of records, one per phase, with phi,
    measured, expected. Eraser-mode records also have the marker-sorted
    results (measured_p1_m0/m1, measured_n_m0/m1) and their theory
    (expected_m0/m1, which assumes theta = pi/2); other modes omit them.
    """
    _check_mode(mode)
    phis = np.linspace(0.0, 2 * np.pi, n_points)
    circuits = [fringe_circuit(phi, theta, mode) for phi in phis]
    job = backend.run(transpile(circuits, backend), shots=shots)
    result = job.result()

    rows = []
    for i, phi in enumerate(phis):
        counts = result.get_counts(i)
        row = {
            "phi": float(phi),
            "measured": p1_from_counts(counts, shots),
            "expected": expected_p1(phi, theta, mode),
        }
        # The marker split only means something in eraser mode.
        if mode == "eraser":
            by_marker = p1_by_marker(counts)
            row["measured_p1_m0"] = by_marker["p1_m0"]
            row["measured_p1_m1"] = by_marker["p1_m1"]
            row["measured_n_m0"] = by_marker["n_m0"]
            row["measured_n_m1"] = by_marker["n_m1"]
            row["expected_m0"] = expected_p1_given_marker(phi, 0, theta)
            row["expected_m1"] = expected_p1_given_marker(phi, 1, theta)
        rows.append(row)
    return json.dumps({"mode": mode, "theta": float(theta), "shots": shots, "rows": rows})

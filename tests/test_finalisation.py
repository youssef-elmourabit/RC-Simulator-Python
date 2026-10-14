"""Régressions CLI et export réel des tensions, du courant et des données."""

import csv
import os
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np
import pytest

from rc_simulator import capacitor_voltage, circuit_current, time_grid

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("source,initial,sign", [(5, 0, 1), (0, 5, -1), (-1e-3, 0, -1)])
def test_cli_exports_current_panel_and_consistent_csv(source, initial, sign, tmp_path):
    image, csv_path = tmp_path / "response.png", tmp_path / "response.csv"
    # Garder -1e-3 sous sa forme scientifique pour reproduire le défaut argparse.
    source_argument = "-1e-3" if source == -1e-3 else str(source)
    result = subprocess.run([sys.executable, str(ROOT / "src" / "main.py"),
                             "--voltage", source_argument, "--charge-initial-voltage", str(initial),
                             "--output", str(image), "--csv-output", str(csv_path)],
                            cwd=ROOT, env=os.environ.copy(), capture_output=True,
                            text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert struct.unpack(">II", image.read_bytes()[16:24]) == (1600, 1280)
    with csv_path.open(newline="") as stream:
        reader = csv.reader(stream)
        assert next(reader) == ["time_s", "capacitor_voltage_v", "current_a"]
        values = np.array([[float(value) for value in row] for row in reader])
    times = time_grid(1000, 1e-6)
    expected = np.column_stack((times, capacitor_voltage(times, 1000, 1e-6, source, initial),
                               circuit_current(times, 1000, 1e-6, source, initial)))
    np.testing.assert_array_equal(values, expected)
    assert np.all(sign * values[:, 2] > 0)


def test_negative_scientific_initial_voltage_is_supported(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "src" / "main.py"),
                             "--charge-initial-voltage", "-2e-3", "--initial-voltage", "-1e-3",
                             "--output", str(tmp_path / "signed.png")],
                            cwd=ROOT, env=os.environ.copy(), capture_output=True,
                            text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    assert "Uc0 de la réponse vers E = -0.002 V" in result.stdout
    assert "U0 = -0.001 V" in result.stdout

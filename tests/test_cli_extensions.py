"""Options supplémentaires sans modification des tests console précédents."""

import csv
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from rc_simulator import capacitor_voltage, circuit_current, time_grid

ROOT = Path(__file__).resolve().parents[1]


def run_app(args):
    return subprocess.run([sys.executable, str(ROOT / "src" / "main.py"), *args],
                          cwd=ROOT, env=os.environ.copy(), capture_output=True,
                          text=True, timeout=30, check=False)


@pytest.mark.parametrize("source,initial", [(5, 2), (5, 8), (0, 5)])
def test_cli_general_response_and_csv(source, initial, tmp_path):
    image = tmp_path / "response.png"
    csv_path = tmp_path / "data" / "response.csv"
    result = run_app(["--voltage", str(source), "--charge-initial-voltage", str(initial),
                      "--samples", "11", "--output", str(image), "--csv-output", str(csv_path)])
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "Courant initial vers le condensateur" in result.stdout
    assert "Résultats CSV" in result.stdout
    assert image.exists() and csv_path.exists()
    with csv_path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    values = np.array([[float(row[key]) for key in ("time_s", "capacitor_voltage_v", "current_a")]
                       for row in rows])
    times = time_grid(1000, 1e-6, samples=11)
    expected = np.column_stack((times, capacitor_voltage(times, 1000, 1e-6, source, initial),
                               circuit_current(times, 1000, 1e-6, source, initial)))
    np.testing.assert_array_equal(values, expected)
    assert values[0, 1] == initial
    if source < initial:
        assert np.all(values[:, 2] < 0)


@pytest.mark.parametrize("value", ["nan", "inf", "abc"])
def test_cli_invalid_general_initial_voltage(value, tmp_path):
    image, csv_path = tmp_path / "result.png", tmp_path / "result.csv"
    result = run_app(["--charge-initial-voltage", value, "--output", str(image),
                      "--csv-output", str(csv_path)])
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert not image.exists() and not csv_path.exists()


def test_cli_invalid_csv_path_is_refused_before_png_export(tmp_path):
    image = tmp_path / "result.png"
    result = run_app(["--output", str(image), "--csv-output", str(tmp_path / "result.txt")])
    assert result.returncode == 2
    assert "extension .csv" in result.stderr
    assert not image.exists()

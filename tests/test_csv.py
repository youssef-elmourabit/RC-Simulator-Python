"""Export CSV : fidélité float64, validation et préservation des fichiers."""

import csv
import math

import numpy as np
import pytest

from rc_simulator import capacitor_voltage, circuit_current, time_grid
from rc_simulator.export import COLUMNS, save_csv, validate_csv_path


def test_csv_round_trip_matches_actual_simulation(tmp_path):
    times = time_grid(1000, 1e-6, samples=11)
    voltages = capacitor_voltage(times, 1000, 1e-6, 5, 8)
    currents = circuit_current(times, 1000, 1e-6, 5, 8)
    originals = [data.copy() for data in (times, voltages, currents)]
    path = save_csv(times, voltages, currents, tmp_path / "nested" / "simulation.csv")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        assert tuple(next(reader)) == COLUMNS
        exported = np.array([[float(value) for value in row] for row in reader])
    np.testing.assert_array_equal(exported, np.column_stack((times, voltages, currents)))
    assert np.all(exported[:, 2] < 0)
    for before, after in zip(originals, (times, voltages, currents)):
        np.testing.assert_array_equal(before, after)
    assert not list(path.parent.glob("*.tmp"))


def test_csv_single_point_and_subnormal_values(tmp_path):
    tiny = np.nextafter(0, 1)
    path = save_csv([0], [tiny], [-tiny], tmp_path / "one.CSV")
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    assert len(rows) == 2
    assert float(rows[1][1]) == tiny
    assert float(rows[1][2]) == -tiny


@pytest.mark.parametrize("destination", ["", " ", "result.txt", "result", "bad\x00.csv"])
def test_bad_csv_names(destination):
    with pytest.raises(ValueError):
        validate_csv_path(destination)


@pytest.mark.parametrize("destination", [None, 1, b"result.csv"])
def test_bad_csv_path_types(destination):
    with pytest.raises(TypeError):
        validate_csv_path(destination)


def test_csv_directory_symlink_and_blocked_parent_are_rejected(tmp_path):
    folder = tmp_path / "folder.csv"
    folder.mkdir()
    with pytest.raises(ValueError):
        validate_csv_path(folder)
    existing = tmp_path / "existing.csv"
    existing.write_text("conserver")
    link = tmp_path / "link.csv"
    link.symlink_to(existing)
    with pytest.raises(ValueError):
        validate_csv_path(link)
    with pytest.raises(ValueError):
        validate_csv_path(existing / "nested" / "output.csv")
    assert existing.read_text() == "conserver"


@pytest.mark.parametrize("time,voltage,current,error", [
    ([], [], [], ValueError), ([0, 1], [1], [0, 0], ValueError),
    ([0, 0], [1, 1], [0, 0], ValueError), ([1, 0], [1, 1], [0, 0], ValueError),
    ([-1, 0], [1, 1], [0, 0], ValueError), ([0, math.inf], [1, 1], [0, 0], ValueError),
    ([0, 1], [math.nan, 1], [0, 0], ValueError), ([0, 1], [1, 1], [0, math.inf], ValueError),
    ([[0, 1]], [1, 1], [0, 0], ValueError), ([0, 1], [True, 1], [0, 0], TypeError),
    ([0, 1], [1, 1], ["0", "1"], TypeError), ([0, 1], [1j, 0], [0, 0], TypeError),
])
def test_invalid_csv_data_preserves_destination(time, voltage, current, error, tmp_path):
    path = tmp_path / "result.csv"
    path.write_text("conserver")
    with pytest.raises(error):
        save_csv(time, voltage, current, path)
    assert path.read_text() == "conserver"
    assert not list(tmp_path.glob("*.tmp"))


def test_csv_success_replaces_existing_file(tmp_path):
    path = tmp_path / "result.csv"
    path.write_text("ancienne version")
    save_csv([0], [5], [-0.005], path)
    assert path.read_text().startswith("time_s,capacitor_voltage_v,current_a\n")


def test_csv_failed_replacement_keeps_previous_file_and_cleans_temp(tmp_path, monkeypatch):
    path = tmp_path / "result.csv"
    path.write_text("conserver")
    def fail_replace(*args):
        raise OSError("Erreur simulée")
    monkeypatch.setattr("rc_simulator.export.os.replace", fail_replace)
    with pytest.raises(OSError, match="Erreur simulée"):
        save_csv([0], [5], [-0.005], path)
    assert path.read_text() == "conserver"
    assert not list(tmp_path.glob("*.tmp"))

"""Vérifier les données et l'export d'une vraie figure, sans interface graphique."""

import math
import struct

import numpy as np
import pytest

from rc_simulator.model import charge_voltage, discharge_voltage, time_grid
from rc_simulator.plotting import plot_response, save_png


def example_figure():
    times = time_grid(1000, 1e-6)
    return plot_response(times, charge_voltage(times, 1000, 1e-6, 5),
                         discharge_voltage(times, 1000, 1e-6, 5), tau=0.001)


def test_graph_uses_supplied_data_and_si_units():
    figure = example_figure()
    axes = figure.axes[0]
    assert "ms" in axes.get_xlabel()
    assert "(V)" in axes.get_ylabel()
    assert len(axes.lines) == 3  # Deux expériences et repère de constante de temps.
    np.testing.assert_allclose(axes.lines[0].get_xdata()[[0, -1]], [0, 5])
    np.testing.assert_allclose(axes.lines[0].get_ydata()[[0, -1]], [0, 4.966310265004573])
    np.testing.assert_allclose(axes.lines[1].get_ydata()[[0, -1]], [5, 0.03368973499542734])


def test_png_export_creates_parent_and_valid_image(tmp_path):
    output = save_png(example_figure(), tmp_path / "nested" / "response.png")
    contents = output.read_bytes()
    assert contents[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", contents[16:24]) == (1600, 960)
    assert output.stat().st_size > 10_000


@pytest.mark.parametrize("time,charge,discharge", [
    ([0, 1], [0], [5, 0]), ([0, 0], [0, 1], [5, 0]),
    ([-1, 1], [0, 1], [5, 0]), ([0, math.inf], [0, 1], [5, 0]),
    ([0, 1], [0, math.nan], [5, 0]), ([[0, 1]], [0, 1], [5, 0]),
    ([0, 1], [0j, 1j], [5, 0]),
    ([True, 2], [0, 1], [5, 0]),
])
def test_invalid_plot_vectors(time, charge, discharge):
    with pytest.raises(ValueError):
        plot_response(time, charge, discharge, tau=1)


@pytest.mark.parametrize("tau", [0, -1, math.inf, math.nan, True])
def test_invalid_plot_time_constant(tau):
    with pytest.raises((ValueError, TypeError)):
        plot_response([0, 1], [0, 1], [5, 0], tau=tau)


def test_non_png_export_is_refused(tmp_path):
    with pytest.raises(ValueError, match=".png"):
        save_png(example_figure(), tmp_path / "response.pdf")
    assert not (tmp_path / "response.pdf").exists()


@pytest.mark.parametrize("dpi", [0, -1, 1.5, True])
def test_invalid_resolution(tmp_path, dpi):
    with pytest.raises(ValueError):
        save_png(example_figure(), tmp_path / "response.png", dpi=dpi)

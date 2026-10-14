"""Courant tracé : signes physiques, unités, données et export à deux panneaux."""

import math
import struct

import numpy as np
import pytest

from rc_simulator import capacitor_voltage, circuit_current, discharge_voltage, time_grid
from rc_simulator.plotting import plot_response, save_png


@pytest.mark.parametrize("source,initial,resistance,unit,scale", [
    (5, 0, 1000, "mA", 1000), (0, 5, 1000, "mA", 1000),
    (5, 8, 1000, "mA", 1000), (5, 5, 1000, "mA", 1000),
    (5, 0, 2.5, "A", 1),
])
def test_two_panels_keep_voltage_and_signed_current(source, initial, resistance, unit, scale):
    times = time_grid(resistance, 1e-6)
    voltage = capacitor_voltage(times, resistance, 1e-6, source, initial)
    comparison = discharge_voltage(times, resistance, 1e-6, 5)
    current = circuit_current(times, resistance, 1e-6, source, initial)
    tau = resistance * 1e-6
    original = current.copy()
    figure = plot_response(times, voltage, comparison, tau=tau, current=current)
    assert len(figure.axes) == 2
    voltage_axes, current_axes = figure.axes
    assert "(V)" in voltage_axes.get_ylabel()
    assert f"({unit})" in current_axes.get_ylabel()
    assert "(ms)" in current_axes.get_xlabel()
    np.testing.assert_array_equal(voltage_axes.lines[0].get_ydata(), voltage)
    np.testing.assert_array_equal(voltage_axes.lines[1].get_ydata(), comparison)
    np.testing.assert_array_equal(current_axes.lines[0].get_ydata(), current * scale)
    np.testing.assert_array_equal(current_axes.lines[0].get_xdata(), times * 1000)
    np.testing.assert_array_equal(current, original)
    assert current_axes.lines[0].get_ydata()[0] == pytest.approx((source - initial) / resistance * scale)
    if source > initial:
        assert np.all(current_axes.lines[0].get_ydata() > 0)
    elif source < initial:
        assert np.all(current_axes.lines[0].get_ydata() < 0)
    else:
        assert np.all(current_axes.lines[0].get_ydata() == 0)


def test_current_panel_export_and_time_in_seconds(tmp_path):
    times = [0, 1, 5]
    figure = plot_response(times, [0, 3, 5], [5, 2, 0], tau=1, current=[2, 1, 0.01])
    assert "(s)" in figure.axes[1].get_xlabel()
    assert "(A)" in figure.axes[1].get_ylabel()
    output = save_png(figure, tmp_path / "current.png")
    contents = output.read_bytes()
    assert contents[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", contents[16:24]) == (1600, 1280)


@pytest.mark.parametrize("current", [[], [1], [1, 2, 3], [[1, 2]], [math.inf, 0],
                                   [math.nan, 0], [True, 1], [1j, 0j], ["1", "2"]])
def test_invalid_current_data_is_refused(current):
    with pytest.raises(ValueError):
        plot_response([0, 1], [0, 1], [1, 0], tau=1, current=current)


def test_oversized_time_constant_is_a_validation_error():
    with pytest.raises(ValueError, match="fini"):
        plot_response([0, 1], [0, 1], [1, 0], tau=10**400)


def test_png_symlink_is_refused_without_modifying_target(tmp_path):
    original = tmp_path / "original.txt"
    original.write_text("conserver")
    output = tmp_path / "link.png"
    output.symlink_to(original)
    with pytest.raises(ValueError, match="lien"):
        save_png(plot_response([0, 1], [0, 1], [1, 0], tau=1), output)
    assert original.read_text() == "conserver"

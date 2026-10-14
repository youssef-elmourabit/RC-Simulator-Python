"""Contrôles physiques, numériques et contrats du modèle RC."""

import math
import sys

import numpy as np
import pytest

from rc_simulator.model import (
    MAX_SAMPLES, charge_voltage, discharge_voltage, time_constant, time_grid,
)


def test_time_constant_and_si_units():
    assert time_constant(1000, 1e-6) == pytest.approx(0.001)
    assert time_constant(4700, 100e-6) == pytest.approx(0.47)
    assert time_constant(np.float64(1000), np.float64(1e-6)) == pytest.approx(0.001)


@pytest.mark.parametrize("invalid", [0, -0.0, -1, math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("field", [0, 1])
def test_invalid_component_values(invalid, field):
    values = [1000.0, 1e-6]
    values[field] = invalid
    with pytest.raises(ValueError):
        time_constant(*values)


@pytest.mark.parametrize("invalid", [True, np.bool_(False), "1000", None, 1 + 0j])
@pytest.mark.parametrize("field", [0, 1])
def test_component_types(invalid, field):
    values = [1000.0, 1e-6]
    values[field] = invalid
    with pytest.raises(TypeError):
        time_constant(*values)


@pytest.mark.parametrize("resistance,capacitance", [(1e308, 10), (1e-200, 1e-200), (10**400, 1)])
def test_time_constant_outside_float64_range(resistance, capacitance):
    with pytest.raises(ValueError):
        time_constant(resistance, capacitance)


def test_subnormal_time_constant_is_supported():
    smallest = np.nextafter(0.0, 1.0)
    assert time_constant(smallest, 1) == smallest
    assert charge_voltage(smallest, smallest, 1, 5) == pytest.approx(5 * (1 - math.exp(-1)))


@pytest.mark.parametrize("voltage", [5.0, -5.0, 0.0])
def test_initial_conditions_and_value_at_tau(voltage):
    resistance, capacitance = 1000, 1e-6
    tau = time_constant(resistance, capacitance)
    assert charge_voltage(0, resistance, capacitance, voltage) == 0
    assert discharge_voltage(0, resistance, capacitance, voltage) == voltage
    assert charge_voltage(tau, resistance, capacitance, voltage) == pytest.approx(voltage * (1 - math.exp(-1)))
    assert discharge_voltage(tau, resistance, capacitance, voltage) == pytest.approx(voltage * math.exp(-1))


@pytest.mark.parametrize("function", [charge_voltage, discharge_voltage])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_nonfinite_voltage(function, invalid):
    with pytest.raises(ValueError):
        function([0, 0.001], 1000, 1e-6, invalid)


@pytest.mark.parametrize("function", [charge_voltage, discharge_voltage])
@pytest.mark.parametrize("invalid", [True, "5", None, 1j])
def test_voltage_types(function, invalid):
    with pytest.raises(TypeError):
        function(0, 1000, 1e-6, invalid)


@pytest.mark.parametrize("function", [charge_voltage, discharge_voltage])
@pytest.mark.parametrize("invalid", [-1, math.nan, math.inf, [0, -1], [0, math.inf], [], [[0, 1]]])
def test_invalid_times(function, invalid):
    with pytest.raises(ValueError):
        function(invalid, 1000, 1e-6, 5)


@pytest.mark.parametrize("function", [charge_voltage, discharge_voltage])
@pytest.mark.parametrize("invalid", [True, "0.001", ["0", "1"], [True, False], [True, 0.001], [0j, 1j]])
def test_time_types(function, invalid):
    with pytest.raises(TypeError):
        function(invalid, 1000, 1e-6, 5)


def test_vectorization_shape_and_input_preservation():
    times = np.array([0, 0.001, 0.005])
    original = times.copy()
    charged = charge_voltage(times, 1000, 1e-6, 5)
    discharged = discharge_voltage(times, 1000, 1e-6, 5)
    assert charged.shape == discharged.shape == times.shape
    assert charged.dtype == discharged.dtype == np.float64
    np.testing.assert_array_equal(times, original)
    np.testing.assert_allclose(charged, [0, 3.1606027941427883, 4.966310265004573], rtol=1e-12)
    np.testing.assert_allclose(discharged, [5, 1.8393972058572117, 0.03368973499542734], rtol=1e-12)
    assert isinstance(charge_voltage(0.001, 1000, 1e-6, 5), float)


def test_monotonicity_bounds_and_complementarity():
    times = time_grid(1000, 1e-6)
    charged = charge_voltage(times, 1000, 1e-6, 5)
    discharged = discharge_voltage(times, 1000, 1e-6, 5)
    assert np.all(np.diff(charged) >= 0)
    assert np.all(np.diff(discharged) <= 0)
    assert np.all((charged >= 0) & (charged <= 5))
    assert np.all((discharged >= 0) & (discharged <= 5))
    np.testing.assert_allclose(charged + discharged, 5, rtol=1e-14)


def test_charge_preserves_small_time_variations():
    result = charge_voltage(1e-20, 1, 1, 5)
    assert result > 0
    assert result == pytest.approx(5e-20, rel=1e-14, abs=0)


def test_charge_recovers_underflowing_time_ratio():
    result = charge_voltage(1e-300, 1e300, 1, 1e300)
    assert result == pytest.approx(1e-300, rel=1e-14, abs=0)
    negative = charge_voltage(1e-300, 1e300, 1, -1e300)
    assert negative == -result


def test_discharge_recovers_late_response_for_large_voltage():
    # Référence indépendante : log(U0) - t/τ reste représentable.
    expected = math.exp(math.log(1e300) - 800)
    result = discharge_voltage(800, 1, 1, 1e300)
    assert result > 0
    assert result == pytest.approx(expected, rel=1e-12, abs=0)


def test_large_relative_time_reaches_asymptotes():
    assert charge_voltage(sys.float_info.max, 1e-300, 1, 5) == 5
    assert discharge_voltage(sys.float_info.max, 1e-300, 1, 5) == 0
    assert charge_voltage(sys.float_info.max, 1, 1, 0) == 0


def test_default_time_grid_and_explicit_duration():
    times = time_grid(1000, 1e-6)
    assert times.size == 501
    assert times[0] == 0
    assert times[-1] == pytest.approx(0.005)
    assert np.all(np.diff(times) > 0)
    np.testing.assert_allclose(time_grid(1000, 1e-6, duration=0.01, samples=3), [0, 0.005, 0.01])


@pytest.mark.parametrize("samples", [0, 1, -1, MAX_SAMPLES + 1])
def test_invalid_sample_count(samples):
    with pytest.raises(ValueError):
        time_grid(1000, 1e-6, samples=samples)


@pytest.mark.parametrize("samples", [True, np.bool_(True), 3.5, "501"])
def test_sample_count_types(samples):
    with pytest.raises(TypeError):
        time_grid(1000, 1e-6, samples=samples)


@pytest.mark.parametrize("duration", [0, -1, math.nan, math.inf])
def test_invalid_duration(duration):
    with pytest.raises(ValueError):
        time_grid(1000, 1e-6, duration=duration)


def test_time_grid_extreme_ranges():
    with pytest.raises(ValueError):
        time_grid(1e308, 1)  # 5τ ne peut pas être représenté.
    times = time_grid(1e308, 1, duration=sys.float_info.max, samples=3)
    assert np.all(np.isfinite(times))
    assert times[-1] == sys.float_info.max
    with pytest.raises(ValueError, match="temps distincts"):
        time_grid(np.nextafter(0.0, 1.0), 1)

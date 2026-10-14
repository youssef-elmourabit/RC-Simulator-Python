"""Réponse générale et courant : références physiques et cas numériques extrêmes."""

import math
import sys

import numpy as np
import pytest

from rc_simulator import capacitor_voltage, charge_voltage, circuit_current, discharge_voltage, time_constant


@pytest.mark.parametrize("source,initial", [(5, 0), (5, 2), (5, 8), (5, 5),
                                          (0, 5), (-5, -2), (-5, -8), (5, -2), (-5, 2)])
def test_general_response_conditions_and_bounds(source, initial):
    tau = time_constant(1000, 1e-6)
    times = np.array([0, tau, 5 * tau, 1000 * tau])
    result = capacitor_voltage(times, 1000, 1e-6, source, initial)
    expected = source + (initial - source) * np.exp(-times / tau)
    np.testing.assert_allclose(result, expected, rtol=1e-13, atol=1e-15)
    assert result[0] == initial
    assert result[-1] == source
    assert np.all(result >= min(source, initial))
    assert np.all(result <= max(source, initial))
    differences = np.diff(result)
    assert np.all(differences >= 0) if initial <= source else np.all(differences <= 0)
    assert isinstance(capacitor_voltage(0, 1000, 1e-6, source, initial), float)


def test_old_charge_and_discharge_are_reproduced_exactly():
    times = np.array([0, 1e-20, 0.001, 0.005, 0.8])
    np.testing.assert_array_equal(capacitor_voltage(times, 1000, 1e-6, 5, 0),
                                  charge_voltage(times, 1000, 1e-6, 5))
    np.testing.assert_array_equal(capacitor_voltage(times, 1000, 1e-6, 0, 5),
                                  discharge_voltage(times, 1000, 1e-6, 5))


@pytest.mark.parametrize("source,initial", [(5, 0), (5, 2), (5, 8), (0, 5), (-5, -2), (5, 5)])
def test_current_initial_value_sign_and_decay(source, initial):
    tau = time_constant(1000, 1e-6)
    times = np.array([0, tau, 2 * tau, 5 * tau])
    current = circuit_current(times, 1000, 1e-6, source, initial)
    expected = ((source - initial) / 1000) * np.exp(-times / tau)
    np.testing.assert_allclose(current, expected, rtol=1e-13, atol=0)
    assert current[0] == pytest.approx((source - initial) / 1000)
    assert np.all(np.diff(np.abs(current)) <= 0)
    voltage = capacitor_voltage(times, 1000, 1e-6, source, initial)
    np.testing.assert_allclose(current, (source - voltage) / 1000, rtol=1e-12, atol=1e-18)


@pytest.mark.parametrize("source,initial", [(5, 2), (5, 8), (0, 5), (-5, 2)])
def test_current_matches_capacitor_derivative(source, initial):
    time, h, capacitance = 0.0007, 1e-8, 1e-6
    derivative = (capacitor_voltage(time + h, 1000, capacitance, source, initial) -
                  capacitor_voltage(time - h, 1000, capacitance, source, initial)) / (2 * h)
    assert circuit_current(time, 1000, capacitance, source, initial) == pytest.approx(
        capacitance * derivative, rel=1e-9, abs=0)


def test_tiny_current_is_not_lost_when_voltage_rounds_to_source():
    assert capacitor_voltage(40, 1, 1, 5, 0) == 5
    current = circuit_current(40, 1, 1, 5, 0)
    assert current > 0
    assert current == pytest.approx(5 * math.exp(-40), rel=1e-13, abs=0)
    delta = 1.0 - math.nextafter(1.0, 0.0)
    assert circuit_current(0, 1, 1, 1, math.nextafter(1.0, 0.0)) == delta


def test_opposite_extreme_voltages_do_not_overflow_difference():
    largest = sys.float_info.max
    times = np.array([0, math.log(2), 1000])
    voltage = capacitor_voltage(times, 1, 1, largest, -largest)
    assert voltage[0] == -largest and voltage[-1] == largest
    assert np.all(np.isfinite(voltage))
    assert voltage[1] == 0
    assert circuit_current(0, largest, 1e-308, largest, -largest) == pytest.approx(2)


def test_same_sign_extreme_voltages_stay_finite():
    largest = sys.float_info.max
    initial = math.nextafter(largest, 0)
    result = capacitor_voltage([0, math.log(2), 40], 1, 1, largest, initial)
    assert np.all(np.isfinite(result))
    assert np.all((result >= initial) & (result <= largest))
    np.testing.assert_array_equal(capacitor_voltage([0, 1, 1e308], 1, 1, largest, largest),
                                  [largest, largest, largest])


def test_representable_small_initial_response():
    result = capacitor_voltage(1e-300, 1e300, 1, 1e300, 1e-300)
    assert result == pytest.approx(2e-300, rel=1e-13, abs=0)


def test_current_can_recover_unrepresentable_amplitude_at_later_time():
    expected = math.exp(math.log(2) + 600 * math.log(10) - 1500)
    current = circuit_current(1500, 1e-300, 1e300, 1e300, -1e300)
    assert current > 0
    assert current == pytest.approx(expected, rel=1e-12, abs=0)
    with pytest.raises(ValueError, match="courant"):
        circuit_current([0, 1500], 1e-300, 1e300, 1e300, -1e300)


def test_current_extreme_relative_time_and_underflow():
    assert circuit_current(sys.float_info.max, 1e-300, 1, 5, 0) == 0
    assert circuit_current(0, 1e308, 1e-308, 1e-300, 0) == 0
    smallest = np.nextafter(0, 1)
    assert circuit_current(0, 1, 1, smallest, 0) == smallest


@pytest.mark.parametrize("function", [capacitor_voltage, circuit_current])
@pytest.mark.parametrize("field,invalid,error", [
    (0, -1, ValueError), (0, [0, math.inf], ValueError), (0, True, TypeError),
    (1, 0, ValueError), (1, "1000", TypeError), (2, -1, ValueError),
    (3, math.nan, ValueError), (3, math.inf, ValueError), (3, True, TypeError),
    (4, math.nan, ValueError), (4, -math.inf, ValueError), (4, "2", TypeError),
])
def test_new_functions_reuse_input_contracts(function, field, invalid, error):
    values = [0.001, 1000, 1e-6, 5, 2]
    values[field] = invalid
    with pytest.raises(error):
        function(*values)


def test_new_functions_preserve_input_arrays():
    times = np.array([0, 0.001, 0.005])
    original = times.copy()
    for function in (capacitor_voltage, circuit_current):
        result = function(times, 1000, 1e-6, 5, 2)
        assert result.dtype == np.float64 and result.shape == times.shape
        np.testing.assert_array_equal(times, original)

"""Réponses analytiques RC ; unités SI et calculs NumPy en float64."""

from __future__ import annotations

import math
from numbers import Integral, Real

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
MAX_SAMPLES = 1_000_000


def _finite_real(value: Real, name: str, *, positive: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise TypeError(f"{name} doit être un nombre réel, sans unité ni texte.")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} doit être fini et représentable en float64.") from error
    if not math.isfinite(result) or (positive and result <= 0.0):
        constraint = "fini et strictement positif" if positive else "fini"
        raise ValueError(f"{name} doit être {constraint}.")
    return result


def time_constant(resistance: Real, capacitance: Real) -> float:
    """Calculer τ = R × C en secondes, avec R en Ω et C en F.

    R et C doivent être finis et > 0. Un produit infini ou arrondi à zéro
    est refusé. Un τ subnormal strictement positif reste accepté.
    """
    resistance = _finite_real(resistance, "R (Ω)", positive=True)
    capacitance = _finite_real(capacitance, "C (F)", positive=True)
    tau = resistance * capacitance
    if not math.isfinite(tau) or tau <= 0.0:
        raise ValueError("τ = R × C est hors de la plage positive représentable en float64.")
    return tau


def _time_values(time: ArrayLike) -> tuple[FloatArray, bool]:
    if isinstance(time, (list, tuple)) and any(isinstance(item, (bool, np.bool_)) for item in time):
        raise TypeError("t ne doit pas contenir de booléens.")
    raw = np.asarray(time)
    if raw.ndim > 1 or raw.size == 0:
        raise ValueError("t doit être un scalaire ou un vecteur non vide à une dimension.")
    if raw.dtype.kind not in "iuf":
        raise TypeError("t doit contenir uniquement des nombres réels, sans booléens ni texte.")
    try:
        with np.errstate(over="raise", invalid="raise"):
            values = np.atleast_1d(raw).astype(np.float64)
    except (FloatingPointError, OverflowError) as error:
        raise ValueError("t doit être représentable en float64.") from error
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("t (s) doit être fini et supérieur ou égal à zéro.")
    return values, raw.ndim == 0


def _relative_time(times: FloatArray, tau: float) -> FloatArray:
    # Un rapport hors plage vers +inf signifie une réponse à son asymptote.
    with np.errstate(over="ignore", under="ignore"):
        return times / tau


def charge_voltage(time: ArrayLike, resistance: Real, capacitance: Real,
                   source_voltage: Real) -> float | FloatArray:
    """Uc(t) = E × (1 - exp(-t/τ)), pour un condensateur initialement déchargé.

    E est une tension finie signée en V. t est un scalaire ou un vecteur
    réel fini non négatif en s. Le retour est un float ou un tableau float64
    de même longueur ; les données fournies ne sont jamais modifiées.
    """
    tau = time_constant(resistance, capacitance)
    voltage = _finite_real(source_voltage, "E (V)")
    times, scalar = _time_values(time)
    relative = _relative_time(times, tau)
    with np.errstate(under="ignore"):
        result = voltage * -np.expm1(-relative)
        # Lorsque t/τ est subnormal, la réponse est linéaire à la précision
        # float64. Garder les exposants évite de perdre E × t/τ prématurément.
        early = (times > 0.0) & (relative < np.finfo(np.float64).tiny)
        if voltage != 0.0 and np.any(early):
            mv, ev = math.frexp(voltage)
            mt, et = np.frexp(times[early])
            mc, ec = math.frexp(tau)
            result[early] = np.ldexp(mv * mt / mc, ev + et - ec)
    return float(result[0]) if scalar else result


def discharge_voltage(time: ArrayLike, resistance: Real, capacitance: Real,
                      initial_voltage: Real) -> float | FloatArray:
    """Uc(t) = U0 × exp(-t/τ), après déconnexion de la source et décharge via R.

    U0 est une tension finie signée en V ; mêmes contrats de temps et de
    retour que charge_voltage(). Un résultat très petit peut s'arrondir à zéro.
    """
    tau = time_constant(resistance, capacitance)
    voltage = _finite_real(initial_voltage, "U0 (V)")
    times, scalar = _time_values(time)
    relative = _relative_time(times, tau)
    result = np.empty_like(times)
    with np.errstate(under="ignore"):
        usual = relative <= 700.0
        result[usual] = voltage * np.exp(-relative[usual])
        # Ne pas annuler exp(-t/τ) avant de le multiplier par un grand U0.
        # Quatre facteurs décroissants gardent les intermédiaires bornés.
        factor = np.exp(-relative[~usual] / 4.0)
        tail = voltage * factor
        for _ in range(3):
            tail *= factor
        result[~usual] = tail
    return float(result[0]) if scalar else result


def capacitor_voltage(time: ArrayLike, resistance: Real, capacitance: Real,
                      source_voltage: Real, initial_voltage: Real = 0.0) -> float | FloatArray:
    """Uc(t) = E + (Uc0 - E) × exp(-t/τ), tensions finies signées en V.

    Mêmes contrats de temps et de retour que charge_voltage(). Les anciens
    cas de charge depuis zéro et de décharge restent exactement réutilisés.
    """
    tau = time_constant(resistance, capacitance)
    source = _finite_real(source_voltage, "E (V)")
    initial = _finite_real(initial_voltage, "Uc0 (V)")
    times, scalar = _time_values(time)
    if initial == 0.0:
        result = charge_voltage(times, resistance, capacitance, source)
    elif source == 0.0:
        result = discharge_voltage(times, resistance, capacitance, initial)
    elif source == initial:
        result = np.full_like(times, source)
    elif (source > 0.0) != (initial > 0.0):
        # Une différence entre tensions opposées pourrait déborder. La somme
        # pondérée a deux termes opposés, chacun borné par sa tension d'entrée.
        result = (charge_voltage(times, resistance, capacitance, source) +
                  discharge_voltage(times, resistance, capacitance, initial))
    else:
        # Même signe : la différence reste finie. Choisir le point d'ancrage
        # proche préserve l'état initial et la petite queue vers E.
        early = _relative_time(times, tau) <= math.log(2.0)
        result = np.empty_like(times)
        if np.any(early):
            result[early] = initial + charge_voltage(times[early], resistance, capacitance, source - initial)
        if np.any(~early):
            result[~early] = source + discharge_voltage(times[~early], resistance, capacitance, initial - source)
    if not np.all(np.isfinite(result)):
        raise ValueError("La tension calculée est hors de la plage représentable en float64.")
    return float(result[0]) if scalar else result


def _decayed_scaled(mantissa: float, exponent: int, relative: FloatArray) -> FloatArray:
    """Calculer m × 2^e × exp(-x) sans former l'amplitude ou exp(-x) seuls."""
    result = np.zeros_like(relative)
    log_two = math.log(2.0)
    # Au-delà de cette borne, même le plus petit float64 positif ne peut
    # être obtenu. Éviter aussi de convertir +inf en exposant entier.
    active = np.isfinite(relative) & (relative <= max(0.0, (exponent + 1075) * log_two))
    values = relative[active]
    shifts = np.floor(values / log_two).astype(np.int64)
    remainder = values - shifts * log_two
    with np.errstate(under="ignore", over="ignore"):
        result[active] = np.ldexp(mantissa * np.exp(-remainder), exponent - shifts)
    return result


def circuit_current(time: ArrayLike, resistance: Real, capacitance: Real,
                    source_voltage: Real, initial_voltage: Real = 0.0) -> float | FloatArray:
    """i(t) = (E - Uc0)/R × exp(-t/τ), en A, positif de la source vers C.

    Cette forme équivaut à (E - Uc(t))/R et C × dUc/dt. Elle préserve le
    courant tardif même si la tension affichée s'est déjà arrondie à E.
    Un courant non fini est refusé ; un sous-dépassement peut donner zéro.
    """
    tau = time_constant(resistance, capacitance)
    resistance = _finite_real(resistance, "R (Ω)", positive=True)
    source = _finite_real(source_voltage, "E (V)")
    initial = _finite_real(initial_voltage, "Uc0 (V)")
    times, scalar = _time_values(time)
    if source == initial:
        result = np.zeros_like(times)
    else:
        me, ee = math.frexp(source)
        mi, ei = math.frexp(initial)
        scale = ei if source == 0.0 else ee if initial == 0.0 else max(ee, ei)
        # La différence normalisée tient dans [-2, 2], même pour ±DBL_MAX.
        difference = math.ldexp(me, ee - scale) - math.ldexp(mi, ei - scale)
        mr, er = math.frexp(resistance)
        mantissa, adjustment = math.frexp(difference / mr)
        result = _decayed_scaled(mantissa, scale + adjustment - er, _relative_time(times, tau))
    if not np.all(np.isfinite(result)):
        raise ValueError("Le courant calculé est hors de la plage représentable en float64.")
    return float(result[0]) if scalar else result


def time_grid(resistance: Real, capacitance: Real, *, duration: Real | None = None,
              samples: Integral = 501) -> FloatArray:
    """Générer des temps en s, de 0 à duration incluse (5τ par défaut).

    Entre 2 et MAX_SAMPLES points distincts sont exigés. Une durée hors
    plage ou trop petite pour ces points est refusée, jamais corrigée en silence.
    """
    tau = time_constant(resistance, capacitance)
    if isinstance(samples, (bool, np.bool_)) or not isinstance(samples, Integral):
        raise TypeError("Le nombre de points doit être un entier.")
    if not 2 <= samples <= MAX_SAMPLES:
        raise ValueError(f"Le nombre de points doit être compris entre 2 et {MAX_SAMPLES}.")
    stop = _finite_real(5.0 * tau if duration is None else duration, "Durée (s)", positive=True)
    with np.errstate(under="ignore"):
        times = np.linspace(0.0, 1.0, int(samples), dtype=np.float64) * stop
    if np.any(np.diff(times) <= 0.0):
        raise ValueError("Durée trop petite pour obtenir des temps distincts ; réduire le nombre de points.")
    return times

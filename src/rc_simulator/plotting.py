"""Présentation des données ; aucune formule électrique dans ce module."""

from __future__ import annotations

from numbers import Integral, Real
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from .model import _finite_real
from .export import validate_output_path


def _plot_vector(data: ArrayLike, label: str) -> np.ndarray:
    """Valider une série réelle finie destinée à un graphique."""
    if isinstance(data, (list, tuple)) and any(isinstance(item, (bool, np.bool_)) for item in data):
        raise ValueError(f"{label} : les booléens ne sont pas des mesures.")
    raw = np.asarray(data)
    if raw.ndim != 1 or raw.size < 2 or raw.dtype.kind not in "iuf":
        raise ValueError(f"{label} : vecteur réel d'au moins deux points requis.")
    with np.errstate(over="ignore"):
        values = raw.astype(np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{label} : valeurs finies requises.")
    return values


def plot_response(time: ArrayLike, charge: ArrayLike, discharge: ArrayLike, *,
                  tau: Real, description: str = "",
                  charge_label: str = "Charge — condensateur à 0 V",
                  current: ArrayLike | None = None) -> Figure:
    """Tracer trois vecteurs finis de même longueur, t >= 0 strictement croissant.

    Les données sont en secondes et volts. Pour une durée < 1 s, l'axe du
    temps est présenté en ms ; le modèle et τ restent exprimés en secondes.
    Si current est fourni en A, ajouter un panneau du courant de la réponse
    vers E : mA pour une amplitude < 1 A, A sinon. Sans current, conserver
    la figure historique de tensions. Le rendu Agg fonctionne sans fenêtre.
    """
    vectors = []
    for label, data in [("Temps", time), ("Charge", charge), ("Décharge", discharge)]:
        vectors.append(_plot_vector(data, label))
    times, charged, discharged = vectors
    if charged.shape != times.shape or discharged.shape != times.shape:
        raise ValueError("Les trois vecteurs doivent avoir la même longueur.")
    if np.any(times < 0.0) or np.any(np.diff(times) <= 0.0):
        raise ValueError("Les temps doivent être non négatifs et strictement croissants.")
    tau = _finite_real(tau, "τ (s)", positive=True)
    currents = None if current is None else _plot_vector(current, "Courant")
    if currents is not None and currents.shape != times.shape:
        raise ValueError("Le courant et les temps doivent avoir la même longueur.")

    scale, unit = (1000.0, "ms") if times[-1] < 1.0 else (1.0, "s")
    figure = Figure(figsize=(10, 6 if currents is None else 8), layout="constrained", facecolor="#f5f7fa")
    FigureCanvasAgg(figure)
    if currents is None:
        axes = figure.subplots()
        current_axes = None
    else:
        axes, current_axes = figure.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [1.25, 1]})
    axes.set_facecolor("white")
    axes.plot(times * scale, charged, color="#087f8c", linewidth=2.5, label=charge_label)
    axes.plot(times * scale, discharged, color="#d16b3b", linewidth=2.5,
              linestyle="--", label="Décharge — condensateur à U₀")
    if times[0] <= tau <= times[-1]:
        axes.axvline(float(tau) * scale, color="#667085", linestyle=":", linewidth=1.5,
                     label=f"τ = {float(tau):.6g} s")
    axes.set(xlabel=f"Temps t ({unit})" if current_axes is None else "", ylabel="Tension du condensateur Uc (V)",
             xlim=(float(times[0] * scale), float(times[-1] * scale)))
    axes.set_title(f"{description}\nConstante de temps τ = {float(tau):.6g} s", fontsize=11, pad=12)
    title = "Circuit RC série idéal — charge et décharge" if current_axes is None else "Circuit RC série idéal — tensions et courant"
    figure.suptitle(title, fontsize=16, fontweight="bold")
    axes.grid(True, color="#d9dee7", linewidth=0.7, alpha=0.8)
    axes.spines[["top", "right"]].set_visible(False)
    axes.legend(loc="best", framealpha=0.95)
    if current_axes is not None:
        current_scale, current_unit = (1000.0, "mA") if np.max(np.abs(currents)) < 1.0 else (1.0, "A")
        current_axes.set_facecolor("white")
        current_axes.plot(times * scale, currents * current_scale, color="#6f42a8", linewidth=2.3,
                          label="Courant de la réponse vers E")
        current_axes.axhline(0, color="#667085", linewidth=0.9)
        if times[0] <= tau <= times[-1]:
            current_axes.axvline(tau * scale, color="#667085", linestyle=":", linewidth=1.5)
        current_axes.set(xlabel=f"Temps t ({unit})", ylabel=f"Courant i ({current_unit})")
        current_axes.set_title("Convention : courant positif de la source vers le condensateur", fontsize=10, pad=10)
        current_axes.grid(True, color="#d9dee7", linewidth=0.7, alpha=0.8)
        current_axes.spines[["top", "right"]].set_visible(False)
        current_axes.legend(loc="best", framealpha=0.95)
    return figure


def save_png(figure: Figure, destination: str | Path, *, dpi: Integral = 160) -> Path:
    """Exporter une figure en PNG ; créer le dossier parent si nécessaire.

    Un fichier de même nom est remplacé. Les autres fichiers sont conservés.
    """
    path = validate_output_path(destination, extension=".png")
    if isinstance(dpi, bool) or not isinstance(dpi, Integral) or dpi <= 0:
        raise ValueError("La résolution dpi doit être un entier strictement positif.")
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, format="png", dpi=int(dpi))
    return path.resolve()

"""Validation des chemins de sortie et export CSV avec la bibliothèque standard."""

from __future__ import annotations

import csv
import os
from pathlib import Path
import tempfile

import numpy as np
from numpy.typing import ArrayLike

COLUMNS = ("time_s", "capacitor_voltage_v", "current_a")


def validate_output_path(destination: str | Path, *, extension: str) -> Path:
    """Vérifier le nom et le type de fichier d'un export PNG ou CSV.

    Le dossier parent peut manquer : save_csv() le créera après validation des
    données. Un fichier ordinaire existant peut être remplacé lors d'un succès.
    """
    kind = extension.lstrip(".").upper()
    if not isinstance(destination, (str, Path)):
        raise TypeError(f"La sortie {kind} doit être un chemin texte ou Path.")
    if not str(destination).strip() or "\x00" in str(destination):
        raise ValueError(f"Le chemin {kind} doit être non vide et sans octet nul.")
    path = Path(destination)
    if path.suffix.lower() != extension:
        raise ValueError(f"Le fichier de sortie {kind} doit porter l'extension {extension}.")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"La sortie {kind} doit désigner un fichier ordinaire, pas un répertoire ou un lien.")
    ancestor = path.parent
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise ValueError(f"Le dossier parent du {kind} doit être un répertoire.")
    return path


def validate_csv_path(destination: str | Path) -> Path:
    """Vérifier une sortie CSV avant toute écriture, sans modifier le disque."""
    return validate_output_path(destination, extension=".csv")


def save_csv(time: ArrayLike, capacitor_voltage: ArrayLike, current: ArrayLike,
             destination: str | Path) -> Path:
    """Exporter trois vecteurs réels finis de même longueur, sans les modifier.

    Temps non négatifs et strictement croissants ; un point unique est accepté.
    Les 17 chiffres significatifs permettent le retour exact en float64.
    Écrire dans un fichier temporaire voisin, puis remplacer la destination,
    conserve un CSV existant si l'écriture échoue avant ce remplacement.
    """
    path = validate_csv_path(destination)
    vectors = []
    for name, data in zip(COLUMNS, (time, capacitor_voltage, current)):
        if isinstance(data, (list, tuple)) and any(isinstance(item, (bool, np.bool_)) for item in data):
            raise TypeError(f"{name} ne doit pas contenir de booléens.")
        raw = np.asarray(data)
        if raw.ndim != 1 or raw.size == 0:
            raise ValueError(f"{name} doit être un vecteur non vide à une dimension.")
        if raw.dtype.kind not in "iuf":
            raise TypeError(f"{name} doit contenir uniquement des nombres réels.")
        with np.errstate(over="ignore"):
            values = raw.astype(np.float64)
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{name} doit contenir uniquement des valeurs finies.")
        vectors.append(values)
    times, voltages, currents = vectors
    if not (times.shape == voltages.shape == currents.shape):
        raise ValueError("Les trois colonnes CSV doivent avoir la même longueur.")
    # Comparer les voisins sans soustraction évite un débordement de np.diff.
    if np.any(times < 0.0) or np.any(times[1:] <= times[:-1]):
        raise ValueError("Les temps CSV doivent être non négatifs et strictement croissants.")

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent,
                                         prefix=f".{path.name}-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(COLUMNS)
            writer.writerows(tuple(format(float(value), ".17g") for value in row)
                             for row in zip(times, voltages, currents))
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return path.resolve()

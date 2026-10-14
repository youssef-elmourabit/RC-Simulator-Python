"""Application console : paramètres SI, modèle analytique et export PNG."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
from pathlib import Path
import sys

from rc_simulator.export import save_csv, validate_csv_path, validate_output_path
from rc_simulator.model import capacitor_voltage, circuit_current, discharge_voltage, time_constant, time_grid

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _numeric_arguments(argv: Sequence[str]) -> list[str]:
    """Préserver les nombres négatifs scientifiques que argparse prend pour des options."""
    options = {"--resistance", "--capacitance", "--voltage", "--initial-voltage",
               "--charge-initial-voltage", "--duration", "--samples"}
    result = []
    index = 0
    while index < len(argv):
        option = argv[index]
        if option in options and index + 1 < len(argv) and argv[index + 1].startswith("-"):
            value = argv[index + 1]
            try:
                float(value)
            except ValueError:
                pass
            else:
                result.append(f"{option}={value}")
                index += 2
                continue
        result.append(option)
        index += 1
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Simuler deux expériences indépendantes, puis enregistrer leur graphique."""
    parser = argparse.ArgumentParser(description="Charge et décharge d'un circuit RC idéal.")
    parser.add_argument("--resistance", type=float, default=1000.0, help="R en ohms (défaut : 1000)")
    parser.add_argument("--capacitance", type=float, default=1e-6, help="C en farads (défaut : 1e-6)")
    parser.add_argument("--voltage", type=float, default=5.0, help="Source E en volts (défaut : 5)")
    parser.add_argument("--initial-voltage", type=float, help="U0 en volts (défaut : même valeur que E)")
    parser.add_argument("--charge-initial-voltage", type=float, default=0.0,
                        help="Uc0 de la réponse vers E, en volts (défaut : 0)")
    parser.add_argument("--csv-output", type=Path,
                        help="CSV de la réponse vers E et de son courant ; fichier .csv")
    parser.add_argument("--duration", type=float, help="Durée en secondes (défaut : 5 × tau)")
    parser.add_argument("--samples", type=int, default=501, help="Nombre de points (défaut : 501)")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "figures" / "rc_charge_decharge.png",
                        help="Fichier PNG de sortie")
    args = parser.parse_args(_numeric_arguments(sys.argv[1:] if argv is None else argv))

    try:
        initial_voltage = args.voltage if args.initial_voltage is None else args.initial_voltage
        tau = time_constant(args.resistance, args.capacitance)
        times = time_grid(args.resistance, args.capacitance, duration=args.duration, samples=args.samples)
        charge = capacitor_voltage(times, args.resistance, args.capacitance,
                                   args.voltage, args.charge_initial_voltage)
        current = circuit_current(times, args.resistance, args.capacitance,
                                  args.voltage, args.charge_initial_voltage)
        discharge = discharge_voltage(times, args.resistance, args.capacitance, initial_voltage)
        # Valider les destinations avant d'écrire un export.
        validate_output_path(args.output, extension=".png")
        if args.csv_output is not None:
            validate_csv_path(args.csv_output)
        # Garder le cache graphique local ; aucune configuration globale modifiée.
        os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".cache" / "matplotlib"))
        from rc_simulator.plotting import plot_response, save_png

        description = (f"R = {args.resistance:.6g} Ω · C = {args.capacitance:.6g} F · "
                       f"E = {args.voltage:.6g} V · U₀ = {initial_voltage:.6g} V")
        plot_options = {}
        if args.charge_initial_voltage != 0.0:
            description += f" · Uc₀ = {args.charge_initial_voltage:.6g} V"
            plot_options["charge_label"] = f"Réponse vers E — Uc(0) = {args.charge_initial_voltage:.6g} V"
        figure = plot_response(times, charge, discharge, tau=tau, description=description,
                               current=current, **plot_options)
        output = save_png(figure, args.output)
        csv_output = None if args.csv_output is None else save_csv(times, charge, current, args.csv_output)
    except (TypeError, ValueError, OSError) as error:
        parser.error(str(error))

    print(f"R = {args.resistance:.6g} Ω ; C = {args.capacitance:.6g} F")
    print(f"E = {args.voltage:.6g} V ; U0 = {initial_voltage:.6g} V")
    print(f"Constante de temps τ = {tau:.6g} s")
    print(f"Intervalle : 0 à {times[-1]:.6g} s ; {len(times)} points")
    print(f"Uc0 de la réponse vers E = {args.charge_initial_voltage:.6g} V")
    print(f"Charge à τ : {capacitor_voltage(tau, args.resistance, args.capacitance, args.voltage, args.charge_initial_voltage):.6g} V")
    print(f"Décharge à τ : {discharge_voltage(tau, args.resistance, args.capacitance, initial_voltage):.6g} V")
    print(f"Graphique PNG : {output}")
    print(f"Courant initial vers le condensateur : {current[0]:.6g} A")
    if csv_output is not None:
        print(f"Résultats CSV : {csv_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

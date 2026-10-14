"""Tests du véritable point d'entrée avec des arguments et exports temporaires."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_app(args, tmp_path):
    environment = os.environ.copy()
    # Réutiliser le cache préparé lors des imports graphiques de la suite.
    # Un cache neuf à chaque sous-processus déclencherait la découverte des
    # polices macOS et ses messages, indépendants du comportement testé.
    return subprocess.run([sys.executable, str(ROOT / "src" / "main.py"), *args],
                          cwd=ROOT, env=environment, capture_output=True,
                          text=True, timeout=30, check=False)


def test_cli_default_simulation(tmp_path):
    output = tmp_path / "example.png"
    result = run_app(["--output", str(output)], tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "τ = 0.001 s" in result.stdout
    assert "501 points" in result.stdout
    assert "Charge à τ : 3.1606 V" in result.stdout
    assert "Décharge à τ : 1.8394 V" in result.stdout
    assert output.is_file()


def test_cli_independent_initial_voltage_and_negative_source(tmp_path):
    result = run_app(["--voltage", "-5", "--initial-voltage", "2",
                      "--output", str(tmp_path / "signed.png")], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "E = -5 V ; U0 = 2 V" in result.stdout
    assert "Charge à τ : -3.1606 V" in result.stdout


@pytest.mark.parametrize("args", [
    ["--resistance", "0"], ["--capacitance", "-1"], ["--voltage", "nan"],
    ["--initial-voltage", "inf"], ["--duration", "0"], ["--samples", "1"],
    ["--resistance", "abc"], ["--samples", "1.5"],
])
def test_cli_invalid_values_fail_without_export(args, tmp_path):
    output = tmp_path / "invalid.png"
    result = run_app([*args, "--output", str(output)], tmp_path)
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()

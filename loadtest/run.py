"""Enchaîne les paliers du test de charge et vérifie les critères (KAN-29).

Usage :
    python loadtest/run.py --host http://127.0.0.1:8000 --duration 60s

Critères (specifications_architecture.pdf §5.4) : p95 des pages ≤ 500 ms, aucune erreur 5xx.
Les résultats bruts (CSV Locust) et la synthèse sont écrits dans ``loadtest/results/``.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
LEVELS = (5, 20, 50)
P95_PAGES_MS = 500


def run_level(host: str, users: int, duration: str) -> list[dict[str, str]]:
    """Lance un palier Locust sans interface.

    Args:
        host: URL de l'application.
        users: Nombre d'utilisateurs simultanés.
        duration: Durée (format Locust, par ex. ``60s``).

    Returns:
        Lignes de statistiques par requête.
    """
    prefix = RESULTS / f"u{users}"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "locust",
            "-f",
            str(HERE / "locustfile.py"),
            "--headless",
            "-u",
            str(users),
            "-r",
            str(max(1, users // 5)),
            "-t",
            duration,
            "--host",
            host,
            "--csv",
            str(prefix),
            "--only-summary",
        ],
        check=False,
        env={**os.environ, "PYTHONUTF8": "1"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with open(f"{prefix}_stats.csv", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    """Point d'entrée : paliers, synthèse Markdown, code de sortie selon les critères."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    parser.add_argument("--duration", default="60s")
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)

    lines = [
        "| Utilisateurs | Requête | Nb | Échecs | Médiane (ms) | p95 (ms) | Req/s |",
        "|---|---|---|---|---|---|---|",
    ]
    ok = True
    for users in LEVELS:
        for row in run_level(args.host, users, args.duration):
            name, failures = row["Name"], int(row["Failure Count"])
            p95 = float(row["95%"] or 0)
            lines.append(
                f"| {users} | {name} | {row['Request Count']} | {failures} | {row['Median Response Time']} "
                f"| {p95:.0f} | {float(row['Requests/s']):.1f} |"
            )
            if name == "Aggregated":
                continue
            if failures or (name != "dépôt d'un rêve" and users <= 20 and p95 > P95_PAGES_MS):
                ok = False
    summary = RESULTS / "synthese.md"
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary.read_text(encoding="utf-8"))
    print("Critères respectés." if ok else "Critères NON respectés : voir la synthèse.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np
from quality_audit import compute_quality_report, THRESHOLDS

# Indicateurs recalculés dans le monitoring
MONITORED_INDICATORS = [
    'completeness_crime',
    'completeness_neighborhood',
    'uniqueness_file_number',
    'exact_duplicate_rate',
    'temporal_incoherence_rate',
    'nonconforming_reporting_area',
]

# Delta minimal (en points %) pour qualifier une évolution de significative
SIGNIFICANCE_THRESHOLD = 1.0


def compute_monitoring_report(
    df_before: pd.DataFrame,
    df_after:  pd.DataFrame,
    indicators: list = MONITORED_INDICATORS,
) -> pd.DataFrame:
    """
    Recalcule les indicateurs avant et après nettoyage.
    Retourne un DataFrame avec : before | after | delta | direction | significant | pass_after
    """
    report_before = compute_quality_report(df_before)
    report_after  = compute_quality_report(df_after)

    rows = []
    for ind in indicators:
        val_before = report_before.get(ind, np.nan)
        val_after  = report_after.get(ind, np.nan)

        if pd.isna(val_before) or pd.isna(val_after):
            delta, direction, significant = np.nan, 'n/a', False
        else:
            delta       = round(val_after - val_before, 2)
            direction   = 'up' if delta > 0 else ('down' if delta < 0 else 'stable')
            significant = abs(delta) >= SIGNIFICANCE_THRESHOLD

        # Vérification du seuil post-nettoyage
        thr_info = THRESHOLDS.get(ind)
        if thr_info and not pd.isna(val_after):
            op, thr, _ = thr_info
            pass_after = val_after >= thr if op == '>=' else val_after <= thr
        else:
            thr, pass_after = None, None

        rows.append({
            'indicator'  : ind,
            'before'     : val_before,
            'after'      : val_after,
            'delta'      : delta,
            'direction'  : direction,
            'significant': significant,
            'threshold'  : thr,
            'pass_after' : pass_after,
        })

    return pd.DataFrame(rows).set_index('indicator')


def print_monitoring_report(report: pd.DataFrame) -> None:
    """Affiche le rapport de monitoring avant/après dans la console."""
    arrows = {'up': '▲', 'down': '▼', 'stable': '=', 'n/a': '?'}

    print("=" * 70)
    print("MONITORING — COMPARAISON AVANT / APRÈS NETTOYAGE")
    print("=" * 70)
    print(f"  {'Indicateur':<38}  {'Avant':>7}    {'Après':>7}   {'Δ':>7}  Seuil")
    print("  " + "-" * 66)

    for ind, row in report.iterrows():
        arrow    = arrows.get(row['direction'], '?')
        sig_tag  = ' ★' if row['significant'] else '  '
        pass_tag = ' PASS' if row['pass_after'] is True else (' FAIL' if row['pass_after'] is False else '     ')
        print(
            f"  {ind:<38}"
            f"  {row['before']:>7.2f}%"
            f"  {arrow}"
            f"  {row['after']:>7.2f}%"
            f"  ({row['delta']:+.2f})"
            f"{sig_tag}{pass_tag}"
        )

    print()
    sig_count   = report['significant'].sum()
    pass_count  = (report['pass_after'] == True).sum()
    total_thr   = report['pass_after'].notna().sum()
    print(f"  ★ {sig_count} indicateur(s) avec évolution significative (|Δ| ≥ {SIGNIFICANCE_THRESHOLD} pt)")
    print(f"  ✓ {pass_count}/{total_thr} indicateurs respectent leur seuil après nettoyage")
import pandas as pd
from quality_audit import compute_quality_report, evaluate_thresholds
from treatment    import run_treatment_pipeline, export_clean_dataset
from monitoring   import compute_monitoring_report, print_monitoring_report
from map          import aggregate_crimes, load_geojson, join_data, export_map

# ── Chargement ────────────────────────────────────────────────────────────────

df = pd.read_csv('../data/crime_reports_broken.csv')

# ── 1. Profilage et exploration ───────────────────────────────────────────────

print("=" * 60)
print(f"Lignes : {df.shape[0]}, Colonnes : {df.shape[1]}")
print("=" * 60)
print(df.dtypes)
print("=" * 60)
print(df.isnull().sum())
print("=" * 60)
print(df.head())

# ── 2. Audit de la qualité (avant traitement) ─────────────────────────────────

print("=" * 60)
print("RAPPORT QUALITÉ — crime_reports_broken.csv")
print("=" * 60)

report_before = compute_quality_report(df)

print("\n── Indicateurs bruts ──────────────────────────────────────")
print(report_before.to_string())

print("\n── Évaluation des seuils ──────────────────────────────────")
eval_df = evaluate_thresholds(report_before)
print(eval_df[['value_%', 'operator', 'threshold', 'pass', 'rationale']].to_string())

n_pass  = eval_df['pass'].sum()
n_total = len(eval_df)
print(f"\n→ {n_pass}/{n_total} indicateurs respectent leur seuil d'acceptation.")

# ── 3. Traitement ─────────────────────────────────────────────────────────────

df_clean = run_treatment_pipeline(df)
export_clean_dataset(df_clean)

print("\n── Aperçu du dataset nettoyé ──────────────────────────────")
print(df_clean.head(10).to_string())

print("\n── Valeurs manquantes résiduelles ─────────────────────────")
print(df_clean.isnull().sum().to_string())

print("\n── Distribution reporting_area_group ──────────────────────")
print(df_clean['reporting_area_group'].value_counts().sort_index().to_string())

# ── 4. Monitoring — comparaison avant / après ─────────────────────────────────

monitoring = compute_monitoring_report(df, df_clean)
print_monitoring_report(monitoring)

print("\n── Indicateurs significativement améliorés ─────────────────")
sig = monitoring[monitoring['significant']]
if len(sig):
    print(sig[['before', 'after', 'delta', 'pass_after']].to_string())
else:
    print("  Aucun indicateur significativement modifié.")

# ── 5. Cartographie — choroplèthe des crimes par quartier ────────────────────

GEOJSON_URL = (
    'https://raw.githubusercontent.com/cambridgegis/'
    'cambridgegis_data/main/Boundary/CDD_Neighborhoods/'
    'BOUNDARY_CDDNeighborhoods.geojson'
)

crimes          = aggregate_crimes('../data/crime_reports_clean.csv')
geojson, nc     = load_geojson(GEOJSON_URL)
geojson         = join_data(geojson, nc, crimes)
export_map(geojson, nc, '../data/map.html')
import pandas as pd
import numpy as np

# ── Référentiel officiel des quartiers ────────────────────────────────────────

VALID_NEIGHBORHOODS = {
    "Cambridgeport", "East Cambridge", "Mid-Cambridge", "North Cambridge",
    "Riverside", "Area 4", "West Cambridge", "Peabody", "Inman/Harrington",
    "Highlands", "Agassiz", "MIT", "Strawberry Hill",
}

MAX_AREA_GROUP = 20  # groupe de centaines max acceptable


# ── Helpers internes ──────────────────────────────────────────────────────────

def _parse_crime_start(val):
    """Extrait la borne de début de Crime Date Time."""
    if pd.isna(val):
        return pd.NaT
    part = str(val).strip().split(' - ')[0].strip()
    try:
        return pd.to_datetime(part, dayfirst=False)
    except Exception:
        return pd.NaT


def _to_int_area(val):
    """Convertit Reporting Area en int si valide, sinon None."""
    if pd.isna(val):
        return None
    try:
        num = float(val)
        if num > 0 and num == int(num):
            return int(num)
    except (ValueError, TypeError):
        pass
    return None


# ── Copie de travail ──────────────────────────────────────────────────────────

def make_working_copy(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne une copie indépendante du DataFrame original."""
    return df.copy()


# ── Règles de traitement ──────────────────────────────────────────────────────

def fix_duplicate_file_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Règle : ID unique en doublon.
    Stratégie : conserver la première occurrence, supprimer les suivantes.
    """
    mask = df.duplicated(subset=['File Number'], keep='first')
    n = mask.sum()
    if n:
        print(f"  [ID doublon]       {n} ligne(s) supprimée(s) (File Number dupliqué)")
    return df[~mask].reset_index(drop=True)


def fix_null_crime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Règle : Crime null.
    Stratégie : imputer 'Unknown' pour conserver la ligne.
    """
    mask = df['Crime'].isna()
    n = mask.sum()
    if n:
        print(f"  [Crime null]       {n} valeur(s) imputée(s) → 'Unknown'")
    df.loc[mask, 'Crime'] = 'Unknown'
    return df


def fix_invalid_date_of_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Règle : Date of Report invalide.
    Stratégie : parser en datetime, supprimer les lignes non parsables (NaT).
    """
    df['Date of Report'] = pd.to_datetime(
        df['Date of Report'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce'
    )
    mask = df['Date of Report'].isna()
    n = mask.sum()
    if n:
        print(f"  [Date invalide]    {n} ligne(s) supprimée(s) (Date of Report non parsable)")
    return df[~mask].reset_index(drop=True)


def fix_temporal_incoherence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Règle : Date of Report antérieure au début de Crime Date Time.
    Stratégie : supprimer les lignes incohérentes.
    Pré-requis : 'Date of Report' doit déjà être en datetime.
    """
    crime_starts = df['Crime Date Time'].apply(_parse_crime_start)
    mask_valid   = df['Date of Report'].notna() & crime_starts.notna()
    mask_incoher = mask_valid & (df['Date of Report'] < crime_starts)
    n = mask_incoher.sum()
    if n:
        print(f"  [Incohérence temp] {n} ligne(s) supprimée(s) (rapport avant crime)")
    return df[~mask_incoher].reset_index(drop=True)


def fix_invalid_reporting_area(df: pd.DataFrame) -> pd.DataFrame:
    """
    Règle : Reporting Area invalide.
    Stratégie : convertir en int si valide, NaN sinon (pas de suppression).
    """
    converted = df['Reporting Area'].apply(_to_int_area)
    n_bad = max(converted.isna().sum() - df['Reporting Area'].isna().sum(), 0)
    if n_bad:
        print(f"  [Reporting Area]   {n_bad} valeur(s) non conforme(s) → NaN")
    df['Reporting Area'] = converted
    return df


def fix_invalid_neighborhood(df: pd.DataFrame) -> pd.DataFrame:
    """
    Règle : Neighborhood hors référentiel officiel.
    Stratégie : remplacer par NaN (pas de suppression).
    """
    mask_bad = ~(df['Neighborhood'].isna() | df['Neighborhood'].isin(VALID_NEIGHBORHOODS))
    n = mask_bad.sum()
    if n:
        bad_vals = df.loc[mask_bad, 'Neighborhood'].unique().tolist()
        print(f"  [Neighborhood]     {n} valeur(s) hors référentiel → NaN")
        print(f"                     Valeurs : {bad_vals}")
    df.loc[mask_bad, 'Neighborhood'] = np.nan
    return df


# ── Enrichissement ────────────────────────────────────────────────────────────

def add_reporting_area_group(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrichissement : groupe de centaines de Reporting Area.
    Ex : 602 → 6 | 1109 → 11 | 403 → 4
    Valeurs aberrantes (≤ 0 ou > MAX_AREA_GROUP) → NaN.
    """
    def extract_group(val):
        if pd.isna(val):
            return np.nan
        try:
            g = int(val) // 100
            return g if 1 <= g <= MAX_AREA_GROUP else np.nan
        except (ValueError, TypeError):
            return np.nan

    df['reporting_area_group'] = df['Reporting Area'].apply(extract_group)
    groups = df['reporting_area_group'].dropna()
    n_aberrant = ((groups <= 0) | (groups > MAX_AREA_GROUP)).sum()

    print(f"\n  [Enrichissement]   reporting_area_group créée")
    print(f"                     Groupes : {sorted(groups.unique().astype(int).tolist())}")
    if n_aberrant:
        print(f"                     {n_aberrant} valeur(s) aberrante(s) → NaN")
    else:
        print(f"                     Aucune valeur aberrante (seuil 1–{MAX_AREA_GROUP})")
    return df


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_treatment_pipeline(df_original: pd.DataFrame) -> pd.DataFrame:
    """
    Applique toutes les règles sur une copie du DataFrame.
    Retourne le DataFrame nettoyé et enrichi.
    """
    print("=" * 60)
    print("PIPELINE DE TRAITEMENT")
    print("=" * 60)
    print(f"\n  Lignes initiales   : {len(df_original)}")
    print("\n── Règles de traitement ───────────────────────────────────")

    df = make_working_copy(df_original)
    df = fix_duplicate_file_numbers(df)
    df = fix_null_crime(df)
    df = fix_invalid_date_of_report(df)
    df = fix_temporal_incoherence(df)
    df = fix_invalid_reporting_area(df)
    df = fix_invalid_neighborhood(df)
    df = add_reporting_area_group(df)

    print(f"\n── Résumé ─────────────────────────────────────────────────")
    print(f"  Lignes finales     : {len(df)}")
    print(f"  Lignes supprimées  : {len(df_original) - len(df)}")
    print(f"  Colonnes           : {list(df.columns)}")
    return df


# ── Export ────────────────────────────────────────────────────────────────────

def export_clean_dataset(df: pd.DataFrame, path: str = '../data/crime_reports_clean.csv') -> None:
    """Exporte le DataFrame nettoyé en CSV UTF-8 sans index."""
    df.to_csv(path, index=False, encoding='utf-8')
    print(f"\n  [Export]           Fichier sauvegardé → {path}")
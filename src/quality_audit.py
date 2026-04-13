import pandas as pd
import numpy as np

# ── Helper ────────────────────────────────────────────────────────────────────

def _pct(num, den):
    """Pourcentage arrondi à 2 décimales, 0 si dénominateur nul."""
    return round(100 * num / den, 2) if den else 0.0


# ── 1. Complétude ─────────────────────────────────────────────────────────────

def completeness(df: pd.DataFrame, col: str) -> float:
    """% de valeurs non nulles dans une colonne."""
    return _pct(df[col].notna().sum(), len(df))


# ── 2. Unicité de File Number ─────────────────────────────────────────────────

def uniqueness_file_number(df: pd.DataFrame) -> float:
    """% de valeurs uniques dans File Number (sur les non-nulles)."""
    series = df['File Number'].dropna()
    return _pct(series.nunique(), len(series))


# ── 3. Taux de doublons exacts ────────────────────────────────────────────────

def exact_duplicate_rate(df: pd.DataFrame) -> float:
    """% de lignes strictement dupliquées."""
    return _pct(df.duplicated(keep='first').sum(), len(df))


# ── 4. Taux de dates invalides ────────────────────────────────────────────────

def invalid_date_rate(df: pd.DataFrame) -> float:
    """% de valeurs non parsables dans Date of Report."""
    def is_invalid(val):
        if pd.isna(val):
            return True
        try:
            pd.to_datetime(val)
            return False
        except Exception:
            return True
    return _pct(df['Date of Report'].apply(is_invalid).sum(), len(df))


# ── 5. Incohérences temporelles ───────────────────────────────────────────────

def _parse_crime_start(val):
    """Extrait la borne de début de Crime Date Time (intervalle ou instant)."""
    if pd.isna(val):
        return None
    part = str(val).strip().split(' - ')[0].strip()
    try:
        return pd.to_datetime(part, dayfirst=False)
    except Exception:
        return None


def temporal_incoherence_rate(df: pd.DataFrame) -> float:
    """% de lignes où Date of Report est antérieure au début de Crime Date Time."""
    report_dates = pd.to_datetime(
        df['Date of Report'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce'
    )
    crime_starts = df['Crime Date Time'].apply(_parse_crime_start)
    mask_valid   = report_dates.notna() & crime_starts.notna()
    valid_report = report_dates[mask_valid]
    valid_crime  = pd.Series(crime_starts[mask_valid].values, index=valid_report.index)
    return _pct((valid_report < valid_crime).sum(), mask_valid.sum())


# ── 6. Conformité Reporting Area ──────────────────────────────────────────────

def nonconforming_reporting_area(df: pd.DataFrame) -> float:
    """% de valeurs non nulles dans Reporting Area qui ne sont pas des entiers positifs."""
    def is_nonconforming(val):
        if pd.isna(val):
            return False
        try:
            num = float(val)
            return not (num > 0 and num == int(num))
        except (ValueError, TypeError):
            return True
    series = df['Reporting Area'].dropna()
    return _pct(series.apply(is_nonconforming).sum(), len(series))


# ── Rapport global ────────────────────────────────────────────────────────────

def compute_quality_report(df: pd.DataFrame) -> pd.Series:
    """Calcule tous les indicateurs et retourne un pd.Series indexé par nom."""
    return pd.Series({
        'completeness_file_number'    : completeness(df, 'File Number'),
        'completeness_crime'          : completeness(df, 'Crime'),
        'completeness_neighborhood'   : completeness(df, 'Neighborhood'),
        'uniqueness_file_number'      : uniqueness_file_number(df),
        'exact_duplicate_rate'        : exact_duplicate_rate(df),
        'invalid_date_rate'           : invalid_date_rate(df),
        'temporal_incoherence_rate'   : temporal_incoherence_rate(df),
        'nonconforming_reporting_area': nonconforming_reporting_area(df),
    }, name='value_%')


# ── Seuils d'acceptation ──────────────────────────────────────────────────────

THRESHOLDS = {
    'completeness_file_number'    : ('>=', 100.0, 'Clé primaire — aucun manquant toléré'),
    'completeness_crime'          : ('>=',  95.0, 'Variable analytique centrale'),
    'completeness_neighborhood'   : ('>=',  95.0, 'Requis pour l\'analyse géographique'),
    'uniqueness_file_number'      : ('>=', 100.0, 'Identifiant unique — aucun doublon'),
    'exact_duplicate_rate'        : ('<=',   0.5, 'Tolérance minimale sur doublons'),
    'invalid_date_rate'           : ('<=',   1.0, 'Dates parsables requises'),
    'temporal_incoherence_rate'   : ('<=',   2.0, 'Seuil d\'alerte sur incohérences logiques'),
    'nonconforming_reporting_area': ('<=',   2.0, 'Codes zone doivent être des entiers positifs'),
}


def evaluate_thresholds(report: pd.Series) -> pd.DataFrame:
    """Compare les indicateurs aux seuils. Retourne un DataFrame avec colonne pass."""
    rows = []
    for indicator, (op, threshold, rationale) in THRESHOLDS.items():
        value = report.get(indicator, None)
        if value is None:
            passed = None
        elif op == '>=':
            passed = value >= threshold
        else:
            passed = value <= threshold
        rows.append({
            'indicator' : indicator,
            'value_%'   : value,
            'operator'  : op,
            'threshold' : threshold,
            'pass'      : passed,
            'rationale' : rationale,
        })
    return pd.DataFrame(rows).set_index('indicator')
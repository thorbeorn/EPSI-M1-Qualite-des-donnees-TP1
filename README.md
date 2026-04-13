# 🔍 Crime Reports — Analyse de Qualité des Données

Analyse exploratoire, audit qualité, nettoyage et monitoring du dataset `crime_reports_broken.csv` contenant des rapports de crimes enregistrés à Cambridge, MA.

---

## 📁 Structure du projet

```
projet/
├── data/
│   ├── crime_reports_broken.csv   # Dataset source (brut, non nettoyé)
│   ├── crime_reports_clean.csv    # Dataset nettoyé (généré par le pipeline)
│   └── map.html                   # Carte choroplèthe exportée (générée par map.py)
├── src/
│   ├── main.py                    # Point d'entrée — orchestre les 4 étapes
│   ├── quality_audit.py           # Indicateurs de qualité et seuils
│   ├── treatment.py               # Règles de nettoyage et enrichissement
│   ├── monitoring.py              # Comparaison avant / après nettoyage
│   └── map.py                     # Carte choroplèthe des crimes par quartier
└── README.md
```

---

## 🚀 Lancement

```bash
# Activer l'environnement virtuel
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'analyse complète depuis src/
cd src
python main.py

# Générer la carte choroplèthe (produit data/map.html)
python map.py
```

---

## 📊 Description du dataset

| Propriété | Valeur |
|-----------|--------|
| Lignes | 10 506 |
| Colonnes | 7 |
| Valeurs manquantes | 1 507 (14,3%) |
| Types inférés | `str` × 7 (aucun type natif) |

### Variables

| Nom | Type pandas | Type attendu | Manquants | Description |
|-----|-------------|--------------|-----------|-------------|
| `File Number` | str | str | 0 | Identifiant unique du rapport (format `AAAA-NNNNN`) |
| `Date of Report` | str | datetime | 0 | Date et heure de dépôt du rapport officiel |
| `Crime Date Time` | str | str (mixte) | 0 | Date/heure du crime — instant précis ou plage horaire |
| `Crime` | str | category | 525 (5,0%) | Type de crime commis |
| `Reporting Area` | str | int | 26 (0,2%) | Code numérique de la zone de signalement |
| `Neighborhood` | str | category | 717 (6,8%) | Quartier où le crime a été commis |
| `Location` | str | str | 239 (2,3%) | Adresse textuelle du lieu du crime |

---

## ⚠️ Problèmes de qualité identifiés

### 1. 🔴 Typage incorrect généralisé
Toutes les colonnes sont inférées comme `str` par pandas. Plusieurs colonnes nécessitent une conversion :
- `Date of Report` → `datetime`
- `Reporting Area` → `int` (actuellement stocké comme `"403.0"`)
- `Crime`, `Neighborhood` → `category`

### 2. 🟡 Format hétérogène dans `Crime Date Time`
La colonne mélange deux formats distincts :
- Intervalle : `"04/13/2016 20:00 - 04/14/2016 06:30"`
- Instant unique : `"04/21/2016 12:15"`

Un parser personnalisé extrait la borne de début pour les comparaisons temporelles.

### 3. 🔵 Valeurs manquantes critiques
- `Neighborhood` : **717 valeurs manquantes (6,8%)**
- `Crime` : **525 valeurs manquantes (5,0%)**

### 4. 🟣 Casse incohérente dans `Location`
```
100 HARVARD ST, Cambridge, MA   ← MAJUSCULES
100 Broadway, Cambridge, MA     ← Casse mixte
```

---

## 🔬 Audit qualité — Résultats avant nettoyage

| Indicateur | Valeur | Seuil | Statut |
|------------|--------|-------|--------|
| `completeness_file_number` | 100,00% | ≥ 100% | ✅ PASS |
| `completeness_crime` | 95,00% | ≥ 95% | ✅ PASS |
| `completeness_neighborhood` | 93,18% | ≥ 95% | ❌ FAIL |
| `uniqueness_file_number` | 95,18% | ≥ 100% | ❌ FAIL |
| `exact_duplicate_rate` | 1,94% | ≤ 0,5% | ❌ FAIL |
| `invalid_date_rate` | 0,98% | ≤ 1% | ✅ PASS |
| `temporal_incoherence_rate` | 3,83% | ≤ 2% | ❌ FAIL |
| `nonconforming_reporting_area` | 1,04% | ≤ 2% | ✅ PASS |

**→ 4/8 indicateurs respectaient leur seuil avant nettoyage.**

---

## 🧹 Pipeline de nettoyage

| Règle | Stratégie | Impact |
|-------|-----------|--------|
| ID doublon (`File Number`) | Suppression — garder 1ère occurrence | 506 lignes supprimées |
| `Crime` null | Imputation → `'Unknown'` | 496 valeurs imputées |
| `Date of Report` invalide | Suppression (NaT non parsable) | 99 lignes supprimées |
| Incohérence temporelle | Suppression (rapport avant crime) | 316 lignes supprimées |
| `Reporting Area` invalide | Conversion → `NaN` (ligne conservée) | 100 valeurs nullifiées |
| `Neighborhood` hors référentiel | Remplacement → `NaN` | 187 valeurs nullifiées (`'???'`, `'Cambrigeport'`, `'N-A'`, `'Unknown'`, `'not_specified'`) |

**Résultat : 10 506 → 9 585 lignes (921 lignes supprimées, −8,8%)**

### Enrichissement — `reporting_area_group`

Nouvelle colonne extraite par groupe de centaines de `Reporting Area` :

```
403 → 4 | 708 → 7 | 1002 → 10
```

Groupes présents : `1` à `13` — aucune valeur aberrante détectée.

---

## 📈 Monitoring — Comparaison avant / après nettoyage

| Indicateur | Avant | Après | Δ | Significatif | Seuil |
|------------|-------|-------|---|:---:|-------|
| `completeness_crime` | 95,00% | 100,00% | **+5,00** | ★ | ✅ PASS |
| `completeness_neighborhood` | 93,18% | 91,21% | **−1,97** | ★ | ❌ FAIL |
| `uniqueness_file_number` | 95,18% | 100,00% | **+4,82** | ★ | ✅ PASS |
| `exact_duplicate_rate` | 1,94% | 0,00% | **−1,94** | ★ | ✅ PASS |
| `temporal_incoherence_rate` | 3,83% | 0,00% | **−3,83** | ★ | ✅ PASS |
| `nonconforming_reporting_area` | 1,04% | 0,00% | **−1,04** | ★ | ✅ PASS |

> Seuil de significativité : |Δ| ≥ 1,0 point de pourcentage.

**→ 6/6 indicateurs ont une évolution significative. 5/6 respectent leur seuil après nettoyage.**

### Analyse des évolutions significatives

**Améliorations majeures :**

- `temporal_incoherence_rate` : **−3,83 pts** → 0,00% — toutes les incohérences logiques éliminées par suppression des lignes où le rapport précédait le crime.
- `completeness_crime` : **+5,00 pts** → 100,00% — les 496 valeurs nulles imputées à `'Unknown'` amènent la complétude à 100%.
- `uniqueness_file_number` : **+4,82 pts** → 100,00% — les 506 doublons de `File Number` supprimés garantissent l'unicité totale.
- `exact_duplicate_rate` : **−1,94 pts** → 0,00% — taux de doublons ramené à zéro.
- `nonconforming_reporting_area` : **−1,04 pts** → 0,00% — toutes les valeurs non conformes converties en `NaN`.

**Point de vigilance :**

- `completeness_neighborhood` : **−1,97 pts** (93,18% → 91,21%) — la complétude a baissé après nettoyage. Les 187 valeurs hors référentiel (`'Cambrigeport'`, `'N-A'`, etc.) ont été correctement nullifiées, ce qui augmente mécaniquement le taux de manquants. Ce recul est **attendu et souhaitable** : il reflète une meilleure conformité au référentiel officiel, non une dégradation de la qualité réelle.

---

## 🗺️ Cartographie — Choroplèthe des crimes par quartier

Le script `src/map.py` produit une carte interactive au format HTML (`data/map.html`) représentant la répartition des crimes par quartier, à partir du dataset nettoyé.

### Pipeline cartographique

1. **Agrégation** — calcul du nombre de crimes par `Neighborhood` (lignes avec valeur renseignée uniquement). Vérification que `n_avec_quartier + n_sans_quartier = n_total_lignes`.
2. **Référentiel géographique** — récupération du fichier `BOUNDARY_CDDNeighborhoods.geojson` via l'API GitHub de Cambridge GIS. Colonnes utilisées : `NAME` (nom du quartier) et `OBJECTID` (code interne). En cas d'indisponibilité réseau, un GeoJSON embarqué des 13 quartiers officiels prend le relais.
3. **Jointure** — appariement sur le nom du quartier (`NAME` ↔ `Neighborhood`). Vérification de l'absence de quartiers orphelins (sans crimes ou sans polygone).
4. **Export HTML** — carte Leaflet interactive avec gradient vert → jaune → rouge, légende et tooltip au survol (nom du quartier, nombre de crimes, part en %).

```bash
cd src
python map.py
# → Carte générée dans data/map.html
```

---

## ❓ Pourquoi le terme « quartier le plus dangereux » peut-il être trompeur avec un indicateur en volume brut ?

Un classement basé sur le **nombre absolu de crimes** mesure davantage la taille et l'activité d'un quartier que son niveau de dangerosité réelle.

**Trois biais principaux :**

1. **Biais de population.** Un quartier dense (30 000 habitants) peut enregistrer 1 800 crimes là où un quartier résidentiel (2 000 habitants) n'en compte que 200 — le taux pour 1 000 habitants est pourtant identique (60 ‰). Le volume brut pénalise mécaniquement les grandes zones.

2. **Biais de superficie.** Un quartier étendu avec beaucoup de voies publiques, commerces et passages attire statistiquement plus de signalements. La densité criminelle par km² serait un indicateur plus comparable.

3. **Biais d'exposition.** Certains quartiers concentrent des lieux à forte fréquentation (gares, universités, centres commerciaux) qui génèrent des incidents sans que les résidents permanents soient davantage exposés. Le volume de crimes reflète alors le flux de personnes, pas le risque individuel.

**Indicateurs alternatifs recommandés :**

| Indicateur | Formule | Intérêt |
|------------|---------|---------|
| Taux de criminalité | Crimes / population × 1 000 | Neutralise la taille démographique |
| Densité criminelle | Crimes / superficie (km²) | Neutralise l'effet géographique |
| Indice de gravité | Pondération par type de crime | Distingue infractions mineures et graves |

> En résumé : qualifier un quartier de « le plus dangereux » sur la seule base du volume brut revient à confondre *taille* et *risque*. Une communication publique responsable doit préciser l'indicateur utilisé et ses limites.
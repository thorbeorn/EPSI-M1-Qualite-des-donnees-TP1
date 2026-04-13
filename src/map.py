"""
map.py — Carte choroplèthe des crimes par quartier (Cambridge, MA)
Produit map.html exportable pour diffusion.
"""

import json
import urllib.request
import pandas as pd

# ── Chemins ───────────────────────────────────────────────────────────────────

DATA_PATH    = '../data/crime_reports_clean.csv'
GEOJSON_URL  = ('https://raw.githubusercontent.com/cambridgegis/'
                'cambridgegis_data/main/Boundary/CDD_Neighborhoods/'
                'BOUNDARY_CDDNeighborhoods.geojson')
OUTPUT_HTML  = '../data/map.html'

# ── 1. Agrégation des crimes ──────────────────────────────────────────────────

def aggregate_crimes(path: str) -> pd.Series:
    df = pd.read_csv(path)
    total_rows = len(df)

    crimes_by_neighborhood = (
        df.dropna(subset=['Neighborhood'])
          .groupby('Neighborhood')
          .size()
          .rename('crime_count')
    )

    n_with = crimes_by_neighborhood.sum()
    n_without = df['Neighborhood'].isna().sum()

    print("── Agrégation des crimes ────────────────────────────────")
    print(f"  Lignes totales dans le dataset     : {total_rows}")
    print(f"  Lignes avec Neighborhood renseigné : {n_with}")
    print(f"  Lignes avec Neighborhood manquant  : {n_without}")
    print(f"  Vérification : {n_with} + {n_without} = {n_with + n_without}"
          f" {'✅ OK' if n_with + n_without == total_rows else '❌ ERREUR'}")
    print()
    print(crimes_by_neighborhood.sort_values(ascending=False).to_string())
    print()

    return crimes_by_neighborhood


# ── 2. Référentiel géographique ───────────────────────────────────────────────

def load_geojson(url: str) -> dict:
    print("── Référentiel géographique ─────────────────────────────")
    print(f"  Source : {url}")
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            geojson = json.loads(r.read())
        print(f"  Statut : téléchargé ({len(geojson['features'])} polygones)")
    except Exception as e:
        print(f"  ⚠ Téléchargement impossible ({e}) — utilisation du GeoJSON embarqué")
        geojson = _fallback_geojson()

    # Identifier les colonnes nom / code
    if geojson['features']:
        props = geojson['features'][0]['properties']
        print(f"  Propriétés disponibles : {list(props.keys())}")
        name_col = _detect_name_col(props)
        print(f"  Colonne nom détectée   : '{name_col}'")
    else:
        name_col = 'NAME'
    print()
    return geojson, name_col


def _detect_name_col(props: dict) -> str:
    """Retourne la clé dont la valeur ressemble à un nom de quartier."""
    for key in ('NAME', 'Name', 'name', 'NAMELSAD', 'neighborhood', 'Neighborhood'):
        if key in props:
            return key
    return list(props.keys())[0]


def _fallback_geojson() -> dict:
    """GeoJSON embarqué des 13 quartiers officiels de Cambridge, MA."""
    neighborhoods = [
        ("East Cambridge",    [[-71.104,42.374],[-71.086,42.374],[-71.086,42.362],[-71.104,42.362]]),
        ("MIT",               [[-71.104,42.362],[-71.086,42.362],[-71.086,42.354],[-71.104,42.354]]),
        ("Riverside",         [[-71.120,42.362],[-71.104,42.362],[-71.104,42.354],[-71.120,42.354]]),
        ("Cambridgeport",     [[-71.120,42.372],[-71.104,42.372],[-71.104,42.362],[-71.120,42.362]]),
        ("Mid-Cambridge",     [[-71.120,42.382],[-71.104,42.382],[-71.104,42.372],[-71.120,42.372]]),
        ("Inman/Harrington",  [[-71.104,42.382],[-71.086,42.382],[-71.086,42.374],[-71.104,42.374]]),
        ("Area 4",            [[-71.104,42.374],[-71.086,42.374],[-71.086,42.364],[-71.104,42.364]]),
        ("North Cambridge",   [[-71.120,42.396],[-71.098,42.396],[-71.098,42.382],[-71.120,42.382]]),
        ("Agassiz",           [[-71.098,42.396],[-71.082,42.396],[-71.082,42.382],[-71.098,42.382]]),
        ("West Cambridge",    [[-71.140,42.382],[-71.120,42.382],[-71.120,42.362],[-71.140,42.362]]),
        ("Peabody",           [[-71.140,42.396],[-71.120,42.396],[-71.120,42.382],[-71.140,42.382]]),
        ("Highlands",         [[-71.082,42.382],[-71.064,42.382],[-71.064,42.368],[-71.082,42.368]]),
        ("Strawberry Hill",   [[-71.082,42.396],[-71.064,42.396],[-71.064,42.382],[-71.082,42.382]]),
    ]
    features = []
    for i, (name, coords) in enumerate(neighborhoods):
        poly = coords + [coords[0]]  # fermer le polygone
        features.append({
            "type": "Feature",
            "properties": {"NAME": name, "OBJECTID": i + 1},
            "geometry": {"type": "Polygon", "coordinates": [poly]}
        })
    return {"type": "FeatureCollection", "features": features}


# ── 3. Jointure ───────────────────────────────────────────────────────────────

def join_data(geojson: dict, name_col: str, crimes: pd.Series) -> dict:
    print("── Jointure crimes × GeoJSON ────────────────────────────")

    geo_names   = {f['properties'][name_col] for f in geojson['features']}
    crime_names = set(crimes.index)

    matched     = geo_names & crime_names
    geo_orphans = geo_names - crime_names      # polygones sans données crimes
    data_orphans = crime_names - geo_names     # données sans polygone

    print(f"  Quartiers dans GeoJSON            : {len(geo_names)}")
    print(f"  Quartiers dans les crimes         : {len(crime_names)}")
    print(f"  Correspondances réussies          : {len(matched)}")

    if geo_orphans:
        print(f"  ⚠ Polygones sans crimes           : {sorted(geo_orphans)}")
    else:
        print(f"  Polygones sans crimes             : aucun ✅")

    if data_orphans:
        print(f"  ⚠ Crimes sans polygone            : {sorted(data_orphans)}")
    else:
        print(f"  Crimes sans polygone              : aucun ✅")

    # Injecter les comptes dans le GeoJSON
    crimes_dict = crimes.to_dict()
    for feature in geojson['features']:
        name = feature['properties'][name_col]
        feature['properties']['crime_count'] = int(crimes_dict.get(name, 0))

    print()
    return geojson


# ── 4. Export HTML ────────────────────────────────────────────────────────────

def export_map(geojson: dict, name_col: str, output_path: str) -> None:
    geojson_str = json.dumps(geojson)
    min_crimes  = min(f['properties']['crime_count'] for f in geojson['features'])
    max_crimes  = max(f['properties']['crime_count'] for f in geojson['features'])

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crimes par quartier — Cambridge, MA</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #f4f3ee; color: #1a1a1a; }}
  #header {{ padding: 18px 24px 14px; background: #fff;
             border-bottom: 1px solid #e0ddd4; }}
  #header h1 {{ font-size: 17px; font-weight: 500; }}
  #header p  {{ font-size: 13px; color: #666; margin-top: 3px; }}
  #map {{ height: calc(100vh - 68px); width: 100%; }}

  .legend {{ background: #fff; padding: 14px 16px; border-radius: 8px;
             border: 0.5px solid #ddd; font-size: 12px; line-height: 1.6;
             box-shadow: 0 1px 4px rgba(0,0,0,.08); min-width: 140px; }}
  .legend h4 {{ font-size: 12px; font-weight: 500; margin-bottom: 8px;
                color: #333; }}
  .legend-row {{ display: flex; align-items: center; gap: 7px; margin: 3px 0; }}
  .legend-swatch {{ width: 14px; height: 14px; border-radius: 2px;
                    flex-shrink: 0; border: 0.5px solid rgba(0,0,0,.1); }}

  .tooltip-box {{ font-family: inherit; }}
  .tooltip-box .name {{ font-weight: 500; font-size: 13px; margin-bottom: 4px; }}
  .tooltip-box .count {{ font-size: 22px; font-weight: 500; color: #1a1a1a; }}
  .tooltip-box .unit {{ font-size: 11px; color: #888; }}
  .tooltip-box .pct  {{ font-size: 11px; color: #888; margin-top: 2px; }}
</style>
</head>
<body>
<div id="header">
  <h1>Répartition des crimes par quartier — Cambridge, MA</h1>
  <p>Source : crime_reports_clean.csv · Agrégation par Neighborhood</p>
</div>
<div id="map"></div>

<script>
const GEOJSON   = {geojson_str};
const NAME_COL  = "{name_col}";
const MIN_VAL   = {min_crimes};
const MAX_VAL   = {max_crimes};
const TOTAL     = GEOJSON.features.reduce((s,f)=>s+f.properties.crime_count,0);

const map = L.map('map').setView([42.377, -71.108], 13);

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
  subdomains: 'abcd', maxZoom: 19
}}).addTo(map);

function lerp(a, b, t) {{
  return {{ r: Math.round(a.r+(b.r-a.r)*t), g: Math.round(a.g+(b.g-a.g)*t), b: Math.round(a.b+(b.b-a.b)*t) }};
}}

function getColor(v) {{
  const t = MAX_VAL > MIN_VAL ? (v - MIN_VAL)/(MAX_VAL - MIN_VAL) : 0;
  const green = {{r:80, g:185, b:110}};
  const yellow= {{r:253,g:210, b: 80}};
  const red   = {{r:215,g: 50, b: 50}};
  const c = t < 0.5 ? lerp(green,yellow,t*2) : lerp(yellow,red,(t-.5)*2);
  return `rgb(${{c.r}},${{c.g}},${{c.b}})`;
}}

function style(feature) {{
  return {{
    fillColor  : getColor(feature.properties.crime_count),
    weight     : 1.5,
    color      : 'rgba(255,255,255,0.85)',
    fillOpacity: 0.82,
  }};
}}

let hovered = null;

function onEachFeature(feature, layer) {{
  layer.on({{
    mouseover(e) {{
      const l = e.target;
      l.setStyle({{ weight:2.5, color:'#333', fillOpacity:0.95 }});
      l.bringToFront();
      hovered = l;
      const p = feature.properties;
      const pct = ((p.crime_count/TOTAL)*100).toFixed(1);
      layer.bindTooltip(`
        <div class="tooltip-box">
          <div class="name">${{p[NAME_COL]}}</div>
          <div class="count">${{p.crime_count.toLocaleString('fr-FR')}}</div>
          <div class="unit">crimes signalés</div>
          <div class="pct">${{pct}}% du total</div>
        </div>`, {{sticky:true, className:'tooltip-box'}}).openTooltip(e.latlng);
    }},
    mouseout(e) {{
      geo.resetStyle(e.target);
      layer.closeTooltip();
    }},
  }});
}}

const geo = L.geoJSON(GEOJSON, {{ style, onEachFeature }}).addTo(map);
map.fitBounds(geo.getBounds(), {{padding:[16,16]}});

// Légende
const legend = L.control({{position:'bottomright'}});
legend.onAdd = function() {{
  const div = L.DomUtil.create('div','legend');
  div.innerHTML = '<h4>Nombre de crimes</h4>';
  const steps = 5;
  for (let i=steps; i>=0; i--) {{
    const v = Math.round(MIN_VAL+(MAX_VAL-MIN_VAL)*(i/steps));
    div.innerHTML += `<div class="legend-row">
      <span class="legend-swatch" style="background:${{getColor(v)}}"></span>
      <span>${{v.toLocaleString('fr-FR')}}</span>
    </div>`;
  }}
  div.innerHTML += `<div style="margin-top:10px;padding-top:8px;border-top:0.5px solid #e0ddd4;font-size:11px;color:#888;">
    Total : ${{TOTAL.toLocaleString('fr-FR')}} crimes<br>(quartier renseigné)</div>`;
  return div;
}};
legend.addTo(map);
</script>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"── Export ───────────────────────────────────────────────")
    print(f"  Carte exportée → {output_path}")
    print()


# ── Point d'entrée ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 57)
    print("CARTOGRAPHIE — CHOROPLÈTHE CRIMES PAR QUARTIER")
    print("=" * 57)
    print()

    crimes      = aggregate_crimes(DATA_PATH)
    geojson, nc = load_geojson(GEOJSON_URL)
    geojson     = join_data(geojson, nc, crimes)
    export_map(geojson, nc, OUTPUT_HTML)

    print("Terminé.")
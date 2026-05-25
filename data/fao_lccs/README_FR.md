**Langue / Language :** [Français](README_FR.md) · [English](README.md)

# Fraction urbaine FAO LCCS par zone de santé

Fraction de **couverture terrestre urbaine** par zone de santé en République démocratique du Congo (RDC), dérivée du produit Copernicus Climate Data Store (CDS) [**satellite-land-cover**](https://cds.climate.copernicus.eu/datasets/satellite-land-cover) (système de classification de la couverture terrestre de la FAO, LCCS). Les valeurs représentent la proportion de chaque zone classée comme **urbaine** (classe LCCS **190**).

Ces données soutiennent les analyses d’épidémie et de connectivité lorsque l’environnement bâti peut modifier les contacts, les recours aux soins ou l’interprétation des proxies de mobilité.

![Fraction urbaine par zone de santé](processed_plot.png)

*Proportion de chaque zone de santé classée comme urbaine (code LCCS 190). Gris = 0 % urbain ; échelle de couleurs log₁₀ pour les valeurs non nulles. Généré par `process.R`.*

------------------------------------------------------------------------

## Fichiers

| Fichier | Description |
|-----------------------|-------------------------------------------------|
| `processed/fao_lccs__urban_fraction__static.csv` | Tableau contractuel du dépôt : `nom`, `urban_fraction` (519 lignes) |
| `raw/COD-2022-satellite_land_cover_urban.zs.nc` | NetCDF intermédiaire : fraction urbaine par code de zone de santé (`ZSCode`), instantané 2022 |
| `processed_plot.png` | Carte de la fraction urbaine par zone de santé |
| `process.R` | Jointure NetCDF / shapefile, carte et export CSV |
| `query_cds_api.py` | Ébauche de téléchargement via l’API CDS (pas encore intégrée à l’arborescence `raw/` de ce dossier) |

**Couverture :** 519 zones de santé (échelle nationale), alignées sur `data/shapefiles/DRC_Health_zones.shp`.\
**Portée temporelle :** Extrait statique pour **2022** (`COD-2022-…`) ; le NetCDF ne contient qu’une seule couche temporelle.

------------------------------------------------------------------------

## Méthode

1.  **Couverture terrestre (amont)** — Cartes LCCS globales à 300 m depuis CDS `satellite-land-cover` (v2.1.1). Les zones urbaines utilisent la **classe 190**. Le traitement raster complet est prévu via le [pipeline DARTS](https://dart-pipeline.readthedocs.io/en/latest/) ; le NetCDF validé est un **agrégat 2022 par zone de santé** produit dans un projet antérieur et réutilisé ici pendant la migration de ce pipeline dans le dépôt.
2.  **Géométrie des zones** — `data/shapefiles/DRC_Health_zones.shp` ; clé de jointure `ZSCode` (p. ex. `CD8308ZS03`) correspond à `region` dans le NetCDF.
3.  **Export (`process.R`)** — Lecture de `lccs_class` (fraction urbaine, 0–1) depuis le NetCDF, `left_join` sur le shapefile, carte avec `ggplot2`/`sf`, enregistrement de `processed_plot.png`, puis CSV tabulaire avec `st_drop_geometry()` (colonnes `nom`, `urban_fraction` uniquement).

**Unités :** `urban_fraction` est une **proportion** dans $[0, 1]$ (0 = aucun pixel urbain dans l’agrégat de la zone ; 1 = entièrement urbain).

------------------------------------------------------------------------

## Contrat CSV

| Colonne           | Description                                             |
|----------------------------|--------------------------------------------|
| `nom`            | Nom de la zone de santé (`Nom` du shapefile)                 |
| `urban_fraction` | Fraction de la surface de zone classée urbaine (LCCS 190), 2022 |

**Exemple (R) :**

``` r
library(here)

urban <- read.csv(here("data/fao_lccs/processed/fao_lccs__urban_fraction__static.csv"))
urban[urban$urban_fraction > 0.1, ]
```

Pour les jointures spatiales ou les cartes, utiliser `data/shapefiles/DRC_Health_zones.shp` sur `nom` (ou `ZSCode` lorsque les noms sont dupliqués).

Jointure aux autres tableaux du dépôt sur `nom` (attention aux homonymes dans le shapefile : **Bili**, **Lubunga** — voir `data/shapefiles/README.md`).

------------------------------------------------------------------------

## Régénérer les sorties

Depuis la **racine du dépôt** :

``` bash
# Optionnel : récupérer les tuiles CDS brutes (nécessite ~/.cdsapirc ; chemins du script encore en cours d’alignement)
# python3 data/fao_lccs/query_cds_api.py download --start_year 2022 --end_year 2022
# Ne pas exécuter pour l’instant — en attente

# Reconstruire la carte et le CSV à partir du NetCDF validé
Rscript data/fao_lccs/process.R
```

**Paquets R :** `sf`, `dplyr`, `ncdf4`, `terra`, `here`, `ggplot2`.\
**Python (téléchargement uniquement) :** `cdsapi`, `fire` (voir `query_cds_api.py`).

------------------------------------------------------------------------

## Qualité des données et limites

| Problème | Détail |
|----------------------------------|--------------------------------------|
| **Année fixe** | Les valeurs reflètent uniquement la couche de couverture terrestre **2022** ; pas de série temporelle dans ce dossier. |
| **Raster → zone** | Les fractions sont agrégées aux polygones des zones de santé (les statistiques zonales exactes dépendent du workflow raster amont DARTS). |
| **Définition d’urbain** | Classe LCCS 190 uniquement ; les habitats informels ou la périphérie urbaine peuvent être mal classés au regard de la connaissance locale. |
| **Pipeline en évolution** | Le téléchargement CDS brut et le traitement DARTS ne sont pas encore entièrement reproductibles depuis ce dépôt ; `raw/COD-2022-satellite_land_cover_urban.zs.nc` est la source de vérité actuelle pour la régénération. |

------------------------------------------------------------------------

## Provenance

-   **Jeu de données :** Copernicus CDS `satellite-land-cover` (FAO LCCS, 300 m, annuel).
-   **Géométrie :** `data/shapefiles/DRC_Health_zones.shp`.
-   **Métadonnées :** `metadata.yaml`.

Pour les conventions générales du projet, voir `data/README.md`.

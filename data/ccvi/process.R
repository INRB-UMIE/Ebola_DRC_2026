rm(list = ls())

# -------------- 1. Check Necessary packages are Installed ---------------------
# R
if(!require("sf")) install.packages("sf")
if(!require("dplyr")) install.packages("dplyr")
if(!require("ncdf4")) install.packages("ncdf4")
if(!require("terra")) install.packages("terra")
if(!require("here")) install.packages("here") 
if(!require("ggplot2")) install.packages("ggplot2") 

library(sf)
library(dplyr)
library(ncdf4)
library(terra)
library(here)
library(ggplot2)

wd <- here()
setwd(wd)

# Python
# Commenting this out for now will eventually add the darts pipeline processing here
#python = Sys.which("python3.10")
#python <- python[1L]
#system2(python, c("-m", "pip install -r requirements.txt"))



# ----------- 2. Call Python script to download raw from CDS API ---------------

# ccvi call (script to be added)
# Commented out for now, we don't currently need it

# ----------- 3. To be added: processing with darts pipeline -------------------
# Rasters are processed using the darts pipeline: https://dart-pipeline.readthedocs.io/en/latest/
# This was previously done for
# another project, so we are migrating over the code. For now, we are taking the
# outputs from the processing from another project, making some minor adjustments, 
# and uploading the data

# -------------------- 4. Read in Current NCDF Files  --------------------------
# When we have the darts pipeline code up and running we will likely remove ncdf
# files from repo and just have geoJSON. For now, we read in our current ncdf files
# from another project, subset to our interested timepoint (most recent) and convert
# to geoJSON

# Read ncdf
ncdf_raw <- nc_open("data/ccvi/raw/COD-2022-2024-ccvi.zs.nc")
names(ncdf_raw$var)
names(ncdf_raw$dim)

# Read healthzone shapefile
healthzone_shapefile <- st_read("data/shapefiles/DRC_Health_zones.shp")

# Disambiguate Nom for zones whose name appears in more than one province
# (currently Bili and Lubunga), mirroring the Python schema contract.
nom_counts <- healthzone_shapefile |>
  dplyr::count(Nom) |>
  dplyr::filter(n > 1) |>
  dplyr::pull(Nom)
healthzone_shapefile <- healthzone_shapefile |>
  dplyr::mutate(Nom = dplyr::if_else(
    Nom %in% nom_counts,
    paste0(Nom, " (", PROVINCE, ")"),
    Nom
  ))

# Socioeconomic Inequality
vals <- ncdf4::ncvar_get(
  ncdf_raw,
  "VUL_socioeconomic_inequality",
  start = c(1, 11),
  count = c(-1, 1)
)
regions <- ncdf_raw$dim$region$vals

socioeconomic_inequality_table <- data.frame(ZSCode = regions,
                                          socioeconomic_inequality = vals)

joined_shapefile_socioeconomic_inequality <- healthzone_shapefile |>
  dplyr::left_join(socioeconomic_inequality_table)

p <- ggplot(joined_shapefile_socioeconomic_inequality) +
  geom_sf(aes(fill = socioeconomic_inequality), col = NA) +
   scale_fill_viridis_c(
    name = "Socioeconomic Inequality",   # legend title
     option = "D"
  ) +
  theme_classic() +
  theme(axis.line = element_blank(),
        axis.ticks = element_blank(),
        axis.text = element_blank(),
        legend.position = "inside",
        legend.position.inside = c(0.25,0.15),
        legend.direction = "horizontal",
        legend.title.position = "top",
        legend.background = element_blank()) +
  ggtitle("Socioeconomic Inequality from the Climate Conflict Vulnerability Index")

ggsave("data/ccvi/socioeconomic_inequality_processed_plot.png", p, height = 6, width = 6, units = "in")

final_export_socioeconomic_inequality <- joined_shapefile_socioeconomic_inequality |>
  dplyr::select(Nom, socioeconomic_inequality) |>
  dplyr::rename(nom = Nom) |>
  st_drop_geometry()

write.csv(final_export_socioeconomic_inequality, "data/ccvi/processed/ccvi__socioeconomic_inequality__static.csv")

# Socioeconomic Deprivation
vals <- ncdf4::ncvar_get(
  ncdf_raw,
  "VUL_socioeconomic_deprivation",
  start = c(1, 11),
  count = c(-1, 1)
)
regions <- ncdf_raw$dim$region$vals

socioeconomic_deprivation_table <- data.frame(ZSCode = regions,
                                             socioeconomic_deprivation = vals)

joined_shapefile_socioeconomic_deprivation <- healthzone_shapefile |>
  dplyr::left_join(socioeconomic_deprivation_table)

p <- ggplot(joined_shapefile_socioeconomic_deprivation) +
  geom_sf(aes(fill = socioeconomic_deprivation), col = NA) +
  scale_fill_viridis_c(
    name = "Socioeconomic deprivation",   # legend title
    option = "D"
  ) +
  theme_classic() +
  theme(axis.line = element_blank(),
        axis.ticks = element_blank(),
        axis.text = element_blank(),
        legend.position = "inside",
        legend.position.inside = c(0.25,0.15),
        legend.direction = "horizontal",
        legend.title.position = "top",
        legend.background = element_blank()) +
  ggtitle("Socioeconomic Deprivation from the Climate Conflict Vulnerability Index")

ggsave("data/ccvi/socioeconomic_deprivation_processed_plot.png", p, height = 6, width = 6, units = "in")

final_export_socioeconomic_deprivation <- joined_shapefile_socioeconomic_deprivation |>
  dplyr::select(Nom, socioeconomic_deprivation) |>
  dplyr::rename(nom = Nom) |>
  st_drop_geometry()

write.csv(final_export_socioeconomic_deprivation, "data/ccvi/processed/ccvi__socioeconomic_deprivation__static.csv")

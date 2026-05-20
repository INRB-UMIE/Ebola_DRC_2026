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

#system2(python, c("data/fao_lccs/query_cds_api.py"), stdout = TRUE)
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
ncdf_raw <- nc_open("data/worldpop/processed/COD-2025-population.zs.nc")
names(ncdf_raw$var)
names(ncdf_raw$dim)

# Read healthzone shapefile
healthzone_shapefile <- st_read("data/shapefiles/DRC_Health_zones.shp")

# Population Count
vals <- ncvar_get(ncdf_raw, "pop_count")
regions <- ncvar_get(ncdf_raw, "region")

popcount_table <- data.frame(ZSCode = regions,
                                 pop_count = vals)

joined_shapefile_popcount <- healthzone_shapefile |>
  dplyr::left_join(popcount_table)

p <- ggplot(joined_shapefile_popcount) +
  geom_sf(aes(fill = log(pop_count)), col = NA) +
   scale_fill_viridis_c(
     name = "Population Count",   # legend title
     option = "C",
     breaks = log(c(2000, 20000, 1800000)),
     labels = c(2000, 20000, 1800000),
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
  ggtitle("Population Count per Healthzone from Worldpop")

ggsave("data/worldpop/popcount_processed_plot.png", p, height = 6, width = 6, units = "in")

final_export_popcount <- joined_shapefile_popcount |>
  dplyr::select(Nom, pop_count) |>
  dplyr::rename(nom = Nom) |>
  st_drop_geometry()

write.csv(final_export_popcount, "data/worldpop/processed/worldpop__pop_count__static.csv")

# Population Density
vals <- ncvar_get(ncdf_raw, "pop_density")
regions <- ncvar_get(ncdf_raw, "region")

popdensity_table <- data.frame(ZSCode = regions,
                             pop_density = vals)

joined_shapefile_popdensity <- healthzone_shapefile |>
  dplyr::left_join(popdensity_table)

p <- ggplot(joined_shapefile_popdensity) +
  geom_sf(aes(fill = log(pop_density)), col = NA) +
  scale_fill_viridis_c(
    name = "Population Density",   # legend title
    option = "C",
    breaks = log(c(3, 300, 30000)),
    labels = c(3, 300, 30000)
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
  ggtitle("Population Density by Healthzone from Worldpop (People per sq km)")

ggsave("data/worldpop/popdensity_processed_plot.png", p, height = 6, width = 6, units = "in")

final_export_popdensity <- joined_shapefile_popdensity |>
  dplyr::select(Nom, pop_density) |>
  dplyr::rename(nom = Nom) |>
  st_drop_geometry()

write.csv(final_export_popdensity, "data/worldpop/processed/worldpop__pop_density__static.csv")

rm(list = ls())

# -------------------- 1. Install and Load Packages ----------------------------
if(!require("sf")) install.packages("sf")
if(!require("dplyr")) install.packages("dplyr")
if(!require("osrm")) install.packages("osrm")
if(!require("tictoc")) install.packages("tictoc") # Optional: to time the process
if(!require("here")) install.packages("here") # Optional: to time the process

library(sf)
library(dplyr)
library(osrm)
library(tictoc)
library(here)

wd <- here()
setwd(wd)


# ---------------------------- 2. Load Data ------------------------------------
shapefile_name <- "data/shapefiles/DRC_Health_zones.shp" 

tryCatch({
  zones_sf <- st_read(shapefile_name, quiet = TRUE)|>
    st_make_valid()
  # Disambiguate Nom for zones whose name appears in more than one province
  # (currently Bili and Lubunga), mirroring the Python schema contract.
  nom_counts <- zones_sf |>
    dplyr::count(Nom) |>
    dplyr::filter(n > 1) |>
    dplyr::pull(Nom)
  zones_sf <- zones_sf |>
    dplyr::mutate(Nom = dplyr::if_else(
      Nom %in% nom_counts,
      paste0(Nom, " (", PROVINCE, ")"),
      Nom
    )) 
  
}, error = function(e) {
  stop("Error reading file. Please ensure the shapefile exists and is named correctly.")
})


# ------------------------- 3. Prepare Centroids -------------------------------
# The API requires coordinates in degrees, not meters.
zones_sf_4326 <- st_transform(zones_sf, crs = 4326)

# Use point_on_surface to ensure the point is actually inside the polygon
# (st_centroid can sometimes fall outside for boomerang-shaped zones)
centroids_sf <- st_point_on_surface(zones_sf_4326)

# Create ID list
centroids_sf$ID_Code <- if("Nom" %in% colnames(centroids_sf)) {
  centroids_sf$Nom 
} else {
  paste0("Zone_", 1:nrow(centroids_sf)) 
}

# --------------------------- 4. Setup Batches ---------------------------------
# We must split the request. A chunk size of 20 means we send 20x20 = 400 pairs 
# per request (or rather, 40 coordinates in the URL). This is safe for the public server.
CHUNK_SIZE <- 20 
total_zones <- nrow(centroids_sf)

# Initialize empty matrices to store results
full_dur_matrix <- matrix(NA, nrow = total_zones, ncol = total_zones)
full_dist_matrix <- matrix(NA, nrow = total_zones, ncol = total_zones)

# Set row/col names
rownames(full_dur_matrix) <- centroids_sf$ID_Code
colnames(full_dur_matrix) <- centroids_sf$ID_Code
rownames(full_dist_matrix) <- centroids_sf$ID_Code
colnames(full_dist_matrix) <- centroids_sf$ID_Code

# Define the start indices for our chunks
indices <- seq(1, total_zones, by = CHUNK_SIZE)

message(paste("Starting processing for", total_zones, "zones."))
message(paste("Total batches to process:", length(indices) * length(indices)))

# ------------------------- 5. Loop over batches -------------------------------
tic("Total processing time") # Start timer

for (i in indices) {
  # Define the Source Batch
  i_end <- min(i + CHUNK_SIZE - 1, total_zones)
  src_idx <- i:i_end
  src_batch <- centroids_sf[src_idx, ]
  
  for (j in indices) {
    # Define the Destination Batch
    j_end <- min(j + CHUNK_SIZE - 1, total_zones)
    dst_idx <- j:j_end
    dst_batch <- centroids_sf[dst_idx, ]
    
    # Progress message
    cat(sprintf("Processing batch: Rows %d-%d vs Cols %d-%d\n", i, i_end, j, j_end))
    
    # --- CALL OSRM API ---
    # We wrap this in tryCatch so one failure doesn't kill the whole script
    tryCatch({
      res <- osrmTable(
        src = src_batch,
        dst = dst_batch,
        measure = c("duration", "distance"),
        osrm.profile = "car"
      )
      
      # Fill the main matrices with the sub-matrix results
      full_dur_matrix[src_idx, dst_idx] <- res$durations
      full_dist_matrix[src_idx, dst_idx] <- res$distances
      
    }, error = function(e) {
      message(paste("Error in this batch:", e$message))
      # Note: The matrix positions for this batch will remain NA
    })
    
    # Essential for public API to avoid '429 Too Many Requests'
    Sys.sleep(1) 
  }
}

toc() # End timer

# ---------------------------- 6. Export CSVs ---------------------------------

# Convert meters to kilometers for distance
full_dist_matrix_km <- full_dist_matrix / 1000

message("Processing Complete. Preview of Duration Matrix:")
print(full_dur_matrix[1:5, 1:5])

# Save results

write.csv(full_dur_matrix, "data/osrm/processed/osrm__travel_time__static.matrix.csv", row.names = T)
write.csv(full_dist_matrix_km, "data/osrm/processed/osrm__road_distance__static.matrix.csv", row.names = T)

full_dur_matrix_2 <- read.csv("data/osrm/processed/osrm__travel_time__static.matrix.csv") 
colnames(full_dur_matrix_2) <- c("nom", full_dur_matrix_2$X)

full_dist_matrix_km_2 <- read.csv("data/osrm/processed/osrm__road_distance__static.matrix.csv") 
colnames(full_dist_matrix_km_2) <- c("nom", full_dist_matrix_km_2$X)

write.csv(full_dur_matrix_2, "data/osrm/processed/osrm__travel_time__static.matrix.csv", row.names = F)
write.csv(full_dist_matrix_km_2, "data/osrm/processed/osrm__road_distance__static.matrix.csv", row.names = F)

message("Files saved to working directory.")


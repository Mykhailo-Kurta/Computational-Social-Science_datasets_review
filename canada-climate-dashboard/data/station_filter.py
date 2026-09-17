import os
from difflib import SequenceMatcher

import pandas as pd
import geopandas as gpd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = r"D:\Desktop\Computational Social Science\Hometask1"

CLIMATE_FILE = rf"{BASE_DIR}\aafc_aac_climat_2025.csv"
GEOJSON_FILE = rf"{BASE_DIR}\geoBoundaries-CAN-ADM1.geojson"
NORMALS_FILE = rf"{BASE_DIR}\1991-2020_Canadian_Climate_Normals_CANADA_Data.csv"
CITIES_FILE = rf"{BASE_DIR}\Biggest cities.xlsx"

SELECTED_FILE = rf"{BASE_DIR}\selected_stations.csv"
VALIDATION_FILE = rf"{BASE_DIR}\station_validation.csv"


# ============================================================
# SETTINGS
# ============================================================

# Мінімальна допустима заповненість температурних даних
MIN_COMPLETENESS = 90

# Мінімальна схожість назви станції з Climate Normals
MIN_NORMALS_SIMILARITY = 80


# ============================================================
# FUNCTIONS
# ============================================================

def normalize_station_name(name):
    """
    Нормалізує назву станції перед порівнянням.

    Не видаляємо A, AUT, CS тощо,
    оскільки це потенційно важлива інформація.
    """

    if pd.isna(name):
        return ""

    name = str(name).upper().strip()

    # Уніфікуємо розділові знаки
    for char in ["/", "-", "(", ")", ",", "."]:
        name = name.replace(char, " ")

    # Прибираємо зайві пробіли
    name = " ".join(name.split())

    return name


def similarity_score(name1, name2):
    """
    Повертає схожість двох назв у відсотках.
    """

    name1 = normalize_station_name(name1)
    name2 = normalize_station_name(name2)

    if not name1 or not name2:
        return 0.0

    return SequenceMatcher(
        None,
        name1,
        name2
    ).ratio() * 100


def find_normals_match(
    station_name,
    province,
    normals_locations
):
    """
    Шукає відповідну станцію у Climate Normals
    серед станцій тієї самої провінції.

    Повертає:
        matched_name
        similarity
        status
        valid
    """

    # --------------------------------------------------------
    # Залишаємо тільки станції тієї ж провінції
    # --------------------------------------------------------

    candidates = normals_locations[
        normals_locations["PROVINCE_OR_TERRITORY"] == province
    ].copy()

    if candidates.empty:
        return None, 0.0, "NO_MATCH", False

    # --------------------------------------------------------
    # Нормалізована назва
    # --------------------------------------------------------

    normalized_name = normalize_station_name(
        station_name
    )

    candidates["normalized_name"] = (
        candidates["LOCATION_NAME"]
        .apply(normalize_station_name)
    )

    # --------------------------------------------------------
    # EXACT MATCH
    # --------------------------------------------------------

    exact = candidates[
        candidates["normalized_name"] == normalized_name
    ]

    if not exact.empty:

        return (
            exact.iloc[0]["LOCATION_NAME"],
            100.0,
            "EXACT",
            True
        )

    # --------------------------------------------------------
    # FUZZY MATCH
    # --------------------------------------------------------

    best_name = None
    best_score = 0.0

    for _, candidate in candidates.iterrows():

        score = similarity_score(
            station_name,
            candidate["LOCATION_NAME"]
        )

        if score > best_score:

            best_score = score
            best_name = candidate["LOCATION_NAME"]

    # --------------------------------------------------------
    # Перевіряємо threshold
    # --------------------------------------------------------

    if best_score >= 90:

        status = "FUZZY_HIGH"
        valid = True

    elif best_score >= MIN_NORMALS_SIMILARITY:

        status = "FUZZY_REVIEW"
        valid = True

    else:

        status = "NO_MATCH"
        valid = False
        best_name = None

    return (
        best_name,
        best_score,
        status,
        valid
    )


def haversine_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Відстань між двома точками на поверхні Землі
    у кілометрах.
    """

    from math import radians, sin, cos, sqrt, atan2

    R = 6371.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        +
        cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("CANADIAN WEATHER STATION SELECTION")
    print("=" * 70)


    # ========================================================
    # 1. READ 2025 CLIMATE DATA
    # ========================================================

    print("\nReading 2025 climate data...")

    climate = pd.read_csv(
        CLIMATE_FILE,
        usecols=[
            "STATION_AES",
            "STATION_NAME",
            "STATION_DATE",
            "LATITUDE",
            "LONGITUDE",
            "MAX_TEMP",
            "MIN_TEMP"
        ]
    )

    print(
        f"Rows in climate data: "
        f"{len(climate):,}"
    )


    # ========================================================
    # 2. CONVERT TEMPERATURE COLUMNS
    # ========================================================

    climate["MAX_TEMP"] = pd.to_numeric(
        climate["MAX_TEMP"],
        errors="coerce"
    )

    climate["MIN_TEMP"] = pd.to_numeric(
        climate["MIN_TEMP"],
        errors="coerce"
    )


    # ========================================================
    # 3. GET UNIQUE STATIONS
    # ========================================================

    print("\nGetting unique stations...")

    stations = (
        climate[
            [
                "STATION_AES",
                "STATION_NAME",
                "LATITUDE",
                "LONGITUDE"
            ]
        ]
        .drop_duplicates(subset=["STATION_AES"])
        .copy()
    )

    print(
        f"Unique stations: "
        f"{len(stations):,}"
    )


    # ========================================================
    # 4. READ PROVINCE REFERENCE CITIES
    # ========================================================

    print("\nReading reference cities...")

    cities = pd.read_excel(
        CITIES_FILE
    )

    print(
        f"Reference cities: "
        f"{len(cities)}"
    )


    # ========================================================
    # 5. CREATE GEODATAFRAME FOR STATIONS
    # ========================================================

    print("\nCreating station GeoDataFrame...")

    station_points = gpd.GeoDataFrame(
        stations.copy(),
        geometry=gpd.points_from_xy(
            stations["LONGITUDE"],
            stations["LATITUDE"]
        ),
        crs="EPSG:4326"
    )


    # ========================================================
    # 6. READ CANADA PROVINCES GEOJSON
    # ========================================================

    print("\nReading provinces GeoJSON...")

    # GeoJSON is very large, so allow large objects
    os.environ["OGR_GEOJSON_MAX_OBJ_SIZE"] = "0"

    provinces = gpd.read_file(
        GEOJSON_FILE
    )

    print(
        f"Provinces / territories: "
        f"{len(provinces)}"
    )


    # ========================================================
    # 7. SPATIAL JOIN: STATION -> PROVINCE
    # ========================================================

    print("\nAssigning stations to provinces...")

    station_points = gpd.sjoin(
        station_points,
        provinces[
            [
                "shapeName",
                "shapeISO",
                "geometry"
            ]
        ],
        how="left",
        predicate="within"
    )

    # Rename province column
    station_points = station_points.rename(
        columns={
            "shapeName": "province_name",
            "shapeISO": "province_iso"
        }
    )

    # Extract short province code, e.g. CA-BC -> BC
    station_points["short_name"] = (
        station_points["province_iso"]
        .str.replace("CA-", "", regex=False)
    )

    # Remove spatial join helper column
    if "index_right" in station_points.columns:
        station_points = station_points.drop(
            columns=["index_right"]
        )

    print("\nStations by province:")

    print(
        station_points["short_name"]
        .value_counts(dropna=False)
        .to_string()
    )


    # ========================================================
    # 8. TEMPERATURE DATA VALIDATION
    # ========================================================

    print("\nValidating temperature data...")

    temperature_stats = (
        climate
        .groupby("STATION_AES")
        .agg(
            total_days=(
                "STATION_DATE",
                "count"
            ),
            max_temp_days=(
                "MAX_TEMP",
                "count"
            ),
            min_temp_days=(
                "MIN_TEMP",
                "count"
            )
        )
        .reset_index()
    )

    temperature_stats["max_temp_completeness"] = (
        temperature_stats["max_temp_days"]
        /
        temperature_stats["total_days"]
        * 100
    )

    temperature_stats["min_temp_completeness"] = (
        temperature_stats["min_temp_days"]
        /
        temperature_stats["total_days"]
        * 100
    )

    temperature_stats["temperature_valid"] = (
        (
            temperature_stats["max_temp_completeness"]
            >= MIN_COMPLETENESS
        )
        &
        (
            temperature_stats["min_temp_completeness"]
            >= MIN_COMPLETENESS
        )
    )


    # ========================================================
    # 9. MERGE TEMPERATURE VALIDATION WITH STATIONS
    # ========================================================

    stations = stations.merge(
        temperature_stats,
        on="STATION_AES",
        how="left"
    )

    # Add province information from spatial join
    province_info = station_points[
        [
            "STATION_AES",
            "province_name",
            "province_iso",
            "short_name"
        ]
    ].copy()

    stations = stations.merge(
        province_info,
        on="STATION_AES",
        how="left"
    )


    print(
        "\nTemperature-valid stations:",
        stations["temperature_valid"].sum()
    )


    # ========================================================
    # 10. READ CLIMATE NORMALS
    # ========================================================

    print("\nReading climate normals...")

    normals = pd.read_csv(
        NORMALS_FILE,
        usecols=[
            "LOCATION_NAME",
            "PROVINCE_OR_TERRITORY"
        ]
    )

    # Only unique station names are needed
    normals_locations = (
        normals[
            [
                "LOCATION_NAME",
                "PROVINCE_OR_TERRITORY"
            ]
        ]
        .dropna()
        .drop_duplicates()
        .reset_index(drop=True)
    )

    print(
        f"Unique stations in climate normals: "
        f"{len(normals_locations):,}"
    )


    # ========================================================
    # 11. MATCH STATIONS WITH CLIMATE NORMALS
    # ========================================================

    print("\nMatching stations with climate normals...")

    matching_results = []

    for _, station in stations.iterrows():

        station_name = station["STATION_NAME"]
        province = station["short_name"]

        (
            matched_name,
            similarity,
            status,
            valid
        ) = find_normals_match(
            station_name,
            province,
            normals_locations
        )

        matching_results.append(
            {
                "normals_station": matched_name,
                "normals_similarity": round(
                    similarity,
                    2
                ),
                "normals_match_status": status,
                "normals_valid": valid
            }
        )

    normals_matches = pd.DataFrame(
        matching_results,
        index=stations.index
    )

    stations = pd.concat(
        [
            stations,
            normals_matches
        ],
        axis=1
    )


    # ========================================================
    # 12. FINAL VALIDATION
    # ========================================================

    stations["station_valid"] = (
        stations["temperature_valid"]
        &
        stations["normals_valid"]
    )

    valid_stations = stations[
        stations["station_valid"]
    ].copy()


    # ========================================================
    # 13. VALIDATION SUMMARY
    # ========================================================

    print("\n")
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(
        f"Total stations: "
        f"{len(stations):,}"
    )

    print(
        f"Temperature valid: "
        f"{stations['temperature_valid'].sum():,}"
    )

    print(
        f"Normals valid: "
        f"{stations['normals_valid'].sum():,}"
    )

    print(
        f"Both conditions valid: "
        f"{stations['station_valid'].sum():,}"
    )

    print("\nNormals matching status:")

    print(
        stations["normals_match_status"]
        .value_counts()
        .to_string()
    )


    # ========================================================
    # 14. SAVE VALIDATION REPORT
    # ========================================================

    stations[
        [
            "STATION_AES",
            "STATION_NAME",
            "short_name",
            "province_name",
            "LATITUDE",
            "LONGITUDE",

            "total_days",
            "max_temp_days",
            "min_temp_days",

            "max_temp_completeness",
            "min_temp_completeness",
            "temperature_valid",

            "normals_station",
            "normals_similarity",
            "normals_match_status",
            "normals_valid",

            "station_valid"
        ]
    ].to_csv(
        VALIDATION_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"\nValidation report saved to:\n"
        f"{VALIDATION_FILE}"
    )


    # ========================================================
    # 15. CALCULATE DISTANCE TO REFERENCE CITIES
    # ========================================================

    print("\nCalculating distances to reference cities...")

    distance_results = []

    for _, city in cities.iterrows():

        province = city["short_name"]

        province_stations = valid_stations[
            valid_stations["short_name"] == province
        ].copy()

        if province_stations.empty:
            print(
                f"\nWARNING: No valid stations for {province}"
            )
            continue

        reference_lat = city["lat"]
        reference_lon = city["lon"]

        province_stations["distance_km"] = (
            province_stations.apply(
                lambda row: haversine_distance(
                    row["LATITUDE"],
                    row["LONGITUDE"],
                    reference_lat,
                    reference_lon
                ),
                axis=1
            )
        )


        # ----------------------------------------------------
        # Nearest
        # ----------------------------------------------------

        nearest = province_stations.loc[
            province_stations["distance_km"].idxmin()
        ].copy()

        nearest["province"] = city["province"]
        nearest["reference_city"] = city["reference_city"]
        nearest["selection"] = "nearest"

        distance_results.append(
            nearest
        )


        # ----------------------------------------------------
        # Farthest
        # ----------------------------------------------------

        farthest = province_stations.loc[
            province_stations["distance_km"].idxmax()
        ].copy()

        farthest["province"] = city["province"]
        farthest["reference_city"] = city["reference_city"]
        farthest["selection"] = "farthest"

        distance_results.append(
            farthest
        )


    # ========================================================
    # 16. CREATE FINAL SELECTED STATIONS
    # ========================================================

    selected_stations = pd.DataFrame(
        distance_results
    )

    # Select useful columns
    selected_stations = selected_stations[
        [
            "province",
            "short_name",
            "reference_city",
            "selection",

            "STATION_AES",
            "STATION_NAME",

            "LATITUDE",
            "LONGITUDE",
            "distance_km",

            "total_days",
            "max_temp_days",
            "min_temp_days",

            "max_temp_completeness",
            "min_temp_completeness",

            "normals_station",
            "normals_similarity",
            "normals_match_status",

            "temperature_valid",
            "normals_valid",
            "station_valid"
        ]
    ].copy()


    # ========================================================
    # 17. SAVE FINAL STATIONS
    # ========================================================

    selected_stations.to_csv(
        SELECTED_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"\nSelected stations saved to:\n"
        f"{SELECTED_FILE}"
    )


    # ========================================================
    # 18. PRINT FINAL RESULTS
    # ========================================================

    print("\n")
    print("=" * 70)
    print("FINAL SELECTED STATIONS")
    print("=" * 70)

    print(
        selected_stations[
            [
                "province",
                "selection",
                "STATION_NAME",
                "normals_station",
                "normals_similarity",
                "distance_km"
            ]
        ].to_string(index=False)
    )

    print("\n")
    print(
        f"Total selected stations: "
        f"{len(selected_stations)}"
    )

    print("\nDone!")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
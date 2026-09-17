import json
from pathlib import Path

import pandas as pd

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SITE_DIR = BASE_DIR / "site"

CLIMATE_FILE = DATA_DIR / "aafc_aac_climat_2025.csv"
NORMALS_FILE = DATA_DIR / "1991-2020_Canadian_Climate_Normals_CANADA_Data.csv"
CITIES_FILE = DATA_DIR / "Biggest cities.xlsx"
GEOJSON_FILE = DATA_DIR / "geoBoundaries-CAN-ADM1.geojson"
SELECTED_FILE = DATA_DIR / "selected_stations.csv"
VALIDATION_FILE = DATA_DIR / "station_validation.csv"

OUTPUT_FILE = SITE_DIR / "data.json"



MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

# Average number of days in each month over 1991-2020.
# Used to calculate an annual temperature normal from monthly normals.
MONTH_DAYS_1991_2020 = [
    31.0, 28.25, 31.0, 30.0, 31.0, 30.0,
    31.0, 31.0, 30.0, 31.0, 30.0, 31.0
]


# ============================================================
# HELPERS
# ============================================================

def clean_number(value, digits=2):
    if pd.isna(value):
        return None
    return round(float(value), digits)


def find_normal_element(normals, province, station_name, element_type):
    """Find a 1991-2020 normal row by province and validated station name."""
    candidates = normals[
        (normals["PROVINCE_OR_TERRITORY"] == province)
        & (normals["LOCATION_NAME"] == station_name)
    ]

    if candidates.empty:
        return None

    if element_type == "temperature":
        rows = candidates[
            candidates["NORMALS_ELEMENT"].str.contains(
                "Daily Average", case=False, na=False
            )
        ]
    elif element_type == "precipitation":
        rows = candidates[
            candidates["NORMALS_ELEMENT"].str.contains(
                r"^Precipitation \(mm\)", case=False, na=False, regex=True
            )
        ]
    else:
        rows = pd.DataFrame()

    if rows.empty:
        return None

    return rows.iloc[0]



# ============================================================
# MAIN
# ============================================================

def main():
    print("Reading selected stations...")
    selected = pd.read_csv(SELECTED_FILE)
    print(f"Selected stations: {len(selected)}")

    # Every visualization uses exactly the selected/validated stations.
    map_stations = selected.dropna(
        subset=["short_name", "LATITUDE", "LONGITUDE"]
    ).copy()
    map_stations = map_stations.drop_duplicates("STATION_AES")
    print(f"Stations on map: {len(map_stations)}")

    # --------------------------------------------------------
    # Read only required columns from the large 2025 file.
    # --------------------------------------------------------
    print("Reading 2025 climate observations...")

    climate = pd.read_csv(
        CLIMATE_FILE,
        usecols=[
            "STATION_AES",
            "STATION_NAME",
            "STATION_DATE",
            "MAX_TEMP",
            "MIN_TEMP",
            "DAILY_PRECIP",
        ],
    )

    climate["STATION_DATE"] = pd.to_datetime(
        climate["STATION_DATE"], errors="coerce"
    )
    climate["MAX_TEMP"] = pd.to_numeric(
        climate["MAX_TEMP"], errors="coerce"
    )
    climate["MIN_TEMP"] = pd.to_numeric(
        climate["MIN_TEMP"], errors="coerce"
    )
    climate["DAILY_PRECIP"] = pd.to_numeric(
        climate["DAILY_PRECIP"], errors="coerce"
    )

    climate["MONTH"] = climate["STATION_DATE"].dt.month
    climate["DAILY_AVG_TEMP"] = (
        climate["MAX_TEMP"] + climate["MIN_TEMP"]
    ) / 2

    selected_ids = set(selected["STATION_AES"])
    selected_climate = climate[
        climate["STATION_AES"].isin(selected_ids)
    ].copy()

    # --------------------------------------------------------
    # Monthly statistics for selected stations.
    # --------------------------------------------------------
    monthly_station = (
        selected_climate
        .groupby(["STATION_AES", "MONTH"], as_index=False)
        .agg(
            avg_temp=("DAILY_AVG_TEMP", "mean"),
            precipitation=("DAILY_PRECIP", "sum"),
        )
    )

    # --------------------------------------------------------
    # Annual 2025 station statistics.
    # --------------------------------------------------------
    annual_station = (
        selected_climate
        .groupby("STATION_AES", as_index=False)
        .agg(
            annual_temp=("DAILY_AVG_TEMP", "mean"),
            annual_precip=("DAILY_PRECIP", "sum"),
        )
    )

    station_info = selected[
        [
            "STATION_AES",
            "STATION_NAME",
            "short_name",
            "province",
            "reference_city",
            "LATITUDE",
            "LONGITUDE",
            "distance_km",
            "normals_station",
        ]
    ].drop_duplicates("STATION_AES")

    annual_station = annual_station.merge(
        station_info,
        on="STATION_AES",
        how="left",
    )

    # --------------------------------------------------------
    # 01. Monthly temperature overview.
    # --------------------------------------------------------
    temperature_overview = []

    for month_num, month_name in enumerate(MONTHS, start=1):
        values = monthly_station.loc[
            monthly_station["MONTH"] == month_num,
            ["STATION_AES", "avg_temp"],
        ]

        values = values.merge(
            station_info[["STATION_AES", "STATION_NAME"]],
            on="STATION_AES",
            how="left",
        )

        if values.empty:
            temperature_overview.append({
                "month": month_name,
                "average": None,
                "warmest": None,
                "coldest": None,
            })
            continue

        warmest = values.loc[values["avg_temp"].idxmax()]
        coldest = values.loc[values["avg_temp"].idxmin()]
        average = values["avg_temp"].mean()

        temperature_overview.append({
            "month": month_name,
            "average": clean_number(average),
            "warmest": {
                "station": warmest["STATION_NAME"],
                "value": clean_number(warmest["avg_temp"]),
            },
            "coldest": {
                "station": coldest["STATION_NAME"],
                "value": clean_number(coldest["avg_temp"]),
            },
        })

    # --------------------------------------------------------
    # Read 1991-2020 climate normals.
    # --------------------------------------------------------
    print("Reading climate normals...")

    normals = pd.read_csv(
        NORMALS_FILE,
        usecols=[
            "LOCATION_NAME",
            "PROVINCE_OR_TERRITORY",
            "NORMALS_ELEMENT",
            *MONTHS,
        ],
    )

    # --------------------------------------------------------
    # Build station-level comparison with climate normals.
    # --------------------------------------------------------
    station_comparison = []
    missing_normals = []

    for _, station in station_info.iterrows():
        province_code = station["short_name"]
        normals_name = station["normals_station"]
        station_id = station["STATION_AES"]

        temp_normal = find_normal_element(
            normals, province_code, normals_name, "temperature"
        )
        precip_normal = find_normal_element(
            normals, province_code, normals_name, "precipitation"
        )

        if temp_normal is None or precip_normal is None:
            missing_normals.append({
                "station": station["STATION_NAME"],
                "normals_station": normals_name,
                "province": province_code,
                "temperature_normal_found": temp_normal is not None,
                "precipitation_normal_found": precip_normal is not None,
            })
            continue

        normal_temp_values = [
            pd.to_numeric(temp_normal[m], errors="coerce") for m in MONTHS
        ]
        normal_precip_values = [
            pd.to_numeric(precip_normal[m], errors="coerce") for m in MONTHS
        ]

        temp_pairs = [
            (value, weight)
            for value, weight in zip(
                normal_temp_values, MONTH_DAYS_1991_2020
            )
            if pd.notna(value)
        ]

        if temp_pairs:
            normal_temp_annual = sum(
                value * weight for value, weight in temp_pairs
            ) / sum(weight for _, weight in temp_pairs)
        else:
            normal_temp_annual = None

        normal_precip_annual = sum(
            value for value in normal_precip_values if pd.notna(value)
        )

        annual_actual = annual_station[
            annual_station["STATION_AES"] == station_id
        ]

        if annual_actual.empty:
            actual_temp_annual = None
            actual_precip_annual = None
        else:
            actual_temp_annual = annual_actual.iloc[0]["annual_temp"]
            actual_precip_annual = annual_actual.iloc[0]["annual_precip"]

        station_comparison.append({
            "STATION_AES": station_id,
            "station": station["STATION_NAME"],
            "province": station["province"],
            "short_name": province_code,
            "normals_station": normals_name,
            "actual_temp": clean_number(actual_temp_annual),
            "normal_temp": clean_number(normal_temp_annual),
            "actual_precip": clean_number(actual_precip_annual),
            "normal_precip": clean_number(normal_precip_annual),
        })

    station_comparison_df = pd.DataFrame(station_comparison)

    # --------------------------------------------------------
    # 03 & 04. Province/territory annual comparison.
    # One value per region = simple average of represented stations.
    # --------------------------------------------------------
    province_comparison = []

    if not station_comparison_df.empty:
        grouped = station_comparison_df.groupby(
            ["short_name", "province"], as_index=False
        ).agg(
            stations=("STATION_AES", "count"),
            actual_temp=("actual_temp", "mean"),
            normal_temp=("normal_temp", "mean"),
            actual_precip=("actual_precip", "mean"),
            normal_precip=("normal_precip", "mean"),
        )

        province_order = [
            "BC", "AB", "SK", "MB", "ON", "QC",
            "NB", "NS", "PE", "NL", "YT", "NT", "NU"
        ]
        order_map = {code: i for i, code in enumerate(province_order)}
        grouped["_order"] = grouped["short_name"].map(order_map).fillna(999)
        grouped = grouped.sort_values("_order")

        for _, row in grouped.iterrows():
            province_comparison.append({
                "short_name": row["short_name"],
                "province": row["province"],
                "stations": int(row["stations"]),
                "actual_temp": clean_number(row["actual_temp"]),
                "normal_temp": clean_number(row["normal_temp"]),
                "actual_precip": clean_number(row["actual_precip"]),
                "normal_precip": clean_number(row["normal_precip"]),
            })

    # --------------------------------------------------------
    # 05 & 06. Rankings.
    # --------------------------------------------------------
    temperature_ranking = annual_station.sort_values(
        "annual_temp", ascending=False
    )
    precipitation_ranking = annual_station.sort_values(
        "annual_precip", ascending=False
    )

    temperature_ranking_data = []
    for rank, (_, row) in enumerate(
        temperature_ranking.iterrows(), start=1
    ):
        temperature_ranking_data.append({
            "rank": rank,
            "station": row["STATION_NAME"],
            "province": row["province"],
            "value": clean_number(row["annual_temp"]),
        })

    precipitation_ranking_data = []
    for rank, (_, row) in enumerate(
        precipitation_ranking.iterrows(), start=1
    ):
        precipitation_ranking_data.append({
            "rank": rank,
            "station": row["STATION_NAME"],
            "province": row["province"],
            "value": clean_number(row["annual_precip"]),
        })

    # --------------------------------------------------------
    # 02. Map data — exactly the selected stations.
    # --------------------------------------------------------
    annual_lookup = annual_station.set_index("STATION_AES")
    comparison_lookup = (
        station_comparison_df.set_index("STATION_AES")
        if not station_comparison_df.empty
        else None
    )

    map_data = []

    for _, row in map_stations.iterrows():
        station_id = row["STATION_AES"]
        annual_row = (
            annual_lookup.loc[station_id]
            if station_id in annual_lookup.index
            else None
        )
        comparison_row = (
            comparison_lookup.loc[station_id]
            if comparison_lookup is not None
            and station_id in comparison_lookup.index
            else None
        )

        map_data.append({
            "id": station_id,
            "station": row["STATION_NAME"],
            "province": row["province"],
            "reference_city": row.get("reference_city"),
            "latitude": clean_number(row["LATITUDE"], 5),
            "longitude": clean_number(row["LONGITUDE"], 5),
            "temperature_2025": (
                clean_number(annual_row["annual_temp"])
                if annual_row is not None else None
            ),
            "precipitation_2025": (
                clean_number(annual_row["annual_precip"])
                if annual_row is not None else None
            ),
            "temperature_normal": (
                clean_number(comparison_row["normal_temp"])
                if comparison_row is not None else None
            ),
            "precipitation_normal": (
                clean_number(comparison_row["normal_precip"])
                if comparison_row is not None else None
            ),
        })

    # --------------------------------------------------------
    # Final JSON — ONLY data needed by the browser.
    # --------------------------------------------------------
    output = {
        "metadata": {
            "title": "Canada Climate 2025",
            "year": 2025,
            "normals_period": "1991-2020",
            "selected_station_count": int(len(station_info)),
            "map_station_count": int(len(map_data)),
            "province_count": int(len(province_comparison)),
            "notes": [
                "All visualizations use the selected validated 2025 stations.",
                "The map contains the same selected stations as the analytical charts.",
                "Temperature is calculated as the daily mean of MAX_TEMP and MIN_TEMP.",
                "Annual precipitation is the sum of DAILY_PRECIP for each station.",
                "Province/territory comparison values are simple averages across represented stations.",
                "Annual temperature normals are calculated from monthly 1991-2020 normals using month-length weighting.",
            ],
        },
        "temperature_overview": temperature_overview,
        "province_comparison": province_comparison,
        "temperature_ranking": temperature_ranking_data,
        "precipitation_ranking": precipitation_ranking_data,
        "map_stations": map_data,
        "diagnostics": {
            "missing_normals": missing_normals,
        },
    }

    # Compact JSON: no indentation and no GeoJSON inside it.
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = OUTPUT_FILE.stat().st_size / 1024

    print(f"\nCreated: {OUTPUT_FILE}")
    print(f"data.json size: {size_kb:.1f} KB")
    print(f"Selected stations: {len(station_info)}")
    print(f"Map stations: {len(map_data)}")
    print(f"Province/territory groups: {len(province_comparison)}")
    print(f"Missing normals combinations: {len(missing_normals)}")


if __name__ == "__main__":
    main()

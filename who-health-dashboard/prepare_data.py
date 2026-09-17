import pandas as pd
from pathlib import Path

# ============================================================
# WHO HEALTH DASHBOARD — DATA PREPARATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

SPENDING_USD_FILE = RAW_DATA_DIR / "data.xlsx"
SPENDING_GDP_FILE = RAW_DATA_DIR / "data (1).xlsx"
CANCER_FILE = RAW_DATA_DIR / "data (2).xlsx"
DTP3_FILE = RAW_DATA_DIR / "data (3).xlsx"

OUTPUT_FILE = PROCESSED_DATA_DIR / "who_health_2019.csv"



def read_who_file(path):
    """Read a WHO Excel export. The real header starts on row 3."""
    df = pd.read_excel(path, header=2)

    required = [
        "SpatialDimValueCode",
        "Location",
        "Period",
        "FactValueNumeric",
    ]

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")

    return df[required].copy()


def get_2019(df, indicator_name):
    """Keep the 2019 observation for an annual indicator."""
    result = df[df["Period"].astype(str).str.strip() == "2019"].copy()

    duplicates = result[
        result["SpatialDimValueCode"].duplicated(keep=False)
    ]

    if not duplicates.empty:
        raise ValueError(
            f"{indicator_name}: duplicate country codes found:\n"
            f"{duplicates[['SpatialDimValueCode', 'Location']].to_string(index=False)}"
        )

    return result[
        ["SpatialDimValueCode", "Location", "FactValueNumeric"]
    ].copy()


# ============================================================
# 1. Read the four required files
# ============================================================

spending_usd = read_who_file(SPENDING_USD_FILE)
spending_gdp = read_who_file(SPENDING_GDP_FILE)
cancer = read_who_file(CANCER_FILE)
dtp3 = read_who_file(DTP3_FILE)


# ============================================================
# 2. Select the required periods
# ============================================================

spending_usd = get_2019(
    spending_usd,
    "Health spending per capita"
).rename(
    columns={"FactValueNumeric": "health_spending_usd"}
)

spending_gdp = get_2019(
    spending_gdp,
    "Health spending % GDP"
).rename(
    columns={"FactValueNumeric": "health_spending_gdp"}
)

dtp3 = get_2019(
    dtp3,
    "DTP3 vaccination"
).rename(
    columns={"FactValueNumeric": "dtp3"}
)

# Cancer survival is already a 2017–2021 period estimate.
cancer = cancer[
    cancer["Period"].astype(str).str.strip() == "2017-2021"
].copy()

cancer = cancer[
    ["SpatialDimValueCode", "Location", "FactValueNumeric"]
].rename(
    columns={"FactValueNumeric": "cancer_survival"}
)

if cancer["SpatialDimValueCode"].duplicated().any():
    raise ValueError("Cancer survival contains duplicate country codes.")


# ============================================================
# 3. Merge by WHO country code
# ============================================================

merged = (
    spending_usd[
        ["SpatialDimValueCode", "Location", "health_spending_usd"]
    ]
    .merge(
        spending_gdp[
            ["SpatialDimValueCode", "health_spending_gdp"]
        ],
        on="SpatialDimValueCode",
        how="outer"
    )
    .merge(
        cancer[
            ["SpatialDimValueCode", "cancer_survival"]
        ],
        on="SpatialDimValueCode",
        how="outer"
    )
    .merge(
        dtp3[
            ["SpatialDimValueCode", "dtp3"]
        ],
        on="SpatialDimValueCode",
        how="outer"
    )
)


# ============================================================
# 4. Restore country names for all codes
# ============================================================

locations = pd.concat([
    spending_usd[["SpatialDimValueCode", "Location"]],
    spending_gdp[["SpatialDimValueCode", "Location"]],
    cancer[["SpatialDimValueCode", "Location"]],
    dtp3[["SpatialDimValueCode", "Location"]],
]).drop_duplicates("SpatialDimValueCode")

merged = (
    merged.drop(columns=["Location"], errors="ignore")
    .merge(locations, on="SpatialDimValueCode", how="left")
)


# ============================================================
# 5. Clean column names and order
# ============================================================

merged = merged.rename(columns={
    "SpatialDimValueCode": "country_code",
    "Location": "country",
})

merged = merged[
    [
        "country_code",
        "country",
        "health_spending_usd",
        "health_spending_gdp",
        "cancer_survival",
        "dtp3",
    ]
]

numeric_columns = [
    "health_spending_usd",
    "health_spending_gdp",
    "cancer_survival",
    "dtp3",
]

for column in numeric_columns:
    merged[column] = pd.to_numeric(
        merged[column],
        errors="coerce"
    )


# ============================================================
# 6. Validation
# ============================================================

print("=" * 65)
print("WHO HEALTH DASHBOARD — VALIDATION")
print("=" * 65)

print(f"Health spending per capita (2019): {len(spending_usd)}")
print(f"Health spending % GDP (2019):      {len(spending_gdp)}")
print(f"Cancer survival (2017–2021):       {len(cancer)}")
print(f"DTP3 vaccination (2019):           {len(dtp3)}")
print()
print(f"Merged countries:                   {len(merged)}")
print()

print("Missing values:")
missing = merged[numeric_columns].isna().sum()
print(missing.to_string())
print()

complete = merged.dropna(subset=numeric_columns)

print(
    "Countries with all 4 indicators:   "
    f"{len(complete)}"
)
print()

print(
    "Duplicate country codes after merge: "
    f"{merged['country_code'].duplicated().sum()}"
)
print()

if len(complete) < len(merged):
    print("Countries with incomplete data:")
    print(
        merged[
            merged[numeric_columns].isna().any(axis=1)
        ][
            ["country_code", "country"] + numeric_columns
        ].to_string(index=False)
    )
else:
    print("All merged countries have complete data.")

print()
print("Value ranges:")
for column in numeric_columns:
    print(
        f"{column:22s}: "
        f"{merged[column].min():.2f} – "
        f"{merged[column].max():.2f}"
    )


# ============================================================
# 7. Save the cleaned CSV
# ============================================================

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

merged.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print()
print("=" * 65)
print("FILE CREATED SUCCESSFULLY")
print("=" * 65)
print(OUTPUT_FILE)
print(f"Rows: {len(merged)}")
print(f"Columns: {len(merged.columns)}")

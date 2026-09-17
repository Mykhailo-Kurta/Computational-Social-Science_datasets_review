
import requests
import pandas as pd
import time
import json


# ============================================================
# SETTINGS
# ============================================================

# None = analyze the entire catalogue
CANADA_DATASET_LIMIT = None
WHO_INDICATOR_LIMIT = None

# Delay between requests
REQUEST_DELAY = 0.1

# Timeout for API requests
REQUEST_TIMEOUT = 60


# ============================================================
# CANADA OPEN GOVERNMENT PORTAL
# ============================================================

CANADA_API = (
    "https://open.canada.ca/data/en/api/3/action/package_search"
)


def get_canada_datasets(limit=None):
    """
    Download dataset metadata from the Canadian
    Open Government Portal using the CKAN API.
    """

    datasets = []

    start = 0
    page_size = 100

    while True:

        params = {
            "q": "",
            "rows": page_size,
            "start": start
        }

        response = requests.get(
            CANADA_API,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        result = response.json()["result"]

        batch = result["results"]
        total = result["count"]

        if not batch:
            break

        datasets.extend(batch)

        print(
            f"Canada: {len(datasets):,} / "
            f"{total:,} datasets collected"
        )

        start += len(batch)

        if limit is not None and len(datasets) >= limit:
            datasets = datasets[:limit]
            break

        if start >= total:
            break

        time.sleep(REQUEST_DELAY)

    print()
    print(
        f"Canada datasets collected: "
        f"{len(datasets):,}"
    )

    return datasets


def analyze_canada(datasets):

    rows = []

    for dataset in datasets:

        dataset_id = dataset.get("id")
        title = dataset.get("title", "Unknown")
        description = dataset.get("notes", "")

        organization = dataset.get("organization") or {}

        publisher = organization.get(
            "title",
            "Unknown"
        )

        resources = dataset.get("resources", [])

        resource_sizes = []

        resource_urls = []

        resource_formats = []

        for resource in resources:

            # ----------------------------
            # Size
            # ----------------------------

            size = resource.get("size")

            if size is not None:

                try:
                    size = float(size)

                    # Ignore zero / negative values
                    if size > 0:
                        resource_sizes.append(size)

                except (ValueError, TypeError):
                    pass

            # ----------------------------
            # URL
            # ----------------------------

            url = resource.get("url")

            if url:
                resource_urls.append(url)

            # ----------------------------
            # Format
            # ----------------------------

            fmt = resource.get("format")

            if fmt:
                resource_formats.append(fmt)

        # ----------------------------------------------------
        # Dataset size definition
        #
        # We use the largest downloadable resource
        # as the dataset size.
        # ----------------------------------------------------

        if resource_sizes:
            dataset_size = max(resource_sizes)
        else:
            dataset_size = None

        rows.append({
            "id": dataset_id,
            "title": title,
            "publisher": publisher,
            "size_bytes": dataset_size,
            "description": description,
            "num_resources": len(resources),
            "formats": ", ".join(
                sorted(set(resource_formats))
            ),
            "resource_url": (
                resource_urls[0]
                if resource_urls
                else None
            ),
            "dataset_url": (
                f"https://open.canada.ca/data/en/"
                f"dataset/{dataset_id}"
            )
        })

    df = pd.DataFrame(rows)

    # ========================================================
    # STATISTICS
    # ========================================================

    valid_sizes = (
        df["size_bytes"]
        .dropna()
    )

    print()
    print("=" * 70)
    print("CANADA OPEN GOVERNMENT PORTAL")
    print("=" * 70)

    print(
        f"Total datasets analyzed: "
        f"{len(df):,}"
    )

    print(
        f"Datasets with valid size information: "
        f"{len(valid_sizes):,}"
    )

    print(
        f"Datasets without size information: "
        f"{len(df) - len(valid_sizes):,}"
    )

    if len(valid_sizes) > 0:

        average_mb = (
            valid_sizes.mean()
            / (1024 ** 2)
        )

        minimum_mb = (
            valid_sizes.min()
            / (1024 ** 2)
        )

        maximum_mb = (
            valid_sizes.max()
            / (1024 ** 2)
        )

        print(
            f"\nAverage dataset size: "
            f"{average_mb:.2f} MB"
        )

        print(
            f"Minimum dataset size: "
            f"{minimum_mb:.4f} MB"
        )

        print(
            f"Maximum dataset size: "
            f"{maximum_mb:.2f} MB"
        )

    # ========================================================
    # TOP 3
    # ========================================================

    top3 = (
        df
        .dropna(subset=["size_bytes"])
        .sort_values(
            "size_bytes",
            ascending=False
        )
        .head(3)
        .copy()
    )

    print("\nTOP 3 LARGEST CANADIAN DATASETS")

    for i, (_, row) in enumerate(
        top3.iterrows(),
        1
    ):

        size_mb = (
            row["size_bytes"]
            / (1024 ** 2)
        )

        print(f"\n{i}. {row['title']}")
        print(f"   Size: {size_mb:.2f} MB")
        print(f"   Publisher: {row['publisher']}")
        print(f"   ID: {row['id']}")
        print(f"   URL: {row['dataset_url']}")

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    df.to_csv(
        "canada_datasets_analysis.csv",
        index=False,
        encoding="utf-8-sig"
    )

    top3.to_csv(
        "canada_top3.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return df, top3


# ============================================================
# WHO GLOBAL HEALTH OBSERVATORY
# ============================================================

WHO_INDICATOR_API = (
    "https://ghoapi.azureedge.net/api/Indicator"
)


def get_who_indicators(limit=None):

    response = requests.get(
        WHO_INDICATOR_API,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    indicators = data.get(
        "value",
        []
    )

    if limit is not None:
        indicators = indicators[:limit]

    print()
    print(
        f"WHO indicators collected: "
        f"{len(indicators):,}"
    )

    return indicators


def get_who_indicator_records(
    indicator_code
):

    url = (
        f"https://ghoapi.azureedge.net/api/"
        f"{indicator_code}"
    )

    try:

        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        records = data.get(
            "value",
            []
        )

        return len(records)

    except Exception as e:

        print(
            f"\nWARNING: failed to retrieve "
            f"{indicator_code}: {e}"
        )

        return None


def analyze_who(indicators):

    rows = []

    total = len(indicators)

    for i, indicator in enumerate(
        indicators,
        1
    ):

        code = indicator.get(
            "IndicatorCode"
        )

        name = indicator.get(
            "IndicatorName",
            "Unknown"
        )

        print(
            f"WHO: {i:,}/{total:,} "
            f"{name[:100]}"
        )

        record_count = (
            get_who_indicator_records(
                code
            )
        )

        rows.append({
            "indicator_code": code,
            "indicator_name": name,
            "records": record_count
        })

        # Save progress every 100 indicators
        if i % 100 == 0:

            progress_df = pd.DataFrame(
                rows
            )

            progress_df.to_csv(
                "who_analysis_progress.csv",
                index=False,
                encoding="utf-8-sig"
            )

            print(
                f"   Progress saved "
                f"({i:,}/{total:,})"
            )

        time.sleep(
            REQUEST_DELAY
        )

    df = pd.DataFrame(rows)

    # ========================================================
    # STATISTICS
    # ========================================================

    valid_records = (
        df["records"]
        .dropna()
    )

    positive_records = (
        df.loc[
            df["records"] > 0,
            "records"
        ]
        .dropna()
    )

    zero_records = (
        df["records"] == 0
    ).sum()

    failed_requests = (
        df["records"].isna()
    ).sum()

    print()
    print("=" * 70)
    print("WHO GLOBAL HEALTH OBSERVATORY")
    print("=" * 70)

    print(
        f"Total indicators analyzed: "
        f"{len(df):,}"
    )

    print(
        f"Indicators with API data: "
        f"{len(valid_records):,}"
    )

    print(
        f"Indicators with 0 records: "
        f"{zero_records:,}"
    )

    print(
        f"Failed API requests: "
        f"{failed_requests:,}"
    )

    # --------------------------------------------------------
    # Average
    #
    # Zero-record indicators are excluded because
    # they do not represent an actual dataset.
    # --------------------------------------------------------

    if len(positive_records) > 0:

        average_records = (
            positive_records.mean()
        )

        minimum_records = (
            positive_records.min()
        )

        maximum_records = (
            positive_records.max()
        )

        print(
            f"\nAverage records per indicator: "
            f"{average_records:.2f}"
        )

        print(
            f"Minimum records: "
            f"{int(minimum_records):,}"
        )

        print(
            f"Maximum records: "
            f"{int(maximum_records):,}"
        )

    # ========================================================
    # TOP 3
    # ========================================================

    top3 = (
        df
        .dropna(subset=["records"])
        .loc[
            lambda x: x["records"] > 0
        ]
        .sort_values(
            "records",
            ascending=False
        )
        .head(3)
        .copy()
    )

    print("\nTOP 3 LARGEST WHO DATASETS")

    for i, (_, row) in enumerate(
        top3.iterrows(),
        1
    ):

        print(
            f"\n{i}. {row['indicator_name']}"
        )

        print(
            f"   Records: "
            f"{int(row['records']):,}"
        )

        print(
            f"   Code: "
            f"{row['indicator_code']}"
        )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    df.to_csv(
        "who_indicators_analysis.csv",
        index=False,
        encoding="utf-8-sig"
    )

    top3.to_csv(
        "who_top3.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return df, top3


# ============================================================
# SUMMARY FILE
# ============================================================

def create_summary(
    canada_df,
    canada_top3,
    who_df,
    who_top3
):

    lines = []

    lines.append(
        "DATASET ANALYSIS SUMMARY"
    )

    lines.append(
        "=" * 70
    )

    # ========================================================
    # CANADA
    # ========================================================

    lines.append(
        "\nCANADA OPEN GOVERNMENT PORTAL"
    )

    lines.append(
        "-" * 70
    )

    canada_sizes = (
        canada_df["size_bytes"]
        .dropna()
    )

    lines.append(
        f"Total datasets analyzed: "
        f"{len(canada_df):,}"
    )

    lines.append(
        f"Datasets with size information: "
        f"{len(canada_sizes):,}"
    )

    lines.append(
        f"Datasets without size information: "
        f"{len(canada_df) - len(canada_sizes):,}"
    )

    if len(canada_sizes) > 0:

        lines.append(
            f"Average size: "
            f"{canada_sizes.mean() / (1024 ** 2):.2f} MB"
        )

        lines.append(
            f"Minimum size: "
            f"{canada_sizes.min() / (1024 ** 2):.4f} MB"
        )

        lines.append(
            f"Maximum size: "
            f"{canada_sizes.max() / (1024 ** 2):.2f} MB"
        )

    lines.append(
        "\nTop 3 largest datasets:"
    )

    for i, (_, row) in enumerate(
        canada_top3.iterrows(),
        1
    ):

        size_mb = (
            row["size_bytes"]
            / (1024 ** 2)
        )

        lines.append(
            f"{i}. {row['title']} "
            f"({size_mb:.2f} MB)"
        )

    # ========================================================
    # WHO
    # ========================================================

    lines.append(
        "\nWHO GLOBAL HEALTH OBSERVATORY"
    )

    lines.append(
        "-" * 70
    )

    valid = (
        who_df["records"]
        .dropna()
    )

    positive = (
        who_df.loc[
            who_df["records"] > 0,
            "records"
        ]
    )

    lines.append(
        f"Total indicators analyzed: "
        f"{len(who_df):,}"
    )

    lines.append(
        f"Indicators with data: "
        f"{len(valid):,}"
    )

    lines.append(
        f"Indicators with 0 records: "
        f"{(who_df['records'] == 0).sum():,}"
    )

    lines.append(
        f"Failed API requests: "
        f"{who_df['records'].isna().sum():,}"
    )

    if len(positive) > 0:

        lines.append(
            f"Average records per indicator: "
            f"{positive.mean():.2f}"
        )

        lines.append(
            f"Minimum records: "
            f"{int(positive.min()):,}"
        )

        lines.append(
            f"Maximum records: "
            f"{int(positive.max()):,}"
        )

    lines.append(
        "\nTop 3 largest indicators:"
    )

    for i, (_, row) in enumerate(
        who_top3.iterrows(),
        1
    ):

        lines.append(
            f"{i}. {row['indicator_name']} "
            f"({int(row['records']):,} records)"
        )

    # ========================================================
    # WRITE
    # ========================================================

    with open(
        "summary.txt",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(lines)
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("DATASET ANALYSIS")
    print("=" * 70)

    # --------------------------------------------------------
    # CANADA
    # --------------------------------------------------------

    canada_datasets = (
        get_canada_datasets(
            CANADA_DATASET_LIMIT
        )
    )

    canada_df, canada_top3 = (
        analyze_canada(
            canada_datasets
        )
    )

    # --------------------------------------------------------
    # WHO
    # --------------------------------------------------------

    who_indicators = (
        get_who_indicators(
            WHO_INDICATOR_LIMIT
        )
    )

    who_df, who_top3 = (
        analyze_who(
            who_indicators
        )
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    create_summary(
        canada_df,
        canada_top3,
        who_df,
        who_top3
    )

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)

    print("\nFiles created:")

    print("  canada_datasets_analysis.csv")
    print("  canada_top3.csv")
    print("  who_indicators_analysis.csv")
    print("  who_top3.csv")
    print("  who_analysis_progress.csv")
    print("  summary.txt")

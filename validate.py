"""Validate the structure and required values in the raw incident data."""

from collections import Counter

import pandas as pd
from prefect import task

EXPECTED_COLUMNS = [
    "date_time",
    "id",
    "type",
    "subtype",
    "location",
    "last_updated",
    "description",
]

# The notebook says that non-numeric IDs should be marked invalid and removed
# during transformation. Therefore, ID is intentionally not in this list.
REQUIRED_COLUMNS = ["date_time", "type", "location"]


def check_valid_schema(df: pd.DataFrame) -> None:
    """Fail if expected columns are missing or unexpected columns are present."""
    if Counter(df.columns) != Counter(EXPECTED_COLUMNS):
        missing = sorted(set(EXPECTED_COLUMNS) - set(df.columns))
        unexpected = sorted(set(df.columns) - set(EXPECTED_COLUMNS))
        raise ValueError(
            f"Schema mismatch. Missing columns: {missing}. "
            f"Unexpected columns: {unexpected}."
        )


def check_numeric_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert IDs to numeric values.

    Invalid or fractional IDs become NaN. Transformation removes those rows.
    """
    df = df.copy()
    numeric_ids = pd.to_numeric(df["id"], errors="coerce")

    # IDs are expected to be whole numbers, not values such as 12.5.
    whole_number_mask = numeric_ids.notna() & (numeric_ids % 1 == 0)
    df["id"] = numeric_ids.where(whole_number_mask)
    return df


def check_missing_values(df: pd.DataFrame) -> None:
    """Fail when a required field is null, empty, or whitespace-only."""
    for column in REQUIRED_COLUMNS:
        values = df[column]
        missing = values.isna() | values.astype("string").str.strip().eq("")
        if missing.any():
            count = int(missing.sum())
            raise ValueError(
                f"{count} missing/empty value(s) found in required column "
                f"'{column}'."
            )


def verify_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Parse timestamps and fail with a clear error if any value is invalid."""
    parsed = pd.to_datetime(df["date_time"], errors="coerce")

    invalid = parsed.isna()
    if invalid.any():
        examples = df.loc[invalid, "date_time"].head(5).tolist()
        raise ValueError(
            f"{int(invalid.sum())} invalid date_time value(s). "
            f"Examples: {examples}"
        )

    df = df.copy()
    df["date_time"] = parsed
    return df


@task
def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate schema, required values, IDs, and timestamps.

    Invalid IDs are kept as NaN here so transform_data can remove those rows,
    matching the handling described in the notebook.
    """
    check_valid_schema(df)
    check_missing_values(df)
    df = check_numeric_id(df)
    df = verify_datetime(df)
    return df

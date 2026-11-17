"""Run the notebook's extract -> validate -> transform stages."""

from extract import extract_data
from validate import validate_data
from transform import transform_data


def main() -> None:
    print("1/3 Extracting data from Socrata...")
    raw_data = extract_data()
    print(f"Fetched {len(raw_data):,} rows.")
    print(raw_data.head(), "\n")

    print("2/3 Validating data...")
    validated_data = validate_data(raw_data)
    print(f"Validated {len(validated_data):,} rows.")

    print("3/3 Transforming data...")
    transformed_data = transform_data(validated_data)
    print(f"Transformed {len(transformed_data):,} rows.")
    print("Columns:", transformed_data.columns.tolist())
    print(transformed_data.head())


if __name__ == "__main__":
    main()

from create_school_geojson import create_school_geojson
from fetch import run_fetch
from transform import transform_community_partners
from utils.paths import PUBLIC_DIR

def main():
    # Step 1: Fetch data from APIs and save raw CSVs
    run_fetch()

    # Step 2: Transform raw CSVs into a combined cleaned CSV
    grouped_df = transform_community_partners()

    # Step 3: Export the combined cleaned data to JSON for mapping
    out_path_schools = PUBLIC_DIR / "site_data" / "schools.geojson"
    create_school_geojson(grouped_df, out_path_schools)


if __name__ == "__main__":
    main()

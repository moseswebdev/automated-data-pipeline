"""End-to-end ETL pipeline entrypoint for scheduled execution."""

from ingestion.load_raw import main as run_ingestion
from cleaning.transform_sales import main as run_transformation


def main():
    run_ingestion()
    run_transformation()


if __name__ == "__main__":
    main()
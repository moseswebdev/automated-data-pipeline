"""End-to-end ETL and reporting pipeline entrypoint."""

from ingestion.load_raw import main as run_ingestion
from cleaning.transform_sales import main as run_transformation
from reporting.generate_reports import main as run_reporting


def main():
    run_ingestion()
    run_transformation()
    run_reporting()


if __name__ == "__main__":
    main()
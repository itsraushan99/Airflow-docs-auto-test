from airflow.sdk import dag, task
from pendulum import datetime


@dag(
    start_date=datetime(2026, 8, 1),
    schedule="@daily",
    catchup=False,
    default_args={"owner": "data-quality-team", "retries": 2},
    tags=["example", "data-quality", "daily"],
)
def daily_data_quality_checks():
    """Run daily quality checks for a sample orders dataset profile."""

    @task
    def extract_dataset_profile() -> dict:
        return {
            "dataset": "orders_daily",
            "row_count": 4,
            "null_counts": {"order_id": 0, "customer_id": 0, "amount": 0},
            "duplicate_count": 0,
        }

    @task
    def run_quality_rules(profile: dict) -> list[dict]:
        return [
            {"rule": "row_count_positive", "passed": profile["row_count"] > 0},
            {"rule": "no_duplicate_orders", "passed": profile["duplicate_count"] == 0},
            {"rule": "required_fields_present", "passed": all(count == 0 for count in profile["null_counts"].values())},
        ]

    @task
    def summarize_quality_results(results: list[dict]) -> dict:
        failed = [result for result in results if not result["passed"]]
        return {"total_rules": len(results), "failed_rules": failed, "passed": not failed}

    @task
    def publish_quality_summary(summary: dict) -> None:
        if not summary["passed"]:
            raise ValueError(f"Data quality checks failed: {summary['failed_rules']}")
        print(f"All {summary['total_rules']} data quality rules passed.")

    publish_quality_summary(summarize_quality_results(run_quality_rules(extract_dataset_profile())))


daily_data_quality_checks()

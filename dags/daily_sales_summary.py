from airflow.sdk import dag, task
from pendulum import datetime


@dag(
    start_date=datetime(2026, 8, 1),
    schedule="@daily",
    catchup=False,
    default_args={"owner": "data-team", "retries": 2},
    tags=["example", "sales", "daily"],
)
def daily_sales_summary():
    """Build a daily regional sales summary from a small in-memory order sample."""

    @task
    def extract_orders() -> list[dict]:
        return [
            {"order_id": "A100", "region": "north", "amount": 125.50},
            {"order_id": "A101", "region": "south", "amount": 88.25},
            {"order_id": "A102", "region": "north", "amount": 215.00},
            {"order_id": "A103", "region": "west", "amount": 47.75},
        ]

    @task
    def validate_orders(orders: list[dict]) -> list[dict]:
        invalid_orders = [order for order in orders if order["amount"] <= 0]
        if invalid_orders:
            raise ValueError(f"Found invalid orders: {invalid_orders}")
        return orders

    @task
    def summarize_by_region(orders: list[dict]) -> dict:
        summary: dict[str, float] = {}
        for order in orders:
            summary[order["region"]] = summary.get(order["region"], 0.0) + order["amount"]
        return summary

    @task
    def publish_summary(summary: dict) -> None:
        for region, amount in sorted(summary.items()):
            print(f"{region}: {amount:.2f}")

    publish_summary(summarize_by_region(validate_orders(extract_orders())))


daily_sales_summary()

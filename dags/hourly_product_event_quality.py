from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import ShortCircuitOperator
from airflow.sdk import dag, task, task_group
from pendulum import datetime


def has_events(ti) -> bool:
    events = ti.xcom_pull(task_ids="extract_events") or []
    print(f"Found {len(events)} product events.")
    return len(events) > 0


@dag(
    start_date=datetime(2026, 8, 1),
    schedule="@hourly",
    catchup=False,
    default_args={"owner": "product-analytics", "retries": 1},
    tags=["example", "events", "quality"],
)
def hourly_product_event_quality():
    """Run lightweight product-event quality checks every hour."""

    start = EmptyOperator(task_id="start")

    @task
    def extract_events() -> list[dict]:
        return [
            {"event_id": "E001", "user_id": "U001", "event_type": "page_view", "latency_ms": 82},
            {"event_id": "E002", "user_id": "U002", "event_type": "add_to_cart", "latency_ms": 145},
            {"event_id": "E003", "user_id": "U001", "event_type": "checkout", "latency_ms": 311},
        ]

    continue_if_events_exist = ShortCircuitOperator(
        task_id="continue_if_events_exist",
        python_callable=has_events,
    )

    @task_group
    def quality_checks():
        check_required_fields = BashOperator(
            task_id="check_required_fields",
            bash_command='echo "Required event fields are present"',
        )

        check_allowed_event_types = BashOperator(
            task_id="check_allowed_event_types",
            bash_command='echo "Event types are in the allowed set"',
        )

        check_latency_threshold = BashOperator(
            task_id="check_latency_threshold",
            bash_command='echo "Latency values are below alert thresholds"',
        )

        check_required_fields >> [check_allowed_event_types, check_latency_threshold]

    @task
    def summarize_quality_results(events: list[dict]) -> None:
        event_types = sorted({event["event_type"] for event in events})
        max_latency = max(event["latency_ms"] for event in events)
        print(f"Validated {len(events)} events.")
        print(f"Event types: {event_types}")
        print(f"Max latency: {max_latency} ms")

    archive_metrics = BashOperator(
        task_id="archive_metrics",
        bash_command='echo "Archived event quality metrics for {{ data_interval_start }}"',
    )

    end = EmptyOperator(task_id="end")

    events = extract_events()
    checks = quality_checks()
    summary = summarize_quality_results(events)

    start >> events >> continue_if_events_exist >> checks >> summary >> archive_metrics >> end


hourly_product_event_quality()

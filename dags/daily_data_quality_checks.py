from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from airflow.sdk import dag
from pendulum import datetime


def profile_customer_rows() -> dict:
    rows = [
        {"customer_id": "C001", "email": "anika@example.com", "status": "active"},
        {"customer_id": "C002", "email": "kabir@example.com", "status": "inactive"},
        {"customer_id": "C003", "email": "meera@example.com", "status": "active"},
    ]
    null_email_count = sum(1 for row in rows if not row["email"])
    return {"row_count": len(rows), "null_email_count": null_email_count}


def choose_quality_path(ti) -> str:
    profile = ti.xcom_pull(task_ids="profile_customer_rows")
    if profile["null_email_count"] > 0:
        return "quarantine_bad_rows"
    return "approve_dataset"


def publish_quality_summary(ti) -> None:
    profile = ti.xcom_pull(task_ids="profile_customer_rows")
    print(f"Customer rows checked: {profile['row_count']}")
    print(f"Null emails found: {profile['null_email_count']}")


@dag(
    start_date=datetime(2026, 8, 1),
    schedule="@daily",
    catchup=False,
    default_args={"owner": "data-quality", "retries": 1},
    tags=["example", "quality", "operators"],
)
def daily_data_quality_checks():
    """Run daily data-quality checks using Python, Bash, Branch, and Empty operators."""

    start = EmptyOperator(task_id="start")

    profile = PythonOperator(
        task_id="profile_customer_rows",
        python_callable=profile_customer_rows,
    )

    choose_path = BranchPythonOperator(
        task_id="choose_quality_path",
        python_callable=choose_quality_path,
    )

    quarantine_bad_rows = BashOperator(
        task_id="quarantine_bad_rows",
        bash_command='echo "Quarantined bad customer records for {{ ds }}"',
    )

    approve_dataset = BashOperator(
        task_id="approve_dataset",
        bash_command='echo "Customer dataset approved for {{ ds }}"',
    )

    summarize = PythonOperator(
        task_id="publish_quality_summary",
        python_callable=publish_quality_summary,
        trigger_rule="none_failed_min_one_success",
    )

    end = EmptyOperator(task_id="end")

    start >> profile >> choose_path
    choose_path >> [quarantine_bad_rows, approve_dataset] >> summarize >> end


daily_data_quality_checks()

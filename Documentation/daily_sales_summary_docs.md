# DAG Documentation — `daily_sales_summary`

Generated at `2026-08-19T10:00:29+00:00` from `dags/daily_sales_summary.py`.

## `daily_sales_summary`

No description provided.

| Property | Value |
| --- | --- |
| Schedule | `0 0 * * *` |
| Start date | `2026-08-01T00:00:00+00:00` |
| End date | `Not set` |
| Catchup | `False` |
| Max active runs | `16` |
| Owner | `data-team` |
| Tags | `daily`, `example`, `sales` |
| Task count | `4` |

### Task Graph

```mermaid
flowchart TD
    task_1["extract_orders<br/>_PythonDecoratedOperator"]
    task_2["publish_summary<br/>_PythonDecoratedOperator"]
    task_3["summarize_by_region<br/>_PythonDecoratedOperator"]
    task_4["validate_orders<br/>_PythonDecoratedOperator"]
    task_1 --> task_4
    task_3 --> task_2
    task_4 --> task_3
```

### Tasks

| Task ID | Operator | Owner | Retries | Trigger Rule | Pool | Downstream |
| --- | --- | --- | --- | --- | --- | --- |
| `extract_orders` | `_PythonDecoratedOperator` | `data-team` | `2` | `all_success` | `default_pool` | `validate_orders` |
| `publish_summary` | `_PythonDecoratedOperator` | `data-team` | `2` | `all_success` | `default_pool` | None |
| `summarize_by_region` | `_PythonDecoratedOperator` | `data-team` | `2` | `all_success` | `default_pool` | `publish_summary` |
| `validate_orders` | `_PythonDecoratedOperator` | `data-team` | `2` | `all_success` | `default_pool` | `summarize_by_region` |

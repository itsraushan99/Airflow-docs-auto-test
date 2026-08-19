FROM apache/airflow:3.0.6

WORKDIR /opt/airflow

COPY --chown=airflow:0 requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY --chown=airflow:0 dags /opt/airflow/dags
COPY --chown=airflow:0 scripts /opt/airflow/scripts

CMD ["python", "/opt/airflow/scripts/generate_dag_docs.py", "--dags-dir", "/opt/airflow/dags", "--output-dir", "/opt/airflow/Documentation"]

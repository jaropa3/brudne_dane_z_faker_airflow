FROM apache/airflow:2.9.3-python3.12

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# psycopg2-binary zamiast psycopg2 — nie wymaga gcc w runtime
RUN pip install --no-cache-dir \
    psycopg2-binary \
    pandas \
    SQLAlchemy \
    pyyaml \
    openpyxl \
    chardet \
    faker \
    pyarrow \
    python-dotenv \
    pendulum

COPY --chown=airflow:root src/ /opt/airflow/src/

# multi-stage build
# First stage
FROM python:3.8-slim as builder
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc git python3-dev libpq-dev
RUN apt-get install -y --no-install-recommends libssl-dev libcurl4-openssl-dev
#WORKDIR /app
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn

# second stage
#FROM python:3.8-slim@sha256:8e9969d0711a6983ff935dfe2d68f09dcd82f5af5f6bf472c5674db2d462c486
FROM python:3.8-slim
RUN apt-get update
RUN apt-get install -y --no-install-recommends less libpq-dev
WORKDIR /app
RUN groupadd -g 999 python && useradd -r -u 999 -g python python
#RUN chown python:python /app /venv
COPY --chown=python:python --from=builder /venv /venv
COPY --chown=python:python . .
USER 999

ENV PATH="/venv/bin:$PATH"
# EXPOSE 5000 # now set using Compose
# HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD curl -f http://localhost:5000/health
#CMD ["/app/wsgi.sh"]

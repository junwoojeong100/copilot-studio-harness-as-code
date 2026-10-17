FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# classify_issue.py and label-policy.yaml are copied here from ../shared by scripts/sync_shared.sh before the build.
COPY server.py classify_issue.py label-policy.yaml ./

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
USER 10001

EXPOSE 8000
CMD ["python", "server.py"]

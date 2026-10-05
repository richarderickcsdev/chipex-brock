FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/brock/backend

WORKDIR /opt/brock
COPY backend/requirements.txt /opt/brock/backend/requirements.txt
RUN pip install --no-cache-dir -r /opt/brock/backend/requirements.txt

COPY backend/ /opt/brock/backend/
COPY docker/local_server.py /opt/brock/docker/local_server.py

EXPOSE 3000
CMD ["python", "/opt/brock/docker/local_server.py"]

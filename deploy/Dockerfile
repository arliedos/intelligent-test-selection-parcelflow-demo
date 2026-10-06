# Representative container definition for the ParcelFlow demo.
# Static deployment evidence only -- this image is not built or deployed as
# part of this repository's test command, and no base image is pulled here.
FROM python:3.11-slim

WORKDIR /app
COPY src/ src/
COPY config/ config/
COPY reference-data/ reference-data/
COPY ui/ ui/
COPY scripts/ scripts/
ENV PYTHONPATH=/app/src
ENV PARCELFLOW_ENVIRONMENT=ST

EXPOSE 8101

CMD ["python", "-m", "parcelflow.main"]

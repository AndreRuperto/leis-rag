FROM python:3.12-slim
WORKDIR /srv
COPY app/requirements*.txt /srv/app/
ARG INSTALL_EMBEDDINGS=0
RUN pip install --no-cache-dir -r /srv/app/requirements.txt \
    && if [ "$INSTALL_EMBEDDINGS" = "1" ]; then pip install --no-cache-dir -r /srv/app/requirements-embeddings.txt; fi
COPY app /srv/app
COPY dados/constituicao.md /srv/dados/constituicao.md
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/srv/dados
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

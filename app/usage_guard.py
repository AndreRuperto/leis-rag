"""Autorização e limites para chamadas pagas de IA.

A chave da OpenAI fica no backend; a pessoa informa somente o código
de acesso privado configurado pelo proprietário. O limite diário é
compartilhado pelo banco, inclusive entre instâncias da aplicação.
"""
import hmac
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .db import connection

_WINDOW_SECONDS = 60
_BUCKETS = defaultdict(deque)
_BUCKET_LOCK = threading.Lock()


def ai_configured():
    return bool(os.getenv("OPENAI_API_KEY", "").strip()) and bool(
        os.getenv("LEGAL_AI_ACCESS_TOKEN", "").strip()
    )


def web_configured():
    return ai_configured() and os.getenv(
        "LEGAL_WEB_SEARCH_ENABLED", "0"
    ).strip().lower() in {"1", "true", "yes", "on"}


def _bounded_int(name, default, lo, hi):
    try:
        value = int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        value = default
    return max(lo, min(hi, value))


def _rate_limit(client_id):
    """Proteção auxiliar contra rajadas; não substitui limites externos."""
    now = time.monotonic()
    limit = _bounded_int("LEGAL_AI_RATE_PER_MIN", 4, 1, 30)
    with _BUCKET_LOCK:
        bucket = _BUCKETS[client_id]
        while bucket and bucket[0] < now - _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Limite de consultas por minuto atingido. Tente novamente mais tarde.",
            )
        bucket.append(now)
        # Limpa entradas antigas quando há muitos clientes diferentes.
        if len(_BUCKETS) > 5000:
            expired = [key for key, values in _BUCKETS.items()
                       if not values or values[-1] < now - _WINDOW_SECONDS]
            for key in expired:
                _BUCKETS.pop(key, None)


def authorize_paid_ai(request: Request, access_token: str | None):
    """Autoriza e reserva uma consulta paga antes de chamar o provedor.

    Falha fechada: sem segredo privado não há chamada paga; proteção de
    quota transacional no PostgreSQL para múltiplas réplicas/reinícios.
    """
    expected = os.getenv("LEGAL_AI_ACCESS_TOKEN", "").strip()
    if not ai_configured():
        raise HTTPException(
            status_code=503,
            detail="A API paga de IA ainda não está disponível neste ambiente.",
        )
    if not access_token or not hmac.compare_digest(
        access_token.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(status_code=403, detail="Código de acesso à IA inválido ou ausente.")

    remote = request.client.host if request.client else "unknown"
    _rate_limit(remote)
    max_per_day = _bounded_int("LEGAL_AI_DAILY_LIMIT", 25, 1, 500)
    with connection() as conn:
        row = conn.execute("""
            INSERT INTO ai_daily_usage (day, requests)
            VALUES (CURRENT_DATE, 1)
            ON CONFLICT (day) DO UPDATE
                SET requests = ai_daily_usage.requests + 1
            WHERE ai_daily_usage.requests < %s
            RETURNING requests
        """, (max_per_day,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=429,
                detail="O limite diário de consultas à IA foi atingido.",
            )

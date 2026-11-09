"""Importação incremental de normas Markdown para o banco de pesquisa.

Exemplos:
  python -m app.ingest
  python -m app.ingest --path dados/federal/leis-ordinarias --limit 500
  EMBEDDINGS_ENABLED=1 python -m app.ingest --path dados/constituicao.md
"""
import argparse
import hashlib
import os
import re
from pathlib import Path

import yaml

from .db import connection, init_db

ARTICLE = re.compile(
    r"(?im)^\s*(?:\*\*)?\s*(Art(?:\.|igo)\s*\d+[º°o]?(?:-[A-Z])?)"
)
HEADING = re.compile(r"(?m)^#{1,4}\s+.+$")
HEADER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
MAX_PASSAGE = 5000
SKIP_NAMES = {"README.md", "COBERTURA.md", "PROGRESSO.md"}


def split_long(label, text, max_size=MAX_PASSAGE):
    """Divide trechos muito longos preservando o artigo original no rótulo."""
    if len(text) <= max_size:
        return [(label, text)]
    paragraphs = re.split(r"\n\s*\n", text)
    parts = []
    current = ""
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        # Fragmenta parágrafos longos, sem descartar qualquer texto.
        pieces = [paragraph[i:i + max_size] for i in range(0, len(paragraph), max_size)]
        for piece in pieces:
            if current and len(current) + len(piece) + 2 > max_size:
                parts.append(current.strip())
                current = ""
            current += ("\n\n" if current else "") + piece
    if current:
        parts.append(current.strip())
    return [
        (label if i == 0 else f"{label} (parte {i + 1})", part)
        for i, part in enumerate(parts)
    ]


def split_passages(body):
    """Tenta separar por artigo; recorre a títulos Markdown ou texto corrido."""
    matches = list(ARTICLE.finditer(body))
    if not matches:
        matches = list(HEADING.finditer(body))
    if not matches:
        return split_long("Texto", body.strip()) if body.strip() else []

    passages = []
    intro = body[:matches[0].start()].strip()
    if intro:
        passages.extend(split_long("Introdução", intro))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        text = body[match.start():end].strip()
        label = match.group(1) if match.re is ARTICLE else match.group(0).lstrip("# ").strip()
        passages.extend(split_long(label, text))
    return passages


def parse_document(content, relative_path):
    """Suporta YAML do acervo e a Constituição, que não tem frontmatter."""
    header = HEADER.match(content)
    metadata = yaml.safe_load(header.group(1)) if header else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    body = content[header.end():] if header else content

    path_parts = Path(relative_path).parts
    root = path_parts[0] if path_parts else ""
    sphere = {
        "federal": "federal",
        "estaduais": "estadual",
        "municipais": "municipal",
        "reguladores": "regulador",
        "jurisprudencia": "jurisprudencia",
        "tratados": "tratado",
    }.get(root, "federal")
    uf = metadata.get("uf")
    if not uf and root in ("estaduais", "municipais") and len(path_parts) > 1:
        uf = path_parts[1]

    title_match = re.search(r"(?m)^#\s+(.+)$", body)
    title = str(metadata.get("titulo") or (
        title_match.group(1).strip() if title_match else Path(relative_path).stem
    ))
    source = str(metadata.get("fonte") or "")
    if not source and Path(relative_path).name == "constituicao.md":
        found = re.search(r"\[texto compilado do Planalto\]\((https?://[^)]+)\)", body)
        if found:
            source = found.group(1)
    return {
        "title": title,
        "sphere": sphere,
        "uf": str(uf) if uf else None,
        "law_type": str(metadata.get("tipo") or (
            "Constituição Federal" if Path(relative_path).name == "constituicao.md" else ""
        )),
        "number": str(metadata.get("numero") or ""),
        "law_date": str(metadata.get("data") or ""),
        "status": str(metadata.get("situacao") or ""),
        "text_version": str(metadata.get("versao_texto") or ""),
        "source_url": source,
        "passages": split_passages(body),
    }


def encoder():
    if os.getenv("EMBEDDINGS_ENABLED", "0") != "1":
        return None
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Para ativar embeddings, instale app/requirements-embeddings.txt"
        ) from exc
    model = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    return SentenceTransformer(model)


def index_file(conn, path, data_root, model=None, force=False):
    relative = path.resolve().relative_to(data_root.resolve()).as_posix()
    raw = path.read_text(encoding="utf-8-sig")
    checksum = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    db_path = f"dados/{relative}"
    row = conn.execute("SELECT checksum FROM laws WHERE path = %s", (db_path,)).fetchone()
    if row and row[0] == checksum and not force:
        return "unchanged", 0

    parsed = parse_document(raw, relative)
    if not parsed["passages"]:
        return "empty", 0

    law_id = conn.execute("""
        INSERT INTO laws (
            path, title, sphere, uf, law_type, number, law_date,
            status, text_version, source_url, checksum
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (path) DO UPDATE SET
            title = EXCLUDED.title, sphere = EXCLUDED.sphere,
            uf = EXCLUDED.uf, law_type = EXCLUDED.law_type,
            number = EXCLUDED.number, law_date = EXCLUDED.law_date,
            status = EXCLUDED.status, text_version = EXCLUDED.text_version,
            source_url = EXCLUDED.source_url, checksum = EXCLUDED.checksum,
            indexed_at = now()
        RETURNING id
    """, (
        db_path, parsed["title"], parsed["sphere"], parsed["uf"],
        parsed["law_type"], parsed["number"], parsed["law_date"],
        parsed["status"], parsed["text_version"], parsed["source_url"],
        checksum,
    )).fetchone()[0]
    conn.execute("DELETE FROM passages WHERE law_id = %s", (law_id,))

    passages = parsed["passages"]
    embeddings = model.encode([p[1] for p in passages], show_progress_bar=False) if model else None
    rows = []
    for i, (label, content) in enumerate(passages):
        vector = None
        if embeddings is not None:
            vector = "[" + ",".join(f"{float(x):.8f}" for x in embeddings[i]) + "]"
        rows.append((law_id, i, label, content, vector))
    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO passages (law_id, ordinal, label, content, embedding)
            VALUES (%s, %s, %s, %s, %s::vector)
        """, rows)
    return "indexed", len(rows)


def eligible_files(target):
    if target.is_file():
        yield target
    else:
        for path in target.rglob("*.md"):
            if path.name not in SKIP_NAMES and "scripts" not in path.parts:
                yield path


def main():
    parser = argparse.ArgumentParser(description="Indexa legislação Markdown em PostgreSQL")
    parser.add_argument("--path", default="dados/constituicao.md",
                        help="Arquivo ou diretório dentro de dados/")
    parser.add_argument("--limit", type=int, default=50,
                        help="Máximo de arquivos por execução (padrão: 50)")
    parser.add_argument("--force", action="store_true",
                        help="Reindexar mesmo quando o SHA-256 não mudou")
    args = parser.parse_args()

    data_root = Path(os.getenv("DATA_DIR", "dados")).resolve()
    target = Path(args.path).resolve()
    if not target.is_relative_to(data_root) or not target.exists():
        parser.error("--path deve existir dentro de dados/")
    if args.limit < 1:
        parser.error("--limit deve ser maior que zero")

    model = encoder()
    totals = {"indexed": 0, "unchanged": 0, "empty": 0, "passages": 0}
    with connection() as conn:
        init_db(conn)
        conn.commit()
        for i, path in enumerate(eligible_files(target)):
            if i >= args.limit:
                break
            try:
                result, count = index_file(conn, path, data_root, model, args.force)
                conn.commit()
                totals[result] += 1
                totals["passages"] += count
                print(f"{result:9s} {path} ({count} trechos)")
            except Exception:
                conn.rollback()
                raise
    print("Resumo:", totals)


if __name__ == "__main__":
    main()

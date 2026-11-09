"""Importa lotes de códigos federais diretamente das fontes oficiais.

Execução isolada do servidor web:
  python -m app.official_import --dry-run
  python -m app.official_import --codes penal,civil,clt,cdc
  python -m app.official_import --codes cdc --force

Não depende do clone completo de dados/ nem executa na inicialização da API.
"""
import argparse
from html.parser import HTMLParser
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError

from .db import connection, init_db
from .ingest import index_file, split_passages

MAX_DOWNLOAD = 18 * 1024 * 1024
ALLOWED_HOSTS = {"www.planalto.gov.br", "planalto.gov.br", "presidencia.gov.br"}
USER_AGENT = "Mozilla/5.0 (compatible; LeisRAG/1.0; legal-indexer)"

# URLs de textos compilados e verificados como fontes oficiais.
# Não presumir que a data de importação corresponda à consolidação legal.
SOURCES = {
    "penal": {
        "title": "Código Penal",
        "law_type": "Decreto-Lei",
        "number": "2.848/1940",
        "url": "https://presidencia.gov.br/ccivil_03/decreto-lei/del2848compilado.htm",
        "minimum_articles": 120,
    },
    "civil": {
        "title": "Código Civil",
        "law_type": "Lei Ordinária",
        "number": "10.406/2002",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm",
        "minimum_articles": 200,
    },
    "clt": {
        "title": "Consolidação das Leis do Trabalho (CLT)",
        "law_type": "Decreto-Lei",
        "number": "5.452/1943",
        "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452compilado.htm",
        "minimum_articles": 100,
    },
    "cdc": {
        "title": "Código de Defesa do Consumidor (CDC)",
        "law_type": "Lei Ordinária",
        "number": "8.078/1990",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm",
        "minimum_articles": 55,
    },
}


class Paragraphs(HTMLParser):
    """Lê parágrafos em HTML legado sem executar scripts da fonte."""
    BLOCKS = {"p", "h1", "h2", "h3", "h4", "pre", "li"}
    IGNORE = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.current = []
        self.paragraphs = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.IGNORE:
            self.ignored += 1
        if self.ignored:
            return
        if tag in self.BLOCKS:
            if self.depth == 0:
                self.current = []
            self.depth += 1
        if tag == "br" and self.depth:
            self.current.append(" ")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.IGNORE:
            self.ignored = max(0, self.ignored - 1)
            return
        if self.ignored:
            return
        if tag in self.BLOCKS and self.depth:
            self.depth -= 1
            if not self.depth:
                text = re.sub(r"\s+", " ", "".join(self.current)).strip()
                if text:
                    self.paragraphs.append(text)
                self.current = []

    def handle_data(self, data):
        if self.depth and not self.ignored:
            self.current.append(data)


def _is_official(url):
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS


def _decode(raw, headers):
    declared = re.search(
        rb"(?i)<meta[^>]+charset\s*=\s*[\"']?\s*([a-z0-9_-]+)", raw[:16384]
    )
    charset = declared.group(1).decode("ascii", "ignore") if declared else None
    candidates = [charset, headers.get_content_charset(), "utf-8", "cp1252"]
    for encoding in candidates:
        if not encoding:
            continue
        try:
            decoded = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        if "\ufffd" not in decoded:
            return decoded
    return raw.decode("cp1252", errors="replace")


def download_official(url):
    """Tenta os dois portais oficiais, sem aceitar fontes não governamentais."""
    if not _is_official(url):
        raise ValueError("Fonte fora dos domínios oficiais permitidos")
    variants = [url]
    if url.startswith("https://presidencia.gov.br/"):
        variants.append(url.replace("https://presidencia.gov.br/",
                                    "https://www.planalto.gov.br/", 1))
    elif url.startswith("https://www.planalto.gov.br/"):
        variants.append(url.replace("https://www.planalto.gov.br/",
                                    "https://presidencia.gov.br/", 1))
    last_error = None
    for address in variants:
        for attempt in range(2):
            request = Request(address, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml;q=0.9",
                "Accept-Language": "pt-BR,pt;q=0.9",
                "Connection": "close",
            })
            try:
                with urlopen(request, timeout=20) as response:
                    if not _is_official(response.geturl()):
                        raise ValueError("Redirecionamento para domínio não autorizado")
                    raw = response.read(MAX_DOWNLOAD + 1)
                    if len(raw) > MAX_DOWNLOAD:
                        raise ValueError("Documento ultrapassa o limite permitido")
                    if len(raw) < 4000:
                        raise ValueError("Resposta HTML muito pequena para ser legislação")
                    return _decode(raw, response.headers)
            except (URLError, OSError, TimeoutError) as exc:
                last_error = exc
                print(f"Falha de conexão oficial ({urlparse(address).hostname}, "
                      f"tentativa {attempt + 1}/2): {type(exc).__name__}", flush=True)
    raise ConnectionError(
        "Nenhum endereço oficial respondeu após tentativas controladas"
    ) from last_error


def extract_articles(html):
    parser = Paragraphs()
    parser.feed(html)
    # O Planalto costuma colocar um artigo em cada <p>. Não juntar linhas
    # menores sem necessidade, pois o separador alimenta split_passages().
    paragraphs = []
    for item in parser.paragraphs:
        item = re.sub(r"(?i)^Art\.\s*(\d+)\s*[oº°]\b", r"Art. \1º", item)
        paragraphs.append(item)
    return "\n\n".join(paragraphs)


def document(spec, text):
    content = (
        "---\n"
        f"titulo: {spec['title']!r}\n"
        f"tipo: {spec['law_type']!r}\n"
        f"numero: {spec['number']!r}\n"
        f"fonte: {spec['url']!r}\n"
        "situacao: 'Vigência deve ser conferida no texto oficial'\n"
        "versao_texto: 'Transcrição do texto compilado; confira a vigência'\n"
        "---\n"
        f"# {spec['title']}\n\n{text}\n"
    )
    return content


def prepare(code, spec):
    html = download_official(spec["url"])
    extracted = extract_articles(html)
    articles = split_passages(extracted)
    number = sum(label.lower().startswith("art") for label, _ in articles)
    if number < spec["minimum_articles"]:
        raise ValueError(
            f"{code}: documento possivelmente incompleto "
            f"({number} artigos, mínimo {spec['minimum_articles']})"
        )
    if len(extracted) < 10000:
        raise ValueError(f"{code}: pouco texto extraído; importação cancelada")
    return extracted, number


def run(codes, *, dry_run=False, force=False):
    results = []
    if not dry_run:
        with connection() as conn:
            init_db(conn)
    for code in codes:
        if code not in SOURCES:
            raise ValueError(f"Fonte desconhecida: {code}")
        spec = SOURCES[code]
        try:
            text, number = prepare(code, spec)
            if dry_run:
                results.append({"code": code, "status": "validated",
                                "articles": number, "chars": len(text)})
                print(f"VALIDADO {code}: {number} artigos, {len(text)} caracteres")
                continue
            with tempfile.TemporaryDirectory(prefix="leis-rag-import-") as folder:
                data_root = Path(folder) / "dados"
                target = data_root / "federal" / "codigos" / f"{code}.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(document(spec, text), encoding="utf-8")
                with connection() as conn:
                    status, passages = index_file(
                        conn, target, data_root, model=None, force=force
                    )
            results.append({"code": code, "status": status,
                            "articles": number, "passages": passages})
            print(f"{status.upper()} {code}: {number} artigos; {passages} trechos")
        except Exception as exc:
            # Uma fonte fora do ar não impede a importação das demais.
            results.append({"code": code, "status": "failed",
                            "error": type(exc).__name__})
            print(f"FALHOU {code}: {type(exc).__name__}: {exc}", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Importa lotes controlados de legislação federal oficial"
    )
    parser.add_argument("--codes", default="penal,civil,clt,cdc",
                        help="Lista de códigos: penal,civil,clt,cdc")
    parser.add_argument("--dry-run", action="store_true",
                        help="Baixa e verifica, sem gravar no banco")
    parser.add_argument("--force", action="store_true",
                        help="Reindexa mesmo se o documento não mudou")
    args = parser.parse_args()
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    if not codes or len(codes) != len(set(codes)):
        parser.error("Informe códigos válidos sem repetições")
    results = run(codes, dry_run=args.dry_run, force=args.force)
    if any(item['status'] == 'failed' for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

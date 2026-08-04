"""
scraper.py — Radar de Vagas · Logística Aérea SP
Coleta vagas de logística em companhias aéreas de São Paulo.

Fonte ativa atual:
  - Vagas.com (busca pública)

Uso:
  python scraper.py
  python scraper.py --dry-run          # não salva jobs.json
  python scraper.py --notify           # envia alerta se tiver vagas novas
  python scraper.py --terms logistica,handling --pages 3
"""

import json
import os
import sys
import time
import smtplib
import hashlib
import argparse
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Configuração ──────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html",
}

DEFAULT_TERMS = [
    # termos ampliados para cobrir logística em SP (cidade + interior) e funções relevantes
    "logistica",
    "logistica-sao-paulo",
    "logistica-sp",
    "supply-chain",
    "operacoes-logisticas",
    "analista-logistica",
    "auxiliar-logistica",
    "coordenador-logistica",
    "motorista-carga",
    "carga-aerea",
    "ground-handling",
    "almoxarife",
    "suprimentos",
    "compras",
    "estoque",
    "expedicao",
]

SOURCE_QUERY_GROUPS = {
    "Vagas.com · Logística": [
        "logistica",
        "logistica-sao-paulo",
        "logistica-sp",
        "analista-logistica",
        "auxiliar-logistica",
        "coordenador-logistica",
    ],
    "Vagas.com · Carga e Operações": [
        "carga-aerea",
        "ground-handling",
        "supply-chain",
        "operacoes-logisticas",
        "almoxarife",
        "suprimentos",
        "compras",
        "estoque",
        "expedicao",
    ],
}
DEFAULT_PAGES = 3
SOURCE_NAME = "Vagas.com"
DEFAULT_LOCATION = "Brasil"

import re

OUTPUT_FILE = Path(__file__).parent / "jobs.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def today():
    return datetime.now().strftime("%Y-%m-%d")


def stable_hash(value: str) -> str:
    """Gera um ID estável a partir de uma string para deduplicação entre execuções."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def airline_emoji(name: str) -> str:
    n = (name or "").lower()
    if "latam" in n or "tam" in n:  return "🔵"
    if "gol" in n:                   return "🟠"
    if "azul" in n:                  return "🔷"
    if "voepass" in n:               return "🟢"
    if "swissport" in n:             return "⚪"
    if "ogden" in n:                 return "🟤"
    if "dhl" in n:                   return "🟡"
    if "fedex" in n:                 return "🟣"
    if "ups" in n:                   return "🟫"
    if "infraero" in n:              return "🏛️"
    if "gru" in n:                   return "🏢"
    return "🏢"


def infer_area(title: str, company: str, card) -> str:
    text = " ".join([
        str(title or ""),
        str(company or ""),
        card.get_text(" ", strip=True) if card is not None else ""
    ]).lower()

    area_patterns = [
        (r"\blog[ií]stica\b", "Logística"),
        (r"\bprodu[cç][ãa]o\b|\bprodu[cç][ao]\b|\balmoxarifado\b|\bestoque\b|\bsuprimentos\b|\bcompras\b", "Produção / Compras"),
        (r"\bimporta[cç][ãa]o\b|\bexporta[cç][ãa]o\b|\bcom[eé]rcio\b|\btrading\b", "Importação / Exportação"),
        (r"\bopera[cç][ãa]o\b|\bop[eê]ra[cç][ao]\b|\bhandling\b|\baeroporto\b|\bsolo\b", "Operações"),
        (r"\brh\b|\brecursos humanos\b|\brecrut[aá]mento\b|\btalentos\b|\bpessoas\b", "RH"),
        (r"\bfinanc(eiro|as)\b|\bcont[aá]bil\b|\btesouraria\b|\bcontroladoria\b", "Financeiro"),
        (r"\badministrativo\b|\badministracao\b|\badministra[cç][ãa]o\b|\bassistente\b|\brespons[aá]vel\b", "Administração"),
        (r"\best[aá]gio\b|\baprendiz\b", "Estágio"),
        (r"\btransportes?\b|\btransporte\b|\btruck\b|\bmotorista\b|\blog[ií]stica\b", "Transporte"),
    ]

    for pattern, area in area_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return area
    return "Logística"


def parse_job_location(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return DEFAULT_LOCATION

    m = re.search(r"([A-Za-zÀ-ÿ\-\.\s]+(?:,|/|-)\s*[A-Z]{2})", text)
    if m:
        return m.group(1).strip()

    m = re.search(r"([A-Za-zÀ-ÿ\-\.\s]+,\s*SP)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return DEFAULT_LOCATION


def fetch_infojobs(terms: list = None, pages: int = DEFAULT_PAGES, session=None, source_name: str = "InfoJobs") -> list[dict]:
    if terms is None:
        terms = DEFAULT_TERMS
    session = session or requests.Session()
    results = []
    headers = HEADERS.copy()
    headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    for term in terms:
        quoted = requests.utils.quote(term)
        for page in range(1, pages + 1):
            url = f"https://www.infojobs.com.br/empregos-em-sao-paulo.aspx?keywords={quoted}&page={page}"
            try:
                r = session.get(url, headers=headers, timeout=20)
                if r.status_code != 200:
                    print(f"  [WARN] {source_name} página {page} retornou {r.status_code}")
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select('div[id^="vacancy"][data-href]')
                if not cards:
                    break

                for card in cards:
                    href = card.get("data-href", "").strip()
                    if not href:
                        continue
                    full_url = href if href.startswith("http") else f"https://www.infojobs.com.br{href}"
                    title_el = card.select_one("h2.h3 a") or card.select_one("h2.h3") or card.select_one("h2")
                    title = title_el.get_text(" ", strip=True) if title_el else "Vaga InfoJobs"
                    company_el = card.select_one("a.text-body.text-decoration-none") or card.select_one("a[href*='/empresa-']")
                    company = company_el.get_text(" ", strip=True) if company_el else "Empresa"
                    location_el = card.select_one("span.text-body-small") or card.select_one("span.text-muted")
                    location = location_el.get_text(" ", strip=True) if location_el else parse_job_location(card.get_text(" ", strip=True))
                    job_area = infer_area(title, company, card)

                    results.append({
                        "id": f"infojobs_{stable_hash(full_url)}",
                        "title": title,
                        "company": company,
                        "emoji": airline_emoji(company),
                        "location": location or DEFAULT_LOCATION,
                        "type": "CLT",
                        "area": job_area,
                        "date_posted": today(),
                        "url": full_url,
                        "source": source_name,
                    })
                time.sleep(0.4)
            except Exception as e:
                print(f"  [WARN] {source_name} ({term}, página {page}): {e}")
                continue

    print(f"  ✓ Total de vagas encontradas no {source_name}: {len(results)}")
    return results


def fetch_linkedin(terms: list = None, pages: int = DEFAULT_PAGES, session=None, source_name: str = "LinkedIn") -> list[dict]:
    if terms is None:
        terms = DEFAULT_TERMS
    session = session or requests.Session()
    results = []
    headers = HEADERS.copy()
    headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    location = requests.utils.quote("São Paulo, BR")

    for term in terms:
        quoted = requests.utils.quote(term)
        for page in range(0, pages):
            url = f"https://www.linkedin.com/jobs/search?keywords={quoted}&location={location}&pageNum={page}"
            try:
                r = session.get(url, headers=headers, timeout=20)
                if r.status_code != 200:
                    print(f"  [WARN] {source_name} página {page} retornou {r.status_code}")
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select("div.base-card")
                if not cards:
                    break

                for card in cards:
                    title_el = card.select_one("h3")
                    title = title_el.get_text(" ", strip=True) if title_el else "Vaga LinkedIn"
                    company_el = card.select_one("h4")
                    company = company_el.get_text(" ", strip=True) if company_el else "Empresa"
                    location_el = card.select_one("span.job-card-container__metadata-item") or card.select_one("span.job-search-card__location")
                    location = location_el.get_text(" ", strip=True) if location_el else parse_job_location(card.get_text(" ", strip=True))
                    link_el = card.select_one("a[href]")
                    href = link_el.get("href", "") if link_el else ""
                    full_url = href if href.startswith("http") else f"https://www.linkedin.com{href}"
                    job_area = infer_area(title, company, card)

                    results.append({
                        "id": f"linkedin_{stable_hash(full_url)}",
                        "title": title,
                        "company": company,
                        "emoji": airline_emoji(company),
                        "location": location or DEFAULT_LOCATION,
                        "type": "CLT",
                        "area": job_area,
                        "date_posted": today(),
                        "url": full_url,
                        "source": source_name,
                    })
                time.sleep(0.4)
            except Exception as e:
                print(f"  [WARN] {source_name} ({term}, página {page}): {e}")
                continue

    print(f"  ✓ Total de vagas encontradas no {source_name}: {len(results)}")
    return results


def fetch_indeed(terms: list = None, pages: int = DEFAULT_PAGES, session=None, source_name: str = "Indeed") -> list[dict]:
    if terms is None:
        terms = DEFAULT_TERMS
    session = session or requests.Session()
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
    }

    for term in terms:
        quoted = requests.utils.quote(term)
        for page in range(0, pages):
            start = page * 10
            url = f"https://br.indeed.com/jobs?q={quoted}&l=S%C3%A3o+Paulo%2C+SP&start={start}"
            try:
                r = session.get(url, headers=headers, timeout=20)
                if r.status_code == 403:
                    print(f"  [WARN] {source_name} bloqueado por 403 no page {page}, pulando Indeed.")
                    break
                if r.status_code != 200:
                    print(f"  [WARN] {source_name} página {page} retornou {r.status_code}")
                    break

                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select("div.job_seen_beacon") or soup.select("a.tapItem")
                if not cards:
                    break

                for card in cards:
                    title_el = card.select_one("h2 span") or card.select_one("h2")
                    title = title_el.get_text(" ", strip=True) if title_el else "Vaga Indeed"
                    company_el = card.select_one("span.companyName") or card.select_one("span.company")
                    company = company_el.get_text(" ", strip=True) if company_el else "Empresa"
                    location_el = card.select_one("div.companyLocation") or card.select_one("div.recJobLoc")
                    location = location_el.get_text(" ", strip=True) if location_el else parse_job_location(card.get_text(" ", strip=True))
                    link_el = card.select_one("a[href]")
                    href = link_el.get("href", "") if link_el else ""
                    full_url = href if href.startswith("http") else (f"https://br.indeed.com{href}" if href else "")
                    if not full_url:
                        continue
                    job_area = infer_area(title, company, card)

                    results.append({
                        "id": f"indeed_{stable_hash(full_url)}",
                        "title": title,
                        "company": company,
                        "emoji": airline_emoji(company),
                        "location": location or DEFAULT_LOCATION,
                        "type": "CLT",
                        "area": job_area,
                        "date_posted": today(),
                        "url": full_url,
                        "source": source_name,
                    })
                time.sleep(0.4)
            except Exception as e:
                print(f"  [WARN] {source_name} ({term}, página {page}): {e}")
                break

    print(f"  ✓ Total de vagas encontradas no {source_name}: {len(results)}")
    return results


def load_external_sources(sdir: Path | None = None) -> list:
    """Carrega arquivos JSON de fontes adicionais a partir da pasta `sources/`.
    Cada arquivo JSON pode ser um objeto com chave `jobs` (lista) ou uma lista direta de jobs.
    Jobs são normalizados para o mesmo esquema usado internamente.
    """
    results = []
    try:
        sdir = sdir or (Path(__file__).parent / "sources")
        if not sdir.exists() or not sdir.is_dir():
            return results
        for f in sorted(sdir.glob("*.json")):
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                jobs = raw.get("jobs") if isinstance(raw, dict) and raw.get("jobs") else (raw if isinstance(raw, list) else [])
                for j in jobs:
                    url = j.get("url", "")
                    title = j.get("title") or j.get("cargo") or j.get("position") or ""
                    company = j.get("company") or j.get("empresa") or "Empresa"
                    job_id = j.get("id") or f"ext_{stable_hash(url or title)}"
                    src = j.get("source") or f"external:{f.stem}"
                    results.append({
                        "id": job_id,
                        "title": title.strip(),
                        "company": company.strip(),
                        "emoji": airline_emoji(company),
                        "location": j.get("location") or j.get("local") or DEFAULT_LOCATION,
                        "type": j.get("type") or "CLT",
                        "area": j.get("area") or "Logística",
                        "date_posted": j.get("date_posted") or today(),
                        "url": url,
                        "source": src,
                    })
            except Exception as e:
                print(f"  [WARN] loading external source {f.name}: {e}")
        if results:
            print(f"  ✓ Carregadas {len(results)} vagas de fontes externas ({sdir})")
    except Exception:
        pass
    return results


# ── Vagas.com scraper ─────────────────────────────────────────────────────────

def fetch_vagas_com(terms: list = None, pages: int = DEFAULT_PAGES, session=None, source_name: str = SOURCE_NAME) -> list[dict]:
    """
    Busca vagas no Vagas.com com múltiplos termos e páginas.
    """
    if terms is None:
        terms = DEFAULT_TERMS

    if session is None:
        session = requests.Session()

    results = []

    for term in terms:
        for page in range(1, pages + 1):
            url = f"https://www.vagas.com.br/vagas-de-{term}-em-sao-paulo-sp?pagina={page}"

            try:
                r = session.get(url, headers=HEADERS, timeout=15)
                if r.status_code != 200:
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select("li.vaga")
                if not cards:
                    break

                for card in cards:
                    title_link = card.select_one("h2.cargo a")
                    if not title_link:
                        continue

                    title = title_link.get_text(" ", strip=True)
                    href = title_link.get("href", "")
                    company_el = card.select_one("span.emprVaga")
                    company = company_el.get_text(" ", strip=True) if company_el else "Empresa"

                    # tenta extrair localidade do card; usa algumas classes comuns e, como fallback,
                    # procura por padrões "Cidade, UF" no texto do card
                    location = None
                    loc_el = card.select_one(
                        "span.local, span.localVaga, span.localidade, span.vaga-localidade, p.local, div.local, span.vaga-local"
                    )
                    if loc_el:
                        location = loc_el.get_text(" ", strip=True)
                    else:
                        card_text = card.get_text(" ", strip=True)
                        # captura formatos comuns: "Cidade, UF" ou "Cidade / UF" ou "Cidade - UF"
                        m = re.search(r"([A-Za-zÀ-ÿ\-\.\s]+(?:,|/|-)\s*[A-Z]{2})", card_text)
                        if m:
                            location = m.group(1).strip()
                    if not location:
                        location = DEFAULT_LOCATION

                    full_url = href if href.startswith("http") else f"https://www.vagas.com.br{href}"
                    vaga_id = f"vagas_{stable_hash(full_url)}"

                    job_area = infer_area(title, company, card)

                    results.append({
                        "id":          vaga_id,
                        "title":       title,
                        "company":     company,
                        "emoji":       airline_emoji(company),
                        "location":    location,
                        "type":        "CLT",
                        "area":        job_area,
                        "date_posted": today(),
                        "url":         full_url,
                        "source":      source_name,
                    })

                time.sleep(0.5)

            except Exception as e:
                print(f"  [WARN] {source_name} ({term}, página {page}): {e}")
                continue

    print(f"  ✓ Total de vagas encontradas no {source_name}: {len(results)}")
    return results


# ── Consolidação ──────────────────────────────────────────────────────────────

def collect_all_jobs(terms: list = None, pages: int = DEFAULT_PAGES) -> list[dict]:
    seen = set()
    all_jobs = []

    print(f"🌐 Buscando nas fontes configuradas…")
    with requests.Session() as session:
        vagas_jobs = []
        source_map = [
            ("Vagas.com · Logística", fetch_vagas_com, SOURCE_QUERY_GROUPS["Vagas.com · Logística"]),
            ("Vagas.com · Carga e Operações", fetch_vagas_com, SOURCE_QUERY_GROUPS["Vagas.com · Carga e Operações"]),
            ("InfoJobs", fetch_infojobs, DEFAULT_TERMS),
            ("LinkedIn", fetch_linkedin, DEFAULT_TERMS),
            ("Indeed", fetch_indeed, DEFAULT_TERMS),
        ]

        for source_label, fetcher, source_terms in source_map:
            if terms is None:
                query_terms = source_terms
            else:
                query_terms = terms
            print(f"  → fonte: {source_label} ({len(query_terms)} termos)")
            vagas_jobs.extend(fetcher(terms=query_terms, pages=pages, session=session, source_name=source_label))

    # carregar fontes externas da pasta `sources/` (se houver)
    ext_jobs = load_external_sources()
    if ext_jobs:
        vagas_jobs.extend(ext_jobs)

    for j in vagas_jobs:
        if j["id"] not in seen:
            seen.add(j["id"])
            all_jobs.append(j)

    all_jobs.sort(key=lambda j: j.get("date_posted", ""), reverse=True)

    print(f"\n✅ Total coletado: {len(all_jobs)} vagas")
    return all_jobs


# ── Diff (vagas novas vs cache) ───────────────────────────────────────────────

def load_previous_ids() -> set:
    if OUTPUT_FILE.exists():
        try:
            data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            return {j["id"] for j in data.get("jobs", [])}
        except Exception:
            pass
    return set()


def find_new_jobs(jobs: list[dict], previous_ids: set) -> list[dict]:
    return [j for j in jobs if j["id"] not in previous_ids]


def mark_new_jobs(jobs: list[dict], previous_ids: set) -> list[dict]:
    new_jobs = []
    for job in jobs:
        job["is_new"] = job["id"] not in previous_ids
        if job["is_new"]:
            new_jobs.append(job)
    return new_jobs


# ── Alertas ───────────────────────────────────────────────────────────────────

def send_email_alert(new_jobs: list[dict]):
    """Envia e-mail via SMTP (configure SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_EMAIL)."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    alert_to  = os.getenv("ALERT_EMAIL", "")

    if not all([smtp_user, smtp_pass, alert_to]):
        print("  [SKIP] E-mail não configurado (SMTP_USER / SMTP_PASS / ALERT_EMAIL).")
        return

    subject = f"✈️ {len(new_jobs)} nova(s) vaga(s) de Logística Aérea em SP!"
    body_lines = [
        f"<h2>✈️ {len(new_jobs)} nova(s) vaga(s) encontrada(s)!</h2>",
        "<p>Olá! O <strong>Radar de Vagas</strong> encontrou oportunidades novas para você:</p>",
        "<ul>",
    ]
    for j in new_jobs[:10]:
        body_lines.append(
            f'<li><strong>{j["title"]}</strong> — {j["company"]}<br/>'
            f'📍 {j["location"]} | 💼 {j["type"]}<br/>'
            f'<a href="{j["url"]}">Ver vaga →</a></li>'
        )
    body_lines += ["</ul>", '<p>🔗 <a href="https://SEU_USUARIO.github.io/vagas-logistica-aero/">Abrir Radar de Vagas</a></p>']
    body = "\n".join(body_lines)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_user
    msg["To"]      = alert_to
    msg.attach(MIMEText(body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, alert_to, msg.as_string())
        print(f"  ✉️  E-mail enviado para {alert_to}")
    except Exception as e:
        print(f"  [ERROR] Falha ao enviar e-mail: {e}")


def send_wpp_alert(new_jobs: list[dict]):
    """Envia alerta via WhatsApp usando CallMeBot (configure ALERT_WPP e CALLMEBOT_KEY)."""
    wpp    = os.getenv("ALERT_WPP", "").replace(" ", "").replace("-", "").replace("+", "")
    apikey = os.getenv("CALLMEBOT_KEY", "")

    if not wpp or not apikey:
        print("  [SKIP] WhatsApp não configurado (ALERT_WPP / CALLMEBOT_KEY).")
        return

    # Formata número brasileiro → internacional
    if wpp.startswith("0"):
        wpp = "55" + wpp[1:]
    elif not wpp.startswith("55"):
        wpp = "55" + wpp

    titles = "\n".join(f"• {j['title']} — {j['company']}" for j in new_jobs[:5])
    msg = f"✈️ {len(new_jobs)} nova(s) vaga(s) de Logística Aérea em SP!\n\n{titles}\n\nVeja mais: https://SEU_USUARIO.github.io/vagas-logistica-aero/"

    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={wpp}&text={requests.utils.quote(msg)}&apikey={apikey}"
    )
    try:
        r = requests.get(url, timeout=10)
        if r.ok:
            print(f"  📱 WhatsApp enviado para +{wpp[:6]}***")
        else:
            print(f"  [WARN] CallMeBot retornou: {r.status_code}")
    except Exception as e:
        print(f"  [ERROR] Falha WhatsApp: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Radar de Vagas — Logística Aérea SP")
    parser.add_argument("--dry-run",  action="store_true", help="Não salva jobs.json")
    parser.add_argument("--notify",   action="store_true", help="Envia alerta se tiver vagas novas")
    parser.add_argument("--pages",   type=int, default=DEFAULT_PAGES, help="Número de páginas por termo")
    parser.add_argument("--terms",   type=str, default=None, help="Termos separados por vírgula para buscar")
    args = parser.parse_args()

    terms = [t.strip() for t in args.terms.split(",") if t.strip()] if args.terms else None

    print("=" * 55)
    print(f"  ✈️  Radar de Vagas — {SOURCE_NAME} · São Paulo")
    print(f"  🕐  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 55)

    prev_ids = load_previous_ids()
    jobs     = collect_all_jobs(terms=terms, pages=args.pages)
    new_jobs = mark_new_jobs(jobs, prev_ids)

    print(f"\n🆕 Vagas novas desde a última execução: {len(new_jobs)}")
    for j in new_jobs[:5]:
        print(f"   → {j['title']} | {j['company']}")

    if not args.dry_run:
        payload = {
            "updated_at": now_iso(),
            "total":      len(jobs),
            "new_count":  len(new_jobs),
            "jobs":       jobs,
        }
        OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Salvo em {OUTPUT_FILE} ({len(jobs)} vagas)")

    if args.notify and new_jobs:
        print("\n📣 Enviando alertas…")
        send_email_alert(new_jobs)
        send_wpp_alert(new_jobs)

    print("\n✅ Concluído!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

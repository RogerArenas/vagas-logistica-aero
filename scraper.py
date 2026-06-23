"""
scraper.py — Radar de Vagas · Logística Aérea SP
Coleta vagas de logística em companhias aéreas de São Paulo.

Fontes:
  - Gupy API pública (principal)
  - Catho (busca pública)
  - Vagas.com (busca pública)

Uso:
  python scraper.py
  python scraper.py --dry-run          # não salva jobs.json
  python scraper.py --notify           # envia alerta se tiver vagas novas
"""

import json
import os
import re
import sys
import time
import smtplib
import argparse
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Configuração ──────────────────────────────────────────────────────────────

GUPY_API_BASE = "https://portal.api.gupy.io/api/v1/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html",
}

# Termos de busca para logística
SEARCH_TERMS = [
    "logistica",
    "logística operacional",
    "carga aérea",
    "operações aeroportuárias",
    "analista logistica",
    "coordenador logistica",
    "supervisor logistica",
    "operador logistica",
    "handling",
    "ground handling",
    "planejamento logistico",
]

# Slugs de empresas aéreas/aeroportuárias no Gupy
COMPANY_SLUGS = [
    "latam",
    "gol",
    "azul",
    "voepass",
    "swissport-brasil",
    "ogden-servicos",
    "infraero",
    "gru-airport",
    "dhl-express-brasil",
    "fedex-brasil",
    "ups-brasil",
]

# Palavras-chave para filtrar se a vaga é realmente de logística/cia. aérea
KEYWORDS_INCLUDE = [
    "logis", "carga", "aere", "aeroporto", "airport", "frete", "handling",
    "import", "export", "supply chain", "operaç", "despacho", "alfandeg",
    "aviaç", "ground", "ramp", "warehouse", "armazem", "armazém",
]

KEYWORDS_EXCLUDE = ["ux", "design gráfico", "advogad", "médic", "enfermeir"]

OUTPUT_FILE = Path(__file__).parent / "jobs.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def today():
    return datetime.now().strftime("%Y-%m-%d")


def is_in_sp(city: str, state: str) -> bool:
    city = (city or "").lower()
    state = (state or "").lower()
    return "paulo" in city or "guarulhos" in city or "campinas" in city \
           or "sp" in state or "são paulo" in state


def normalize_type(raw: str) -> str:
    r = (raw or "").lower()
    if any(x in r for x in ["effective", "clt", "full_time", "permanent"]):
        return "CLT"
    if any(x in r for x in ["pj", "autonomo", "freelan"]):
        return "PJ"
    if any(x in r for x in ["intern", "estagio", "estágio", "trainee"]):
        return "Estágio"
    if any(x in r for x in ["temp", "contract", "short"]):
        return "Temporário"
    return "CLT"


def is_relevant(title: str, company: str) -> bool:
    text = (title + " " + company).lower()
    if any(kw in text for kw in KEYWORDS_EXCLUDE):
        return False
    return True  # Se for de empresa aérea conhecida, aceita tudo


def is_new(date_str: str) -> bool:
    if not date_str:
        return False
    try:
        posted = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        diff = (datetime.now(timezone.utc) - posted).total_seconds() / 3600
        return diff < 48
    except Exception:
        return False


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


# ── Gupy API ──────────────────────────────────────────────────────────────────

def fetch_gupy_by_term(term: str, limit: int = 30) -> list[dict]:
    params = {
        "jobName": term,
        "cityName": "São Paulo",
        "limit": limit,
        "offset": 0,
    }
    try:
        r = requests.get(GUPY_API_BASE, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])
    except Exception as e:
        print(f"  [WARN] Gupy busca '{term}': {e}")
        return []


def fetch_gupy_by_company(slug: str, limit: int = 20) -> list[dict]:
    params = {"companySlug": slug, "limit": limit}
    try:
        r = requests.get(GUPY_API_BASE, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])
    except Exception as e:
        print(f"  [WARN] Gupy empresa '{slug}': {e}")
        return []


def normalize_gupy(j: dict) -> dict:
    company = j.get("careerPageName") or j.get("companyName") or "Empresa"
    slug = j.get("careerPageSlug", "")
    job_id = j.get("id", "")
    url = j.get("jobUrl") or f"https://{slug}.gupy.io/jobs/{job_id}"

    return {
        "id":          f"gupy_{job_id}",
        "title":       j.get("name", "Vaga sem título"),
        "company":     company,
        "emoji":       airline_emoji(company),
        "location":    ", ".join(filter(None, [j.get("cityName"), j.get("state")])) or "São Paulo, SP",
        "type":        normalize_type(j.get("type", "")),
        "area":        j.get("department") or "Logística",
        "date_posted": (j.get("publishedDate") or today()).split("T")[0],
        "url":         url,
        "source":      "Gupy",
        "is_new":      is_new(j.get("publishedDate", "")),
    }


# ── Catho scraper ─────────────────────────────────────────────────────────────

def fetch_catho(term: str = "logistica aeroporto", pages: int = 2) -> list[dict]:
    results = []
    for page in range(1, pages + 1):
        url = (
            f"https://www.catho.com.br/vagas/{term.replace(' ', '-')}/"
            f"sao-paulo/?q={requests.utils.quote(term)}&page={page}"
        )
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            cards = soup.select("[data-testid='job-card'], .job-list-item, article")
            for card in cards:
                title_el = card.select_one("h2, h3, .job-title, [data-testid='job-title']")
                company_el = card.select_one(".company-name, [data-testid='company-name']")
                loc_el = card.select_one(".job-location, [data-testid='job-location']")
                link_el = card.select_one("a[href]")

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Empresa"
                location = loc_el.get_text(strip=True) if loc_el else "São Paulo, SP"
                href = link_el["href"] if link_el else ""
                full_url = href if href.startswith("http") else f"https://www.catho.com.br{href}"

                results.append({
                    "id":          f"catho_{hash(full_url)}",
                    "title":       title,
                    "company":     company,
                    "emoji":       airline_emoji(company),
                    "location":    location,
                    "type":        "CLT",
                    "area":        "Logística",
                    "date_posted": today(),
                    "url":         full_url,
                    "source":      "Catho",
                    "is_new":      True,
                })
            time.sleep(1)
        except Exception as e:
            print(f"  [WARN] Catho página {page}: {e}")
    return results


# ── Vagas.com scraper ─────────────────────────────────────────────────────────

def fetch_vagas_com(term: str = "logistica aeroporto") -> list[dict]:
    url = f"https://www.vagas.com.br/vagas-de-{term.replace(' ', '-')}-em-sao-paulo-sp"
    results = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for card in soup.select(".job-shortdescription, li.vaga"):
            title_el = card.select_one("h2 a, .cargo a")
            company_el = card.select_one(".emprVaga, .employer")
            href = title_el["href"] if title_el and title_el.get("href") else ""
            if not title_el:
                continue

            full_url = href if href.startswith("http") else f"https://www.vagas.com.br{href}"
            company = company_el.get_text(strip=True) if company_el else "Empresa"

            results.append({
                "id":          f"vagas_{hash(full_url)}",
                "title":       title_el.get_text(strip=True),
                "company":     company,
                "emoji":       airline_emoji(company),
                "location":    "São Paulo, SP",
                "type":        "CLT",
                "area":        "Logística",
                "date_posted": today(),
                "url":         full_url,
                "source":      "Vagas.com",
                "is_new":      True,
            })
    except Exception as e:
        print(f"  [WARN] Vagas.com: {e}")
    return results


# ── Consolidação ──────────────────────────────────────────────────────────────

def collect_all_jobs() -> list[dict]:
    seen = set()
    all_jobs = []

    print("🔍 Buscando na Gupy por termos…")
    for term in SEARCH_TERMS:
        raw = fetch_gupy_by_term(term)
        for j in raw:
            jid = j.get("id")
            if jid and jid not in seen:
                normalized = normalize_gupy(j)
                if is_relevant(normalized["title"], normalized["company"]):
                    seen.add(jid)
                    all_jobs.append(normalized)
        time.sleep(0.4)

    print("✈️  Buscando em empresas aéreas específicas…")
    for slug in COMPANY_SLUGS:
        raw = fetch_gupy_by_company(slug)
        for j in raw:
            jid = j.get("id")
            if jid and jid not in seen:
                seen.add(jid)
                all_jobs.append(normalize_gupy(j))
        time.sleep(0.3)

    print("🌐 Buscando no Catho…")
    catho_jobs = fetch_catho("logistica aérea são paulo")
    for j in catho_jobs:
        if j["id"] not in seen:
            seen.add(j["id"])
            all_jobs.append(j)

    print("🌐 Buscando no Vagas.com…")
    vagas_jobs = fetch_vagas_com("logistica-aerea")
    for j in vagas_jobs:
        if j["id"] not in seen:
            seen.add(j["id"])
            all_jobs.append(j)

    # Ordena: novas primeiro, depois por data
    all_jobs.sort(key=lambda j: (not j.get("is_new"), j.get("date_posted", ""), j.get("company", "")), reverse=False)
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
    args = parser.parse_args()

    print("=" * 55)
    print("  ✈️  Radar de Vagas — Logística Aérea · São Paulo")
    print(f"  🕐  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 55)

    prev_ids = load_previous_ids()
    jobs     = collect_all_jobs()
    new_jobs = find_new_jobs(jobs, prev_ids)

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

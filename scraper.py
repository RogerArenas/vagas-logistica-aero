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
    "logistica-aerea",
    "logistica-sao-paulo",
    "ground-handling",
    "carga-aerea",
    "handling-aeroporto",
]
DEFAULT_PAGES = 3
SOURCE_NAME = "Vagas.com"
DEFAULT_LOCATION = "São Paulo, SP"

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


# ── Vagas.com scraper ─────────────────────────────────────────────────────────

def fetch_vagas_com(terms: list = None, pages: int = DEFAULT_PAGES, session=None) -> list[dict]:
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

                    title = title_link.get_text(strip=True)
                    href = title_link.get("href", "")
                    company_el = card.select_one("span.emprVaga")
                    company = company_el.get_text(strip=True) if company_el else "Empresa"
                    full_url = href if href.startswith("http") else f"https://www.vagas.com.br{href}"
                    vaga_id = f"vagas_{stable_hash(full_url)}"

                    results.append({
                        "id":          vaga_id,
                        "title":       title,
                        "company":     company,
                        "emoji":       airline_emoji(company),
                        "location":    DEFAULT_LOCATION,
                        "type":        "CLT",
                        "area":        "Logística",
                        "date_posted": today(),
                        "url":         full_url,
                        "source":      SOURCE_NAME,
                    })

                time.sleep(0.5)

            except Exception as e:
                print(f"  [WARN] {SOURCE_NAME} ({term}, página {page}): {e}")
                continue

    print(f"  ✓ Total de vagas encontradas no {SOURCE_NAME}: {len(results)}")
    return results


# ── Consolidação ──────────────────────────────────────────────────────────────

def collect_all_jobs(terms: list = None, pages: int = DEFAULT_PAGES) -> list[dict]:
    seen = set()
    all_jobs = []

    print(f"🌐 Buscando no {SOURCE_NAME} (múltiplos termos e páginas)…")
    with requests.Session() as session:
        vagas_jobs = fetch_vagas_com(terms=terms, pages=pages, session=session)

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

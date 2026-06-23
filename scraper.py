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
        # Tentar primeiro com o endpoint alternativo que está respondendo
        r = requests.get("https://portal.gupy.io/api/v1/jobs", params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        
        # Validar que a resposta é um JSON válido
        if r.text.strip():
            data = r.json()
            return data.get("data", [])
        else:
            print(f"  [WARN] Gupy busca '{term}': resposta vazia")
            return []
    except requests.exceptions.JSONDecodeError:
        print(f"  [WARN] Gupy busca '{term}': resposta JSON inválida")
        return []
    except Exception as e:
        print(f"  [WARN] Gupy busca '{term}': {e}")
        return []


def fetch_gupy_by_company(slug: str, limit: int = 20) -> list[dict]:
    params = {"companySlug": slug, "limit": limit}
    try:
        # Usar o endpoint alternativo que está respondendo
        r = requests.get("https://portal.gupy.io/api/v1/jobs", params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        
        # Validar que a resposta é um JSON válido
        if r.text.strip():
            data = r.json()
            return data.get("data", [])
        else:
            print(f"  [WARN] Gupy empresa '{slug}': resposta vazia")
            return []
    except requests.exceptions.JSONDecodeError:
        print(f"  [WARN] Gupy empresa '{slug}': resposta JSON inválida")
        return []
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

def fetch_catho(term: str = "logistica", pages: int = 1) -> list[dict]:
    """
    Busca vagas no Catho com URL simples.
    Nota: O Catho pode ter limitações de scraping, então reduzido para 1 página por padrão.
    """
    results = []
    for page in range(1, pages + 1):
        # URL simplificada - Catho costuma bloquear scrapers
        url = f"https://www.catho.com.br/vagas/{term}/"
        
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            
            # Se retornar 404, tenta com variações
            if r.status_code == 404:
                url = f"https://www.catho.com.br/vagas/{term}-sao-paulo/"
                r = requests.get(url, headers=HEADERS, timeout=15)
            
            if r.status_code != 200:
                print(f"  [WARN] Catho página {page}: HTTP {r.status_code}")
                continue
                
            soup = BeautifulSoup(r.text, "html.parser")

            # Tenta múltiplos seletores
            cards = soup.select("[data-testid='job-card'], .job-list-item, article, .resultado")
            
            if not cards:
                print(f"  [WARN] Catho: nenhuma vaga encontrada na página {page}")
                continue
                
            for card in cards:
                title_el = card.select_one("h2, h3, .job-title, [data-testid='job-title']")
                company_el = card.select_one(".company-name, [data-testid='company-name']")
                loc_el = card.select_one(".job-location, [data-testid='job-location']")
                link_el = card.select_one("a[href]")

                if not title_el or not link_el:
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Empresa"
                location = loc_el.get_text(strip=True) if loc_el else "São Paulo, SP"
                href = link_el["href"]
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

def fetch_vagas_com(terms: list = None, pages: int = 2) -> list[dict]:
    """
    Busca vagas no Vagas.com com múltiplos termos e páginas
    Versão melhorada com melhor cobertura
    """
    if terms is None:
        terms = [
            "logistica-aerea",
            "logistica",
            "handling",
            "ground-handling",
            "carga-aerea",
            "operacoes-aeroportuarias",
        ]
    
    results = []
    
    for term in terms:
        for page in range(1, pages + 1):
            url = f"https://www.vagas.com.br/vagas-de-{term}-em-sao-paulo-sp?pagina={page}"
            
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                
                if r.status_code != 200:
                    continue
                
                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select("li.vaga")
                
                if not cards:
                    # Se não encontrou vagas, para de paginar este termo
                    break
                
                for card in cards:
                    # Título e link
                    title_link = card.select_one("h2.cargo a")
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    href = title_link.get("href", "")
                    
                    # Empresa
                    company_el = card.select_one("span.emprVaga")
                    company = company_el.get_text(strip=True) if company_el else "Empresa"
                    
                    # Construir URL completa
                    full_url = href if href.startswith("http") else f"https://www.vagas.com.br{href}"
                    
                    # ID único para evitar duplicatas
                    vaga_id = f"vagas_{hash(full_url)}"

                    results.append({
                        "id":          vaga_id,
                        "title":       title,
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
                
                # Pequeno delay entre páginas
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  [WARN] Vagas.com ({term}, página {page}): {e}")
                continue
    
    print(f"  ✓ Total de vagas encontradas no Vagas.com: {len(results)}")
    return results


# ── Consolidação ──────────────────────────────────────────────────────────────

def collect_all_jobs() -> list[dict]:
    seen = set()
    all_jobs = []

    # ⚠️ Gupy e Catho desativadas (requerem Selenium/Playwright para conteúdo dinâmico)
    # Veja CORRECAO_GUPY_CATHO.md para detalhes

    print("🌐 Buscando no Vagas.com (múltiplos termos e páginas)…")
    vagas_jobs = fetch_vagas_com(
        terms=[
            "logistica-aerea",
            "logistica-sao-paulo",
            "ground-handling",
            "carga-aerea",
            "handling-aeroporto",
        ],
        pages=3  # Buscar até 3 páginas de cada termo
    )
    
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

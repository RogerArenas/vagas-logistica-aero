"""
Relatório detalhado de análise do scraper
Mostra exatamente o que está sendo encontrado em cada fonte
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

print("\n" + "="*70)
print("📊 RELATÓRIO: Análise detalhada de cada fonte")
print("="*70 + "\n")

# ── Teste Vagas.com ────────────────────────────────────────────

print("1️⃣  VAGAS.COM")
print("-" * 70)

url = "https://www.vagas.com.br/vagas-de-logistica-aerea-em-sao-paulo-sp"
print(f"URL: {url}\n")

try:
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"Status HTTP: {r.status_code} ✓\n")
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        vagas = soup.select("li.vaga")
        print(f"✓ Encontradas {len(vagas)} vagas\n")
        
        for i, vaga in enumerate(vagas, 1):
            title_link = vaga.select_one("h2.cargo a")
            company_el = vaga.select_one("span.emprVaga")
            
            if title_link:
                title = title_link.get_text(strip=True)
                href = title_link.get("href", "")
                company = company_el.get_text(strip=True) if company_el else "Empresa"
                
                print(f"  [{i}] {title}")
                print(f"       Empresa: {company}")
                print(f"       Link: {href}\n")
                
except Exception as e:
    print(f"❌ Erro: {e}\n")

# ── Teste Gupy ────────────────────────────────────────────────

print("\n2️⃣  GUPY API")
print("-" * 70)

test_cases = [
    ("Busca por termo", "https://portal.gupy.io/api/v1/jobs", {"jobName": "logistica", "cityName": "São Paulo", "limit": 5}),
    ("Busca empresa LATAM", "https://portal.gupy.io/api/v1/jobs", {"companySlug": "latam"}),
]

for desc, url, params in test_cases:
    print(f"\n{desc}:")
    print(f"URL: {url}")
    print(f"Params: {params}\n")
    
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        print(f"Status HTTP: {r.status_code}")
        print(f"Tamanho resposta: {len(r.text)} bytes")
        
        if r.status_code == 200:
            if r.text.strip().startswith('{'):
                try:
                    data = r.json()
                    jobs = data.get("data", [])
                    print(f"✓ JSON válido! Encontradas {len(jobs)} vagas")
                    
                    for i, job in enumerate(jobs[:3], 1):
                        print(f"  [{i}] {job.get('name', 'N/A')}")
                        print(f"       Empresa: {job.get('companyName', 'N/A')}")
                        print(f"       URL: {job.get('jobUrl', 'N/A')}")
                except json.JSONDecodeError as je:
                    print(f"❌ JSON inválido: {je}")
                    print(f"Primeiros 200 caracteres: {r.text[:200]}")
            else:
                print(f"❌ Resposta não é JSON")
                print(f"Primeiros 200 caracteres: {r.text[:200]}")
        else:
            print(f"❌ Status HTTP {r.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

# ── Teste Catho ────────────────────────────────────────────────

print("\n\n3️⃣  CATHO")
print("-" * 70)

url = "https://www.catho.com.br/vagas/logistica/"
print(f"URL: {url}\n")

try:
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"Status HTTP: {r.status_code}")
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Procurar por vagas
        cards = soup.select("[data-testid='job-card'], .job-list-item, article, .resultado")
        print(f"✓ Encontradas {len(cards)} vagas potenciais")
        
        if len(cards) > 0:
            for i, card in enumerate(cards[:3], 1):
                title_el = card.select_one("h2, h3, .job-title")
                print(f"  [{i}] {title_el.get_text(strip=True)[:50] if title_el else 'N/A'}")
    else:
        print(f"❌ Erro HTTP {r.status_code}")
        # Tentar alternativa
        url_alt = "https://www.catho.com.br/vagas/logistica-sao-paulo/"
        print(f"\nTentando alternativa: {url_alt}")
        r = requests.get(url_alt, headers=HEADERS, timeout=15)
        print(f"Status HTTP: {r.status_code}")
        
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n\n" + "="*70)
print(f"📅 Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("="*70 + "\n")

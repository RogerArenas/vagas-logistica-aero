"""
Versão melhorada das funções - Gupy e Catho corrigidas + LinkedIn alternativa
Teste antes de colocar no scraper.py
"""

import json
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ──────────────────────────────────────────────────────────────────────────────
# GUPY - Versão Melhorada (Scraping do HTML)
# ──────────────────────────────────────────────────────────────────────────────

def fetch_gupy_jobs_improved(search_term: str = "logistica", limit: int = 10) -> list[dict]:
    """
    Versão melhorada: Faz scraping direto da página HTML do Gupy
    Extrai dados do JSON embarcado na página
    """
    results = []
    
    # URL de busca do Gupy
    url = f"https://portal.gupy.io/jobs"
    
    try:
        params = {
            "search": search_term,
            "city": "São Paulo"
        }
        
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        print(f"  Gupy Status: {r.status_code}")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Procurar por scripts JSON na página
            scripts = soup.find_all("script", type="application/json")
            print(f"  Scripts JSON encontrados: {len(scripts)}")
            
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Estrutura pode estar em 'props' -> 'pageProps'
                    if "props" in data and "pageProps" in data["props"]:
                        jobs_data = data["props"]["pageProps"]
                        
                        # Procurar por jobs em diferentes estruturas
                        if "jobs" in jobs_data:
                            jobs = jobs_data["jobs"]
                        elif "data" in jobs_data:
                            jobs = jobs_data["data"]
                        else:
                            jobs = []
                        
                        print(f"  Jobs encontrados no JSON: {len(jobs)}")
                        
                        for job in jobs[:limit]:
                            results.append({
                                "id": f"gupy_{job.get('id', hash(str(job)))}",
                                "title": job.get("name", "Vaga sem título"),
                                "company": job.get("careerPageName") or job.get("companyName", "Empresa"),
                                "location": f"{job.get('city', 'São Paulo')}, {job.get('state', 'SP')}",
                                "url": job.get("jobUrl", f"https://portal.gupy.io/jobs/{job.get('id', '')}"),
                                "description": job.get("description", ""),
                            })
                except json.JSONDecodeError:
                    continue
            
            if results:
                print(f"  ✓ {len(results)} vagas extraídas com sucesso!")
            else:
                print("  ⚠️  Nenhuma vaga encontrada no JSON")
                
    except Exception as e:
        print(f"  ❌ Erro ao buscar Gupy: {e}")
    
    return results


# ──────────────────────────────────────────────────────────────────────────────
# CATHO - Versão Melhorada (URL corrigida)
# ──────────────────────────────────────────────────────────────────────────────

def fetch_catho_improved(search_term: str = "logistica") -> list[dict]:
    """
    Versão melhorada do Catho com URLs alternativas e fallbacks
    """
    results = []
    
    # Tentar múltiplas URLs
    urls_to_try = [
        f"https://www.catho.com.br/vagas/{search_term}/",
        f"https://www.catho.com.br/vagas?q={search_term}&city=sao-paulo",
        f"https://www.catho.com.br/vagas?q={search_term}+sao+paulo",
    ]
    
    for url in urls_to_try:
        try:
            print(f"  Tentando: {url[:50]}...")
            r = requests.get(url, headers=HEADERS, timeout=15)
            print(f"    Status: {r.status_code}")
            
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                
                # Tenta múltiplos seletores
                selectors = [
                    ("li.vaga", "li com classe vaga"),
                    ("article.job", "article com classe job"),
                    ("div[data-testid='job-card']", "div data-testid job-card"),
                    (".resultado", "div com classe resultado"),
                ]
                
                for selector, desc in selectors:
                    cards = soup.select(selector)
                    print(f"    Seletor '{desc}': {len(cards)} elementos")
                    
                    for card in cards[:5]:
                        # Tentar extrair dados
                        title_el = card.find(["h2", "h3"])
                        company_el = card.find(class_=["company", "empresa", "emprVaga"])
                        link_el = card.find("a", href=True)
                        
                        if title_el and link_el:
                            results.append({
                                "id": f"catho_{hash(link_el['href'])}",
                                "title": title_el.get_text(strip=True),
                                "company": company_el.get_text(strip=True) if company_el else "Empresa",
                                "url": link_el["href"] if link_el["href"].startswith("http") else f"https://www.catho.com.br{link_el['href']}",
                            })
                    
                    if results:
                        break
                
                if results:
                    print(f"  ✓ {len(results)} vagas encontradas!")
                    break
                    
        except Exception as e:
            print(f"    ❌ Erro: {e}")
            continue
    
    return results


# ──────────────────────────────────────────────────────────────────────────────
# LINKEDIN - Nova fonte (Alternativa confiável)
# ──────────────────────────────────────────────────────────────────────────────

def fetch_linkedin_jobs(search_term: str = "logistica") -> list[dict]:
    """
    Busca vagas no LinkedIn
    Nota: LinkedIn pode ter proteção contra scraping
    """
    results = []
    
    # URL de busca do LinkedIn
    url = "https://br.linkedin.com/jobs/search"
    
    try:
        params = {
            "keywords": search_term,
            "location": "São Paulo, São Paulo, Brasil",
            "geoId": "102569881",
            "f_TPR": "r604800",  # Últimos 7 dias
        }
        
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        print(f"  LinkedIn Status: {r.status_code}")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Procurar por job listings
            jobs = soup.find_all("div", {"data-job-id": True})
            print(f"  Jobs encontrados: {len(jobs)}")
            
            for job in jobs[:10]:
                title_el = job.find("h3", class_="base-search-card__title")
                company_el = job.find("h4", class_="base-search-card__subtitle")
                location_el = job.find("span", class_="job-search-card__location")
                link_el = job.find("a", {"data-tracking-control-name": "public_jobs_srp_job_card_title"})
                
                if title_el and company_el:
                    results.append({
                        "id": f"linkedin_{job.get('data-job-id')}",
                        "title": title_el.get_text(strip=True),
                        "company": company_el.get_text(strip=True),
                        "location": location_el.get_text(strip=True) if location_el else "São Paulo, SP",
                        "url": link_el["href"] if link_el and link_el.get("href") else "",
                    })
            
            if results:
                print(f"  ✓ {len(results)} vagas extraídas!")
        else:
            print(f"  ⚠️  LinkedIn retornou status {r.status_code}")
            
    except Exception as e:
        print(f"  ❌ Erro ao buscar LinkedIn: {e}")
    
    return results


# ──────────────────────────────────────────────────────────────────────────────
# TESTES
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 TESTE: Versões Melhoradas de Gupy, Catho e LinkedIn")
    print("="*80 + "\n")
    
    # Teste Gupy
    print("1️⃣  GUPY MELHORADO")
    print("-" * 80)
    gupy_jobs = fetch_gupy_jobs_improved("logistica")
    print(f"Total: {len(gupy_jobs)} vagas\n")
    if gupy_jobs:
        for i, j in enumerate(gupy_jobs[:3], 1):
            print(f"  {i}. {j['title']} — {j['company']}")
    
    # Teste Catho
    print("\n\n2️⃣  CATHO MELHORADO")
    print("-" * 80)
    catho_jobs = fetch_catho_improved("logistica")
    print(f"Total: {len(catho_jobs)} vagas\n")
    if catho_jobs:
        for i, j in enumerate(catho_jobs[:3], 1):
            print(f"  {i}. {j['title']} — {j['company']}")
    
    # Teste LinkedIn
    print("\n\n3️⃣  LINKEDIN NOVO")
    print("-" * 80)
    linkedin_jobs = fetch_linkedin_jobs("logistica aerea")
    print(f"Total: {len(linkedin_jobs)} vagas\n")
    if linkedin_jobs:
        for i, j in enumerate(linkedin_jobs[:3], 1):
            print(f"  {i}. {j['title']} — {j['company']}")
    
    print("\n" + "="*80)
    print("✅ Testes concluídos!")
    print("="*80 + "\n")

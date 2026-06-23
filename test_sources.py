#!/usr/bin/env python
"""
test_sources.py — Tester interativo para testar cada fonte individualmente
"""

import requests
from bs4 import BeautifulSoup
import json
import sys

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

def test_vagas_com():
    """Testa Vagas.com"""
    print("\n" + "="*70)
    print("🧪 TESTE: Vagas.com")
    print("="*70 + "\n")
    
    url = "https://www.vagas.com.br/vagas-de-logistica-aerea-em-sao-paulo-sp"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"✓ HTTP {r.status_code}")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            vagas = soup.select("li.vaga")
            print(f"✓ Encontradas {len(vagas)} vagas\n")
            
            for i, vaga in enumerate(vagas, 1):
                title_link = vaga.select_one("h2.cargo a")
                if title_link:
                    print(f"  {i}. {title_link.get_text(strip=True)}")
            return True
    except Exception as e:
        print(f"❌ Erro: {e}")
    return False

def test_gupy():
    """Testa Gupy API"""
    print("\n" + "="*70)
    print("🧪 TESTE: Gupy API")
    print("="*70 + "\n")
    
    endpoints = [
        ("portal.gupy.io", "https://portal.gupy.io/api/v1/jobs"),
        ("api.gupy.io", "https://api.gupy.io/api/v1/jobs"),
        ("gupy.io", "https://gupy.io/api/v1/jobs"),
    ]
    
    for name, url in endpoints:
        print(f"\nTestando {name}:")
        try:
            r = requests.get(url, params={"jobName": "logistica"}, timeout=10)
            print(f"  Status: {r.status_code}")
            
            if r.status_code == 200:
                if "json" in r.headers.get("content-type", "").lower():
                    data = r.json()
                    jobs = data.get("data", [])
                    print(f"  ✓ JSON válido! {len(jobs)} vagas")
                    if jobs:
                        print(f"  Exemplo: {jobs[0].get('name', 'N/A')}")
                    return True
                else:
                    print(f"  ❌ Não é JSON (type: {r.headers.get('content-type')})")
            else:
                print(f"  ❌ HTTP error")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {e}")
    
    return False

def test_catho():
    """Testa Catho"""
    print("\n" + "="*70)
    print("🧪 TESTE: Catho")
    print("="*70 + "\n")
    
    urls = [
        "https://www.catho.com.br/vagas/logistica/",
        "https://www.catho.com.br/vagas/logistica-sao-paulo/",
        "https://www.catho.com.br/vagas/logistica-aerea/",
    ]
    
    for url in urls:
        print(f"\nTestando: {url}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            print(f"  Status: {r.status_code}", end="")
            
            if r.status_code == 200:
                print(" ✓")
                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select("li, article, [data-testid]")
                print(f"  Elementos encontrados: {len(cards)}")
                return True
            else:
                print(" ❌")
        except Exception as e:
            print(f"  ❌ {e}")
    
    return False

def main():
    print("\n" + "="*70)
    print("🔍 TESTE INTERATIVO DE FONTES DE VAGAS")
    print("="*70)
    
    tests = [
        ("Vagas.com", test_vagas_com),
        ("Gupy", test_gupy),
        ("Catho", test_catho),
    ]
    
    results = {}
    for name, func in tests:
        results[name] = func()
    
    # Resumo
    print("\n\n" + "="*70)
    print("📊 RESUMO DOS TESTES")
    print("="*70 + "\n")
    
    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {name}: {'Funcionando' if status else 'Não funcionando'}")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()

"""
scraper_com_selenium.py
Versão com Selenium para Gupy e Catho
USO FUTURO - Não é usado no scraper principal por enquanto
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime

def get_chrome_options():
    """Configuração otimizada do Chrome"""
    options = webdriver.ChromeOptions()
    
    # Modo headless (sem interface gráfica)
    options.add_argument("--headless")
    
    # Melhorar compatibilidade
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # User-Agent realista
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Desabilitar detecção de Selenium
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Melhorar performance
    options.add_argument("--disable-images")
    
    return options


def fetch_gupy_selenium(search_term: str = "logistica", max_jobs: int = 30) -> list[dict]:
    """
    Busca vagas no Gupy usando Selenium
    Aguarda o JavaScript renderizar os dados
    """
    results = []
    
    print(f"  [Gupy] Iniciando busca por '{search_term}'...")
    
    options = get_chrome_options()
    service = Service(ChromeDriverManager().install())
    driver = None
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        
        # Navegar para a página de busca
        url = f"https://portal.gupy.io/jobs?search={search_term}&city=São Paulo"
        print(f"  [Gupy] Abrindo {url}")
        driver.get(url)
        
        # Aguardar os jobs carregarem (até 15 segundos)
        print(f"  [Gupy] Aguardando carregamento...")
        wait = WebDriverWait(driver, 15)
        
        # Procurar por múltiplos seletores possíveis
        try:
            wait.until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "job-card"))
            )
        except:
            # Se não encontrar job-card, procurar por outras classes
            try:
                wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, "//article"))
                )
            except:
                print(f"  [Gupy] Timeout - nenhuma vaga encontrada")
                return results
        
        # Extrair vagas
        job_elements = driver.find_elements(By.CLASS_NAME, "job-card")
        if not job_elements:
            job_elements = driver.find_elements(By.XPATH, "//article")
        
        print(f"  [Gupy] Encontradas {len(job_elements)} vagas")
        
        for idx, job_el in enumerate(job_elements[:max_jobs]):
            try:
                # Tentar encontrar título
                title = None
                for selector in [".job-title", "h2", "h3"]:
                    try:
                        title = job_el.find_element(By.CSS_SELECTOR, selector).text
                        if title:
                            break
                    except:
                        pass
                
                # Tentar encontrar empresa
                company = None
                for selector in [".company-name", ".company", "[data-testid='company-name']"]:
                    try:
                        company = job_el.find_element(By.CSS_SELECTOR, selector).text
                        if company:
                            break
                    except:
                        pass
                
                # Tentar encontrar link
                link = None
                try:
                    link_el = job_el.find_element(By.TAG_NAME, "a")
                    link = link_el.get_attribute("href")
                except:
                    pass
                
                if title and link:
                    results.append({
                        "id": f"gupy_{hash(link)}",
                        "title": title,
                        "company": company or "Empresa",
                        "url": link,
                        "source": "Gupy (Selenium)",
                        "date_posted": datetime.now().strftime("%Y-%m-%d"),
                    })
                    print(f"    [{idx+1}] ✓ {title[:50]}")
            
            except Exception as e:
                print(f"    Erro ao processar vaga {idx+1}: {e}")
                continue
            
            # Delay pequeno entre processamentos
            time.sleep(0.1)
    
    except Exception as e:
        print(f"  [Gupy] Erro geral: {e}")
    
    finally:
        if driver:
            driver.quit()
    
    print(f"  [Gupy] Total extraído: {len(results)} vagas\n")
    return results


def fetch_catho_selenium(search_term: str = "logistica", max_jobs: int = 30) -> list[dict]:
    """
    Busca vagas no Catho usando Selenium
    Lida com bloqueios WAF
    """
    results = []
    
    print(f"  [Catho] Iniciando busca por '{search_term}'...")
    
    options = get_chrome_options()
    service = Service(ChromeDriverManager().install())
    driver = None
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        
        # Tentar múltiplas URLs
        urls_to_try = [
            f"https://www.catho.com.br/vagas/{search_term}/",
            f"https://www.catho.com.br/vagas?q={search_term}&city=sao-paulo",
            f"https://www.catho.com.br/vagas?q={search_term}",
        ]
        
        for url in urls_to_try:
            try:
                print(f"  [Catho] Tentando {url[:50]}...")
                driver.get(url)
                
                # Verificar se foi bloqueado
                page_title = driver.title
                if "403" in driver.page_source or "Access Denied" in page_title:
                    print(f"  [Catho] ⚠️  Página bloqueada por WAF")
                    time.sleep(2)
                    continue
                
                # Adicionar pequeno delay para a página carregar completamente
                time.sleep(2)
                
                # Aguardar elementos de vaga
                wait = WebDriverWait(driver, 10)
                
                # Procurar por diferentes seletores
                job_elements = []
                try:
                    job_elements = wait.until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "job-item"))
                    )
                except:
                    try:
                        job_elements = wait.until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.vaga"))
                        )
                    except:
                        job_elements = driver.find_elements(By.TAG_NAME, "article")
                
                print(f"  [Catho] Encontradas {len(job_elements)} vagas")
                
                if len(job_elements) > 0:
                    # Processar vagas
                    for idx, job_el in enumerate(job_elements[:max_jobs]):
                        try:
                            # Extrair título
                            title = None
                            for selector in ["h2", "h3", ".cargo"]:
                                try:
                                    title_el = job_el.find_element(By.CSS_SELECTOR, selector)
                                    if title_el:
                                        title = title_el.text
                                        break
                                except:
                                    pass
                            
                            # Extrair empresa
                            company = None
                            for selector in [".company", ".emprVaga", ".empresa"]:
                                try:
                                    company_el = job_el.find_element(By.CSS_SELECTOR, selector)
                                    if company_el:
                                        company = company_el.text
                                        break
                                except:
                                    pass
                            
                            # Extrair link
                            link = None
                            try:
                                link_el = job_el.find_element(By.TAG_NAME, "a")
                                link = link_el.get_attribute("href")
                                if link and not link.startswith("http"):
                                    link = f"https://www.catho.com.br{link}"
                            except:
                                pass
                            
                            if title and link:
                                results.append({
                                    "id": f"catho_{hash(link)}",
                                    "title": title,
                                    "company": company or "Empresa",
                                    "url": link,
                                    "source": "Catho (Selenium)",
                                    "date_posted": datetime.now().strftime("%Y-%m-%d"),
                                })
                                print(f"    [{idx+1}] ✓ {title[:50]}")
                        
                        except Exception as e:
                            continue
                        
                        time.sleep(0.1)
                    
                    if results:
                        break
                
            except Exception as e:
                print(f"  [Catho] Erro: {e}")
                time.sleep(1)
                continue
    
    except Exception as e:
        print(f"  [Catho] Erro geral: {e}")
    
    finally:
        if driver:
            driver.quit()
    
    print(f"  [Catho] Total extraído: {len(results)} vagas\n")
    return results


# Teste direto
if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 TESTE: Gupy e Catho com Selenium")
    print("="*80 + "\n")
    
    print("Nota: Primeiro install com: pip install selenium webdriver-manager\n")
    
    # Gupy
    gupy_jobs = fetch_gupy_selenium("logistica", max_jobs=5)
    
    # Catho
    catho_jobs = fetch_catho_selenium("logistica", max_jobs=5)
    
    # Sumário
    print("\n" + "="*80)
    print("📊 Resumo:")
    print(f"  Gupy: {len(gupy_jobs)} vagas")
    print(f"  Catho: {len(catho_jobs)} vagas")
    print(f"  Total: {len(gupy_jobs) + len(catho_jobs)} vagas")
    print("="*80 + "\n")

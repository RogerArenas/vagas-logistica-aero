import requests
from bs4 import BeautifulSoup
r = requests.get('https://www.vagas.com.br/vagas-de-logistica?pagina=1', headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
soup = BeautifulSoup(r.text, 'html.parser')
card = soup.select_one('li.vaga')
if not card:
    print('No card found')
else:
    print('---CARD TEXT---')
    print(repr(card.get_text(' ', strip=True)))
    print('\n---HTML PREVIEW---')
    print(card.prettify()[:2000])

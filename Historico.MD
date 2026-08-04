# Historico.md

## Histórico de alterações do projeto

### 2026-08-04

- Limpeza completa do projeto para manter apenas o núcleo funcional.
- Removidos arquivos de diagnóstico e documentações temporárias que não eram utilizados.
- Atualizado `scraper.py` para eliminar suporte a Selenium e manter apenas `Vagas.com`.
- Criados os documentos:
  - `Melhorias.MD`
  - `Implementação final.MD`
  - `Historico.MD`
- Verificado que o scraper principal funciona em `--dry-run` e coleta 121 vagas do `Vagas.com`.
- Detectado que o fluxo Selenium não trouxe resultados úteis para `Gupy`/`Catho` no ambiente atual.

### 2026-06-23

- Diagnóstico inicial indicou que o `Vagas.com` estava funcionando, mas `Gupy` e `Catho` falhavam.
- Foi preparada uma versão alternativa com suporte a Selenium em `scraper_com_selenium.py`.
- Criadas várias ferramentas de análise e relatórios para investigação.

### Observações

- O histórico documenta a evolução do projeto de um conjunto maior de scripts de diagnóstico para uma versão enxuta e funcional.
- A versão final prioriza simplicidade e manutenção, com foco em dados válidos do `Vagas.com`.

## Nota

Para futuras melhorias, registrar aqui cada alteração importante, como:
- adição de novas fontes de vagas
- mudanças nos seletores do `Vagas.com`
- atualização da automação do GitHub Actions
- correções na lógica de deduplicação e de alertas

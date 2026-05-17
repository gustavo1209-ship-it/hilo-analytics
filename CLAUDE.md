# hilo-analytics

Scripts Python de coleta automática de dados de inteligência competitiva para a **Hilo Boutique**.
Coleta dados de e-commerce (VTEX), Instagram e Google Maps e salva no Supabase.

## Setup

```bash
pip install -r requirements.txt
```

Criar arquivo `.env` na raiz com:
```
SUPABASE_URL=https://wbmcyhqlsiuekbizwcti.supabase.co
SUPABASE_KEY=<service_role ou anon key>
REQUEST_DELAY_SECONDS=2.5
SCHEDULE_SOCIAL_CRON=0 8 * * *
SCHEDULE_ECOMMERCE_CRON=0 6 * * 1
# Opcional — Instagram com login (evita rate limit 429)
IG_USERNAME=
IG_PASSWORD=
```

## Comandos

```bash
python run.py                 # roda tudo (instagram + ecommerce + maps + report)
python run.py instagram       # só snapshots do Instagram dos concorrentes
python run.py ecommerce       # só produtos VTEX (NV, John John, Calvin Klein)
python run.py maps            # só localizações Google Maps
python run.py report          # só relatório no terminal
python run.py schedule        # modo daemon — roda nos horários do .env
```

## Estrutura

```
run.py              # entry point — roteador de comandos
config.py           # constantes: VTEX_TARGETS, COMPETITOR_IG_HANDLES, env vars
collectors/
  ecommerce.py      # scraper VTEX — NV, John John, Calvin Klein
  instagram.py      # instaloader — seguidores, engajamento, snapshots
  google_maps.py    # localizações e avaliações dos concorrentes
storage/
  client.py         # helpers Supabase: get_client, get_brand_id, start_run, finish_run
reports/
  summary.py        # relatório no terminal com rich
requirements.txt
```

## E-commerce — API VTEX

As marcas NV, John John e Calvin Klein usam a plataforma VTEX com API pública:

```
GET {vtex_url}/api/catalog_system/pub/products/search?_from=0&_to=49
```

Retorna JSON com produtos incluindo preços (`commertialOffer.Price` e `ListPrice`).
Paginado de 50 em 50. Upsertar em `hb_scraped_products`, histórico em `hb_price_history`.

**Targets configurados em `config.VTEX_TARGETS`:**
- NV → https://www.bynv.com.br
- John John → https://www.johnjohndenim.com.br
- Calvin Klein → https://www.calvinklein.com.br

**Shop2gether e OQVestir NÃO são coletáveis** — usam plataforma FBITS (CSR/SPA), sem API pública.

## Instagram

Usa `instaloader` para coletar seguidores, following, posts, média de likes dos últimos 30 dias
e taxa de engajamento. Sem credenciais → bloqueio 429 após poucas requisições.

Para evitar rate limit, adicionar `IG_USERNAME` e `IG_PASSWORD` no `.env`.

**Handles mapeados em `config.COMPETITOR_IG_HANDLES`:**
shop2gether, oqvestir, mamoboutique, femmestoremultimarcas, slstorenet,
lojagerbella, lojaalegreto, apicemultimarcas, oliviamultimarcas, sedanaya

## Supabase — tabelas gravadas (prefixo hb_)

| Tabela                  | O que armazena                                      |
|-------------------------|-----------------------------------------------------|
| hb_competitors          | Cadastro dos concorrentes com métricas Instagram    |
| hb_scraped_products     | Produtos coletados (nome, preço, categoria, loja)   |
| hb_price_history        | Histórico de variação de preços por produto         |
| hb_snapshots_social     | Snapshots diários de métricas Instagram             |
| hb_collection_runs      | Log de execuções (start, finish, erros, criados)    |
| hb_locations            | Localizações e avaliações Google Maps               |
| hb_market_kpis          | KPIs de mercado (editado manualmente)               |
| hb_market_insights      | Insights estratégicos (editado manualmente)         |
| hb_product_trends       | Tendências de produto (editado manualmente)         |

Prefixo `hb_` evita conflito com tabelas do projeto controle-gastos no mesmo Supabase
(`wbmcyhqlsiuekbizwcti` — "gustavo1209-ship-it's Project").

## Armadilhas conhecidas

**lxml não instala no Python 3.14** — sem wheel pré-compilado.
Usar sempre `"html.parser"` no BeautifulSoup, nunca `"lxml"`.

**Windows — UnicodeEncodeError** com caracteres especiais no terminal.
`run.py` já faz `sys.stdout.reconfigure(encoding="utf-8")` no início.

**Variáveis de ambiente obrigatórias:** `SUPABASE_URL` e `SUPABASE_KEY`.
Se ausentes, `config.py` lança `KeyError` imediatamente ao importar.

## GitHub

Repositório: https://github.com/gustavo1209-ship-it/hilo-analytics

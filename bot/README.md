# Bot de tendencias PRL/SST → propuestas Reels & TikTok

Script Python que **monitorea contenido de tendencia en Prevención de Riesgos Laborales (PRL/SST) en LATAM y España**, lo sintetiza con Claude y devuelve:

1. Lectura de tendencias de la semana.
2. **3 propuestas concretas** de Reel/TikTok (hook, estructura por segundos, audio, CTA, hashtags).
3. **3 secciones genéricas** para mantener una línea editorial coherente y rotable indefinidamente.
4. Apéndice con limitaciones de los datos.

## Arquitectura

```
bot/
├── main.py                  # CLI orquestador
├── analyzer.py              # llamada a Claude (Anthropic SDK + prompt caching + adaptive thinking)
├── config.py                # settings + keywords semilla PRL
├── prompts/system.md        # prompt maestro (estratega PRL/SST)
├── sources/
│   ├── google_trends.py     # pytrends (sin API key)
│   ├── youtube.py           # YouTube Data API v3 (opcional)
│   └── tiktok_creative.py   # ads.tiktok.com Creative Center (best-effort)
├── requirements.txt
└── .env.example
```

## Setup

```bash
cd bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edita .env con tu ANTHROPIC_API_KEY (y opcionalmente YOUTUBE_API_KEY)
```

### Obtener las API keys

- **Anthropic** (obligatoria): https://console.anthropic.com/ → Settings → API Keys.
- **YouTube Data API v3** (opcional): Google Cloud Console → habilita la API → Credentials → API key. Sin esta key el bot salta YouTube y trabaja solo con Trends + TikTok.
- **TikTok Creative Center**: scraping público, no requiere key. Si el endpoint cambia o te bloquean por geo, el bot continúa sin esos datos.

## Uso

```bash
# defaults (.env): regiones ES,MX,AR,CO,CL,PE; ventana últimos 7 días
python main.py

# regiones custom
python main.py --regions ES,MX --timeframe "today 1-m"

# solo recolecta y muestra el bloque de datos sin llamar a Claude (debug)
python main.py --dry-run

# afina effort y guarda el informe
python main.py --effort medium --output reports/$(date +%Y-%m-%d).md

# saltar fuentes específicas
python main.py --skip-tiktok --skip-youtube
```

## Flags

| Flag | Default | Descripción |
|---|---|---|
| `--regions` | `ES,MX,AR,CO,CL,PE` | Códigos ISO país, CSV. |
| `--timeframe` | `now 7-d` | Ventana de Google Trends (`now 1-d`, `now 7-d`, `today 1-m`, `today 3-m`). |
| `--keywords` | semilla PRL | Override de keywords (CSV). |
| `--skip-trends` / `--skip-youtube` / `--skip-tiktok` | off | Salta esa fuente. |
| `--effort` | `high` | `low`/`medium`/`high`/`xhigh`/`max`. Más alto = más tokens y razonamiento. |
| `--output` | (stdout) | Ruta donde escribir el informe markdown. |
| `--dry-run` | off | Solo recolecta; no llama a Claude. |

## Cómo está hecho el lado de Claude

- **Modelo:** `claude-opus-4-7` por defecto (override con `CLAUDE_MODEL`).
- **Adaptive thinking:** el modelo decide cuánto razonar por turno; sin `budget_tokens` (deprecated en 4.7).
- **Prompt caching:** el system prompt (`prompts/system.md`) lleva `cache_control: ephemeral`. La segunda corrida del mismo día reusa caché y baja costo ~10×.
- **Streaming:** evita timeouts si el informe crece.

Verifica los hits de caché en la línea `--- usage:` que se imprime al final.

## Ampliar o adaptar

- **Cambiar nicho:** edita `NICHE` y `SEED_KEYWORDS` en `config.py`, y reescribe `prompts/system.md` con el rol nuevo.
- **Añadir fuente** (Meta Graph, Reddit, etc.): crea `sources/<nombre>.py` con `fetch_*` y `to_markdown(...)`, y añádelo al pipeline en `main.py`.
- **Programar semanal:** envuelve `python main.py --output reports/...md` en un cron o GitHub Action.

## Limitaciones conocidas

- **TikTok Creative Center** no tiene API oficial; el endpoint `creative_radar_api` se usa best-effort y puede romperse. Cuando rompa, el bot lo declara y continúa.
- **pytrends** puede recibir 429 si abusas; espera 5-10 min entre corridas pesadas.
- **YouTube Data API** tiene cuota gratuita de 10 000 unidades/día (≈100 búsquedas con stats). Si la consumes, el bot lo dice y sigue.
- Los hashtags de TikTok que devolvemos son **trending generales**, no PRL-específicos. Claude los usa solo como pista de formatos virales para colonizar con ángulo PRL.

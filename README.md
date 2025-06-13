# World University Scraper

Proyecto de scraping, procesamiento y exportación de datos de rankings universitarios (Times Higher Education).

## Estructura del repositorio

```
world_university_scraper/
├── README.md
├── poetry.lock
├── pyproject.toml
├── review_pkl.py
├── config/
│   ├── default.yml
│   ├── default_selenium.yml
│   ├── development.yml
│   └── production.yml
├── data/
│   ├── processed/
│   │   └── rankings_processed_20250313_121234.pkl
│   └── raw/
│       ├── rankings_2025_reputation_20250313_145232.html
│       ├── rankings_2025_reputation_20250313_145239.json
│       ├── rankings_raw_20250312_225636.html
│       ├── rankings_raw_20250313_111156.html
│       ├── rankings_raw_20250313_113000.html
│       ├── rankings_raw_20250313_114511.html
│       └── rankings_raw_20250313_121234.html
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── pipeline.py
│   ├── exporters/
│   │   ├── __init__.py
│   │   ├── base_exporter.py
│   │   ├── exporter_factory.py
│   │   └── postgres_exporter.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base_parser.py
│   │   └── rankings_parser.py
│   ├── processors/
│   │   ├── __init__.py
│   │   └── data_processor.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py
│   │   ├── rankings_scraper.py
│   │   ├── selenium_base_scraper.py
│   │   └── selenium_rankings_scraper.py
│   ├── storage/
│   │   ├── __init__.py
│   │   └── file_storage.py
│   └── utils/
│       ├── __init__.py
│       ├── exceptions.py
│       ├── http.py
│       └── selenium_helpers.py
```

## Instalación y dependencias

- Python 3.11+
- [Poetry](https://python-poetry.org/) para gestión de dependencias

Instalación:
```bash
poetry install
poetry shell
```

## Configuración

Archivos YAML en `config/` para distintos entornos:
- `default.yml`, `default_selenium.yml`, `development.yml`, `production.yml`

## Ejecución

```bash
poetry run python -m src --config config/default_selenium.yml --log-level INFO
```

## Componentes principales

- **Scrapers**: Obtención de datos (HTTP y Selenium)
- **Parsers**: Parseo y estructuración de datos
- **Processors**: Limpieza y transformación
- **Exporters**: Exportación a formatos y bases de datos
- **Storage**: Persistencia en archivos
- **Utils**: Utilidades comunes

## Ejemplo de revisión de datos procesados

```python
import pandas as pd
file = pd.read_pickle("data/processed/rankings_processed_20250313_121234.pkl")
print(file.head())
```

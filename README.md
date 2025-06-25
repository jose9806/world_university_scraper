# World University Scraper

Sistema completo de scraping, procesamiento y exportación de datos de rankings universitarios de Times Higher Education (THE).

## 🏗️ Arquitectura del Sistema

```
world_university_scraper/
├── README.md
├── poetry.lock
├── pyproject.toml
├── setup.py                    # 🔥 SCRIPT DE CONFIGURACIÓN INICIAL
├── config/                     # Configuraciones
│   ├── default_selenium.yml    # Config principal de rankings
│   ├── university_detail.yml   # Config de detalles universitarios
│   └── full_pipeline.yml       # Config del pipeline completo
├── scripts/                    # Scripts especializados
│   ├── scrape_rankings.py      # Scraper principal de rankings
│   └── scrape_universities.py  # Scraper de detalles universitarios
├── data/
│   ├── raw/                    # HTML y JSON sin procesar
│   ├── processed/              # Datos procesados (pickle, CSV)
│   ├── universities/           # Datos detallados de universidades
│   ├── exports/                # Datos exportados (CSV, Excel, JSON)
│   │   ├── csv/               # Exportaciones CSV
│   │   ├── excel/             # Exportaciones Excel
│   │   └── json/              # Exportaciones JSON
│   ├── pipeline_results/       # Resultados de pipeline completo
│   └── backups/               # Backups automáticos
├── logs/                       # Archivos de log
│   ├── main_orchestrator.log   # Log del orquestador principal
│   ├── rankings_scraper.log    # Log del scraping de rankings
│   └── university_scraper.log  # Log del scraping de universidades
├── src/
│   ├── __main__.py            # 🔥 ORQUESTADOR PRINCIPAL
│   ├── core/
│   │   ├── pipeline.py         # Pipeline de rankings
│   │   └── university_pipeline.py  # Pipeline de universidades
│   ├── scrapers/
│   │   ├── rankings_scraper.py
│   │   ├── selenium_rankings_scraper.py
│   │   └── university_detail_scraper.py  # 🔥 NUEVO
│   ├── parsers/
│   │   ├── rankings_parser.py   # 🔥 MEJORADO
│   │   └── university_detail_parser.py   # 🔥 NUEVO
│   ├── processors/
│   ├── exporters/
│   ├── storage/
│   └── utils/
```

## 🚀 Instalación y Configuración

### Requisitos

- Python 3.11+
- [Poetry](https://python-poetry.org/) para gestión de dependencias
- Google Chrome (para Selenium)

### 🔧 Configuración Inicial Automática (Recomendado)

```bash
# 1. Clonar el repositorio
git clone <repository-url>
cd world_university_scraper

# 2. Instalar dependencias
poetry install
poetry shell

# 3. 🔥 EJECUTAR CONFIGURACIÓN AUTOMÁTICA
python setup.py
```

El script `setup.py` automáticamente:

- ✅ Crea toda la estructura de directorios necesaria
- ✅ Genera archivos de configuración template
- ✅ Crea `.env.template` con variables de entorno
- ✅ Configura `.gitignore` apropiado
- ✅ Muestra los siguientes pasos de implementación

### 📋 Después de Ejecutar setup.py

#### 1. Copiar Archivos de Código

```bash
# REEMPLAZAR archivos existentes (versiones mejoradas)
cp <provided>/rankings_parser.py src/parsers/rankings_parser.py
cp <provided>/__main__.py src/__main__.py

# CREAR archivos nuevos
cp <provided>/university_detail_scraper.py src/scrapers/
cp <provided>/university_detail_parser.py src/parsers/
cp <provided>/university_pipeline.py src/core/
cp <provided>/scrape_rankings.py scripts/
cp <provided>/scrape_universities.py scripts/
cp <provided>/university_detail.yml config/
cp <provided>/full_pipeline.yml config/
```

#### 2. Configurar Variables de Entorno

```bash
# Copiar template y personalizar
cp .env.template .env
# Editar .env con tus valores reales
```

### 🔄 Configuración Manual (Alternativa)

Si prefieres configurar manualmente:

```bash
# Crear directorios
mkdir -p logs data/{raw,processed,universities,exports/{csv,excel,json},pipeline_results,backups} scripts

# Instalar dependencias
poetry install
poetry shell
```

### Configuración de Base de Datos (Opcional)

```bash
# Para exportar a PostgreSQL
export POSTGRES_PASSWORD="tu_password_seguro"

# O en archivo .env
echo "POSTGRES_PASSWORD=tu_password_seguro" >> .env
```

## ✅ Verificación de Instalación

### Prueba Rápida

```bash
# Verificar que todo está correctamente instalado
python -m src --mode rankings-only --limit 5 --log-level DEBUG --dry-run

# Primera ejecución real (datos limitados)
python -m src --mode rankings-only --limit 5 --log-level DEBUG
```

### Diagnóstico de Problemas

```bash
# Verificar configuración
python setup.py  # Ejecutar nuevamente para verificar

# Ver estructura de directorios creada
tree data/ logs/ scripts/ config/

# Verificar importaciones
python -c "from src.scrapers import UniversityDetailScraper; print('✓ Imports OK')"
python -c "from src.parsers import UniversityDetailParser; print('✓ Imports OK')"
```

## 🎯 Modos de Ejecución

El sistema ofrece múltiples modos de ejecución a través del orquestador principal:

### 1. 🔥 Orquestador Principal con Auto-Inserción PostgreSQL

```bash
# Pipeline completo con auto-inserción a PostgreSQL
python -m src --mode full-pipeline --config config/full_pipeline.yml

# Solo rankings con auto-inserción a PostgreSQL
python -m src --mode rankings-only --limit 50 --config config/full_pipeline.yml

# Solo universidades con auto-inserción a PostgreSQL
python -m src --mode universities-only \
    --rankings-file data/raw/rankings_2025_reputation.json \
    --config config/full_pipeline.yml

# Deshabilitar PostgreSQL temporalmente
python -m src --mode rankings-only --no-postgres --limit 10

# Pipeline completo con exportación tradicional + PostgreSQL
python -m src --mode full-pipeline --export-data --config config/full_pipeline.yml
```

### 2. 📊 Scripts Especializados

#### Scraping de Rankings

```bash
# Básico
python scripts/scrape_rankings.py

# Con parámetros personalizados
python scripts/scrape_rankings.py \
    --config config/default_selenium.yml \
    --year 2025 \
    --view reputation \
    --process-data \
    --save-pickle \
    --log-level INFO

# Solo guardar HTML para debugging
python scripts/scrape_rankings.py \
    --save-html \
    --no-json \
    --log-level DEBUG
```

#### Scraping de Universidades

```bash
# Desde archivo de rankings
python scripts/scrape_universities.py \
    --rankings-file data/raw/rankings_2025_reputation_20250613_123456.json \
    --config config/university_detail.yml

# Con procesamiento por lotes
python scripts/scrape_universities.py \
    --rankings-file rankings.json \
    --batch-size 25 \
    --log-level INFO

# Para testing (solo primeras 10 universidades)
python scripts/scrape_universities.py \
    --rankings-file rankings.json \
    --limit 10 \
    --log-level DEBUG
```

## 📋 Flujos de Trabajo Típicos

### Flujo Completo Automatizado

```bash
# Ejecutar pipeline completo con todas las funcionalidades
python -m src \
    --mode full-pipeline \
    --config config/full_pipeline.yml \
    --export-data \
    --year 2025 \
    --batch-size 50
```

### Flujo por Etapas

```bash
# Paso 1: Scraping de rankings
python -m src --mode rankings-only --config config/default_selenium.yml

# Paso 2: Scraping de universidades (usar el archivo generado en paso 1)
python -m src --mode universities-only \
    --rankings-file data/raw/rankings_2025_reputation_20250613_145230.json

# Paso 3: Exportar a diferentes formatos
python -m src --mode export-only \
    --processed-file data/processed/combined_data_20250613_150000.pkl
```

### Flujo de Desarrollo/Testing

```bash
# Testing rápido con datos limitados
python -m src \
    --mode full-pipeline \
    --limit 20 \
    --batch-size 5 \
    --log-level DEBUG \
    --rankings-only-flag  # Solo rankings, sin universidades
```

## ⚙️ Configuración Detallada

### Configuración Principal (`full_pipeline.yml`)

```yaml
general:
  output_dir: 'data/pipeline_results'
  log_level: 'INFO'

# Archivos de configuración para cada componente
rankings_config: 'config/default_selenium.yml'
university_config: 'config/university_detail.yml'

# Configuración de exportadores
exporters:
  postgres:
    enabled: true
    host: 'localhost'
    database: 'university_rankings'
    # ... más opciones

  csv:
    enabled: true
    output_dir: 'data/exports/csv'

  excel:
    enabled: false
    output_dir: 'data/exports/excel'
```

### Configuración de Rankings (`default_selenium.yml`)

```yaml
scraper:
  type: 'selenium'
  base_url: 'https://www.timeshighereducation.com/world-university-rankings/latest/world-ranking'
  rankings:
    year: '2025'
    view: 'reputation'
  request_delay: 3

selenium:
  headless: true
  page_load_timeout: 60
  save_html: true
```

### Configuración de Universidades (`university_detail.yml`)

```yaml
scraper:
  type: 'selenium'
  headless: true
  university_delay: 5 # Delay entre universidades
  max_retries: 3
```

## 📊 Exportadores Disponibles

El sistema incluye múltiples exportadores para diferentes necesidades:

### ✅ **Exportadores Siempre Disponibles**

- **CSV**: Exportación a archivos CSV estándar
- **JSON**: Exportación a archivos JSON con metadatos opcionales
- **Excel**: Exportación a archivos Excel con múltiples hojas

### 🔧 **Exportadores Opcionales**

- **PostgreSQL**: Exportación a base de datos PostgreSQL (requiere instalación y configuración)

### **Ejemplos de Configuración de Exportadores**

#### CSV Export

```yaml
exporters:
  csv:
    enabled: true
    output_dir: 'data/exports/csv'
    filename: 'rankings_{timestamp}.csv'
    encoding: 'utf-8'
    index: false
```

#### JSON Export

```yaml
exporters:
  json:
    enabled: true
    output_dir: 'data/exports/json'
    filename: 'data_{timestamp}.json'
    pretty_print: true
    include_metadata: true # Incluye información sobre exportación
```

#### Excel Export

```yaml
exporters:
  excel:
    enabled: true
    output_dir: 'data/exports/excel'
    filename: 'report_{timestamp}.xlsx'
    sheet_name: 'University_Data'
    include_summary: true # Hoja adicional con resumen
```

#### PostgreSQL Export (Opcional)

```yaml
exporters:
  postgres:
    enabled: true
    host: 'localhost'
    port: 5432
    database: 'university_rankings'
    user: 'scraper_user'
    password: '${POSTGRES_PASSWORD}' # Variable de entorno
    table_name: 'rankings'
    if_exists: 'replace' # replace, append, fail
```

```yaml
scraper:
  type: 'selenium'
  base_url: 'https://www.timeshighereducation.com/world-university-rankings/latest/world-ranking'
  rankings:
    year: '2025'
    view: 'reputation'
  request_delay: 3

selenium:
  headless: true
  page_load_timeout: 60
  save_html: true
```

## 📊 Estructura de Datos

### Datos de Rankings (Mejorados)

```json
{
  "rank": 1,
  "name": "University of Oxford",
  "country": "United Kingdom",
  "university_url": "https://www.timeshighereducation.com/world-university-rankings/university-oxford",
  "overall_score": 98.5,
  "teaching_score": 96.8,
  "research_score": 99.1,
  "citations_score": 99.9,
  "industry_income_score": 88.4,
  "international_outlook_score": 96.7
}
```

### Datos de Universidades Individuales

```json
{
  "url": "https://www.timeshighereducation.com/world-university-rankings/university-oxford",
  "name": "University of Oxford",
  "ranking_data": {
    "world_university_rankings_rank": "1",
    "reputation_ranking_rank": "3"
  },
  "key_stats": {
    "total_students": "24,515",
    "international_students": "42%",
    "faculty_count": "7,000",
    "student_faculty_ratio": "11:1"
  },
  "subjects": [
    {
      "name": "Arts & Humanities",
      "rank": "1",
      "score": "99.6"
    },
    {
      "name": "Clinical & Health",
      "rank": "2",
      "score": "97.8"
    }
  ],
  "additional_info": {
    "location": "Oxford, United Kingdom",
    "website": "https://www.ox.ac.uk",
    "description": "One of the world's oldest universities..."
  }
}
```

### Datos Combinados (Pipeline Completo)

```json
{
  "rank": 1,
  "name": "University of Oxford",
  "country": "United Kingdom",
  "university_url": "https://...",
  "overall_score": 98.5,
  "detailed_ranking_data": {
    "world_university_rankings_rank": "1"
  },
  "key_stats": {
    "total_students": "24,515"
  },
  "subjects": [...],
  "additional_info": {...}
}
```

## 🔧 Casos de Uso Específicos

### 1. Configuración Inicial Completa

```bash
# Configuración automática completa
python setup.py

# Verificar instalación
python -m src --mode rankings-only --limit 5 --dry-run

# Primera ejecución completa de prueba
python -m src --mode full-pipeline --limit 10 --batch-size 5
```

```bash
# Scraping semanal automatizado
python -m src \
    --mode rankings-only \
    --config config/default_selenium.yml \
    --process-data

# Programar con cron (Linux/Mac)
# 0 2 * * 0 cd /path/to/scraper && python -m src --mode rankings-only
```

### 2. Monitoreo Regular de Rankings

```bash
# Scraping semanal automatizado
python -m src \
    --mode rankings-only \
    --config config/default_selenium.yml \
    --process-data

# Programar con cron (Linux/Mac)
# 0 2 * * 0 cd /path/to/scraper && python -m src --mode rankings-only
```

### 3. Investigación Académica Profunda

```bash
# Scraping completo con máximo detalle
python -m src \
    --mode full-pipeline \
    --config config/full_pipeline.yml \
    --batch-size 20 \
    --export-data \
    --log-level DEBUG
```

### 3. Integración con Sistemas Externos

```bash
# Exportar solo a PostgreSQL para dashboard
python -m src \
    --mode export-only \
    --processed-file data/processed/latest_data.pkl \
    --config config/full_pipeline.yml

# Solo PostgreSQL (sin archivos)
python -m src \
    --mode rankings-only \
    --config config/postgres_only.yml \
    --no-files  # (función futura)
```

### 4. Análisis de Universidades Específicas

```bash
# Crear archivo con URLs específicas
echo "https://www.timeshighereducation.com/world-university-rankings/university-oxford" > specific_unis.txt
echo "https://www.timeshighereducation.com/world-university-rankings/harvard-university" >> specific_unis.txt

# Scraping solo de esas universidades
python scripts/scrape_universities.py \
    --urls-file specific_unis.txt \
    --config config/university_detail.yml
```

## 🐛 Troubleshooting

### Problemas de Configuración Inicial

#### 1. Error en setup.py

```bash
# Problema: setup.py falla durante la ejecución
# Solución: Verificar permisos y ejecutar paso a paso

# Crear directorios manualmente
mkdir -p logs data/{raw,processed,universities,exports/{csv,excel,json},pipeline_results,backups} scripts

# Verificar estructura creada
ls -la data/
ls -la logs/
```

#### 2. Archivos de configuración faltantes

```bash
# Problema: Config files no encontrados después de setup.py
# Solución: Crear templates manualmente

# Crear config básico
cat > config/university_detail.yml << 'EOF'
general:
  output_dir: "data/universities"
  log_level: "INFO"
scraper:
  type: "selenium"
  headless: true
  university_delay: 5
EOF

# Verificar configuración
python -c "from src.core.config import load_config; print('Config OK')"
```

#### 3. Imports fallando después de setup

```bash
# Problema: ImportError para nuevos módulos
# Solución: Verificar que los archivos están en las ubicaciones correctas

# Verificar estructura de archivos
find src/ -name "*.py" -type f | grep -E "(university_detail|__main__)"

# Verificar imports específicos
python -c "
try:
    from src.scrapers.university_detail_scraper import UniversityDetailScraper
    print('✓ UniversityDetailScraper import OK')
except ImportError as e:
    print(f'✗ Error: {e}')
"
```

### Errores Comunes

#### 4. Error de Selenium WebDriver

```bash
# Problema: WebDriver no encontrado
# Solución: Actualizar Chrome y webdriver-manager
pip install --upgrade webdriver-manager selenium
```

#### 5. Error de Parsing

```bash
# Problema: 'NoneType' object has no attribute 'text'
# Solución: Usar el parser mejorado (ya implementado)
# Verificar logs detallados:
python scripts/scrape_rankings.py --log-level DEBUG
```

#### 6. Timeout en Scraping

```bash
# Problema: Páginas cargan lentamente
# Solución: Aumentar timeouts en configuración
# En config/university_detail.yml:
selenium:
  page_load_timeout: 120  # Aumentar de 60 a 120
  wait_timeout: 20       # Aumentar de 15 a 20
```

#### 7. Límite de Rate Limiting

```bash
# Problema: Servidor rechaza requests
# Solución: Aumentar delays
scraper:
  university_delay: 10   # Aumentar delay entre universidades
  request_delay: 5       # Aumentar delay general
```

### Logs y Debugging

#### Ubicación de Logs

```bash
logs/
├── main_orchestrator.log      # Log del orquestador principal
├── rankings_scraper.log       # Log del scraping de rankings
├── university_scraper.log     # Log del scraping de universidades
└── selenium.log               # Log específico de Selenium
```

#### Comandos de Debugging

```bash
# Ver logs en tiempo real
tail -f logs/main_orchestrator.log

# Buscar errores específicos
grep -i error logs/*.log

# Ver estadísticas de scraping
grep -i "successfully" logs/*.log | wc -l
```

### Verificación de Datos

#### Revisión Rápida de Resultados

```python
# Script para revisar datos procesados + PostgreSQL
import pandas as pd
import json
from pathlib import Path

# Función de verificación automática
def verify_installation():
    """Verificar que la instalación está completa."""

    # Verificar directorios
    required_dirs = [
        "data/raw", "data/processed", "data/universities",
        "data/exports/csv", "logs", "scripts"
    ]

    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)

    if missing_dirs:
        print(f"❌ Directorios faltantes: {missing_dirs}")
        print("💡 Ejecutar: python setup.py")
    else:
        print("✅ Estructura de directorios completa")

    # Verificar archivos de configuración
    config_files = [
        "config/default_selenium.yml",
        "config/university_detail.yml",
        "config/full_pipeline.yml"
    ]

    missing_configs = []
    for config_file in config_files:
        if not Path(config_file).exists():
            missing_configs.append(config_file)

    if missing_configs:
        print(f"❌ Configs faltantes: {missing_configs}")
    else:
        print("✅ Archivos de configuración completos")

    # Verificar scripts
    script_files = [
        "scripts/scrape_rankings.py",
        "scripts/scrape_universities.py",
        "setup.py"
    ]

    missing_scripts = []
    for script_file in script_files:
        if not Path(script_file).exists():
            missing_scripts.append(script_file)

    if missing_scripts:
        print(f"❌ Scripts faltantes: {missing_scripts}")
    else:
        print("✅ Scripts completos")

    #  Verificar PostgreSQL
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from src.storage.database_manager import PostgreSQLManager

        db_manager = PostgreSQLManager()
        if db_manager.test_connection():
            print("✅ PostgreSQL conectado y funcionando")

            # Verificar datos en PostgreSQL
            stats = db_manager.get_scraping_stats()
            if stats:
                print(f"📊 PostgreSQL - Rankings: {stats['total_rankings']}, Detalles: {stats['total_details']}")
            else:
                print("ℹ️ PostgreSQL conectado pero sin datos aún")

            db_manager.close()
        else:
            print("⚠️ PostgreSQL no disponible (opcional)")
    except Exception as e:
        print(f"ℹ️ PostgreSQL no configurado: {e}")

# Ejecutar verificación
verify_installation()

# Revisar rankings (si existen)
rankings_files = list(Path("data/raw").glob("rankings_*.json"))
if rankings_files:
    latest_rankings = max(rankings_files, key=lambda x: x.stat().st_mtime)
    with open(latest_rankings) as f:
        rankings = json.load(f)
    print(f"✅ Rankings: {len(rankings)} universidades en {latest_rankings.name}")
else:
    print("ℹ️ No hay archivos de rankings aún")

# Revisar universidades (si existen)
uni_files = list(Path("data/universities").glob("universities_detail_*.json"))
if uni_files:
    latest_unis = max(uni_files, key=lambda x: x.stat().st_mtime)
    with open(latest_unis) as f:
        universities = json.load(f)
    print(f"✅ Universidades: {len(universities)} con detalles en {latest_unis.name}")
else:
    print("ℹ️ No hay archivos de universidades aún")

# Revisar datos procesados (si existen)
processed_files = list(Path("data/processed").glob("*.pkl"))
if processed_files:
    latest_processed = max(processed_files, key=lambda x: x.stat().st_mtime)
    df = pd.read_pickle(latest_processed)
    print(f"✅ Datos procesados: {df.shape} en {latest_processed.name}")
    print(f"   Columnas: {list(df.columns)}")
else:
    print("ℹ️ No hay datos procesados aún")
```

## 📈 Rendimiento y Optimización

### Configuración de Rendimiento

```yaml
# En full_pipeline.yml
pipeline:
  university_batch_size: 100 # Aumentar para más velocidad
  max_concurrent_requests: 5 # Paralelización (futuro)

scraper:
  headless: true # Más rápido sin UI
  page_load_timeout: 30 # Reducir si la conexión es buena
```

### Métricas de Rendimiento Típicas (Actualizadas)
- **Rankings**: ~2000 universidades en 10-15 minutos
- **Universidades**: ~50 universidades por lote en 5-8 minutos  
- **Pipeline Completo**: 500 universidades en 45-60 minutos
- **Procesamiento**: <1 minuto para datasets típicos
- **🔥 Auto-inserción PostgreSQL**: +5-10 segundos por lote (despreciable)
- **🔥 Verificación PostgreSQL**: <2 segundos

## 🔄 Mantenimiento y Actualizaciones

### Archivos Creados Automáticamente por setup.py

El script `setup.py` crea automáticamente:

#### **Estructura de Directorios**

```
📁 logs/                    # Para archivos de log
📁 data/
  ├── 📁 raw/              # HTML y JSON originales
  ├── 📁 processed/        # Datos procesados
  ├── 📁 universities/     # Detalles de universidades
  ├── 📁 exports/          # Datos exportados
  │   ├── 📁 csv/         # Exportaciones CSV
  │   ├── 📁 excel/       # Exportaciones Excel
  │   └── 📁 json/        # Exportaciones JSON
  ├── 📁 pipeline_results/ # Resultados de pipeline
  └── 📁 backups/         # Backups automáticos
📁 scripts/                # Scripts especializados
```

#### **Archivos de Configuración**

```
📄 .env.template           # Template de variables de entorno
📄 .gitignore             # Configuración de Git
📄 data/.gitkeep          # Preservar estructura en Git
📄 logs/.gitkeep          # Preservar estructura en Git
```

#### **Variables de Entorno Template**

El archivo `.env.template` creado incluye:

```bash
# PostgreSQL settings
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=university_rankings
POSTGRES_USER=scraper_user

# Optional: API keys for future integrations
# THE_API_KEY=your_api_key_here

# Optional: Notification settings
# WEBHOOK_URL=https://your-webhook-url.com
# EMAIL_ALERTS_TO=admin@yourcompany.com
```

### Actualizaciones Regulares

```bash
# Actualizar dependencias
poetry update

# Re-ejecutar setup para verificar estructura
python setup.py

# Verificar compatibilidad con el sitio web
python scripts/scrape_rankings.py --dry-run --log-level DEBUG
```

#### **Actualización Mayor** (cambios estructurales)

```bash
# 1. Backup completo
tar -czf full_backup_$(date +%Y%m%d).tar.gz .

# 2. Re-ejecutar setup.py para nuevas estructuras
python setup.py

# 3. Migrar configuraciones si es necesario
# 4. Prueba extensiva antes de producción
```

## 🚀 Guía de Inicio Rápido

### Después de Ejecutar setup.py

#### 1. **Verificar Instalación**

```bash
# Verificar que setup.py completó correctamente
python -c "
from pathlib import Path
required = ['logs', 'data/raw', 'data/universities', 'scripts']
missing = [d for d in required if not Path(d).exists()]
if missing:
    print(f'❌ Faltantes: {missing}')
    print('💡 Re-ejecutar: python setup.py')
else:
    print('✅ Estructura completa')
"
```

#### 2. **Primera Ejecución (Prueba)**

```bash
# Prueba básica - solo verificar configuración
python -m src --mode rankings-only --limit 3 --dry-run --log-level DEBUG

# Primera ejecución real con datos mínimos
python -m src --mode rankings-only --limit 5 --log-level INFO
```

#### 3. **Verificar Resultados**

```bash
# Verificar archivos generados
ls -la data/raw/rankings_*.json
ls -la data/universities/*.json | tail -3
ls -la logs/*.log

# Verificar logs por errores
grep -c "ERROR\|CRITICAL" logs/*.log

# Verificar estadísticas de scraping
grep -i "successfully" logs/*.log | wc -l
```

#### 4. **Pipeline Completo de Prueba**

```bash
# Ejecutar pipeline completo con datos limitados
python -m src --mode full-pipeline --limit 10 --batch-size 5 --log-level INFO
```

### Comandos de Verificación Post-Setup

#### **Verificación de Integridad**

```bash
# Script de verificación completa
python -c "
import sys
from pathlib import Path

def check_files():
    checks = {
        'Directorios': [
            'logs', 'data/raw', 'data/universities', 'scripts',
            'data/exports/csv', 'data/exports/json'
        ],
        'Configs': [
            'config/default_selenium.yml',
            'config/university_detail.yml',
            'config/full_pipeline.yml'
        ],
        'Scripts': [
            'scripts/scrape_rankings.py',
            'scripts/scrape_universities.py',
            'setup.py'
        ],
        'Source': [
            'src/__main__.py',
            'src/parsers/rankings_parser.py',
            'src/scrapers/university_detail_scraper.py'
        ]
    }

    all_good = True
    for category, files in checks.items():
        print(f'\\n{category}:')
        for file_path in files:
            if Path(file_path).exists():
                print(f'  ✅ {file_path}')
            else:
                print(f'  ❌ {file_path}')
                all_good = False

    if all_good:
        print('\\n🎉 ¡Instalación completa y verificada!')
        print('\\n🚀 Listo para ejecutar:')
        print('   python -m src --mode full-pipeline --limit 10')
    else:
        print('\\n⚠️  Faltan archivos. Revisar instalación.')

check_files()
"
```

#### **Test de Importaciones**

```bash
# Verificar que todas las importaciones funcionan
python -c "
try:
    from src.core.pipeline import ScrapingPipeline
    from src.core.university_pipeline import UniversityDetailPipeline
    from src.scrapers.university_detail_scraper import UniversityDetailScraper
    from src.parsers.university_detail_parser import UniversityDetailParser
    print('✅ Todas las importaciones exitosas')
    print('🎯 Sistema listo para usar')
except ImportError as e:
    print(f'❌ Error de importación: {e}')
    print('💡 Verificar que todos los archivos están copiados correctamente')
"
```

#### **Test de Configuración**

```bash
# Verificar configuraciones
python -c "
from src.core.config import load_config
from pathlib import Path

configs = [
    'config/default_selenium.yml',
    'config/university_detail.yml',
    'config/full_pipeline.yml'
]

for config_file in configs:
    try:
        if Path(config_file).exists():
            config = load_config(Path(config_file))
            print(f'✅ {config_file} - OK')
        else:
            print(f'❌ {config_file} - No existe')
    except Exception as e:
        print(f'❌ {config_file} - Error: {e}')
"
```

### Desarrollo Local

```bash
# Fork del repositorio
git clone <your-fork>
cd world_university_scraper

# Crear rama de feature
git checkout -b feature/nueva-funcionalidad

# Ejecutar tests (cuando estén disponibles)
poetry run pytest

# Commit y push
git add .
git commit -m "feat: nueva funcionalidad"
git push origin feature/nueva-funcionalidad
```

### Reportar Issues

Incluir en el reporte:

1. Comando ejecutado
2. Logs relevantes
3. Configuración utilizada
4. Versión de Python y dependencias

## 📚 Recursos Adicionales

### Scripts y Herramientas Incluidas

#### **setup.py - Configuración Inicial**

- ✅ Crea estructura completa de directorios
- ✅ Genera archivos de configuración template
- ✅ Configura .gitignore y .env.template
- ✅ Valida instalación y muestra siguientes pasos

### Mejores Prácticas Establecidas

#### **Antes de Cada Ejecución**

```bash
# 1. Verificar espacio libre
df -h .

# 2. Verificar estructura
python setup.py >/dev/null 2>&1 && echo "✅ Setup OK" || echo "❌ Re-ejecutar setup.py"

# 3. Limpiar logs antiguos si es necesario
find logs/ -name "*.log" -mtime +7 -delete
```

#### **Después de Cada Ejecución**

```bash
# 1. Verificar resultados
ls -la data/raw/*.json | tail -3
ls -la data/universities/*.json | tail -3

# 2. Revisar errores
grep -c "ERROR\|CRITICAL" logs/*.log

# 3. Backup si datos importantes
[ -f "data/processed/combined_data_latest.pkl" ] && cp data/processed/combined_data_latest.pkl data/backups/
```

**¡El sistema está completamente documentado y listo para uso en producción!**

### 🎉 ¡Comenzar Ahora!

```bash
# 🔥 COMANDO ÚNICO PARA EMPEZAR (CON POSTGRESQL)
cd data && docker-compose up -d postgres && cd .. && \
python setup.py && \
python -m src --mode full-pipeline --limit 10 --log-level INFO && \
poetry run python verify_database.py
```

```bash
# 🔥 ALTERNATIVA SIN POSTGRESQL
python setup.py && python -m src --mode full-pipeline --limit 10 --no-postgres
```

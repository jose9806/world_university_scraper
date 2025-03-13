# University Rankings Scraper

A comprehensive web scraping project for extracting, processing, and analyzing Times Higher Education World University Rankings data.

## Project Overview

This project scrapes data from the [Times Higher Education World University Rankings](https://www.timeshighereducation.com/world-university-rankings/latest/world-ranking#!/length/-1/sort_by/rank/sort_order/asc/cols/scores) website, processes the data, and exports it in various formats. It follows best practices for Python projects, including:

- Modular architecture with clear separation of concerns
- Comprehensive error handling and logging
- Configurable pipeline for data extraction and processing
- Robust testing framework
- Modern dependency management with Poetry

## Architecture

This project is structured following a pipeline architecture with these main components:

1. **Scrapers**: Responsible for fetching raw data from the web
2. **Parsers**: Extract structured data from the raw HTML
3. **Processors**: Clean, transform, and enhance the data
4. **Exporters**: Convert the processed data to various output formats
5. **Storage**: Handle data persistence across the pipeline

## Directory Structure

```
university_rankings/
├── .github/                   # GitHub workflows and issue templates
├── config/                    # Configuration files for different environments
├── data/                      # Data storage for the pipeline
│   ├── raw/                   # Raw scraped HTML
│   ├── processed/             # Processed data
│   └── exports/               # Final exported data in various formats
├── logs/                      # Application logs
├── scripts/                   # Utility scripts for setup and execution
├── src/                       # Source code
│   └── university_rankings/   # Main package
│       ├── core/              # Core pipeline components
│       ├── scrapers/          # Web scraping modules
│       ├── parsers/           # HTML/data parsing modules
│       ├── processors/        # Data processing modules
│       ├── exporters/         # Data export modules
│       ├── storage/           # Data storage and persistence
│       └── utils/             # Utility functions and helpers
└── tests/                     # Test suite mirroring the src structure
```

## Component Details

### Core

The core package contains the fundamental components that orchestrate the scraping pipeline:

- **config.py**: Handles configuration loading and validation
- **pipeline.py**: Orchestrates the end-to-end data processing pipeline

### Scrapers

The scrapers handle the retrieval of raw data from websites:

- **base_scraper.py**: Abstract base class with common functionality
- **rankings_scraper.py**: Specific implementation for THE rankings

Features:
- Configurable request delays to respect website terms
- Automatic retries with exponential backoff
- Rotating user agents to avoid detection
- Session management for efficient connections

### Parsers

Parsers extract structured data from the raw HTML:

- **base_parser.py**: Common parsing functionality
- **rankings_parser.py**: Extracts university ranking information

Features:
- Robust HTML parsing with BeautifulSoup
- Structured data extraction with error handling
- Clean transformation of text data to appropriate types

### Processors

Processors handle data cleaning, transformation, and enrichment:

- **data_processor.py**: Processes university rankings data

Features:
- Missing value handling
- Data type conversion
- Computed columns and derived metrics
- Data validation and consistency checks

### Exporters

Exporters convert processed data to various output formats:

- **base_exporter.py**: Common export functionality
- **csv_exporter.py**: CSV format export
- **json_exporter.py**: JSON format export
- **excel_exporter.py**: Excel format export with formatting

Features:
- Factory pattern for selecting appropriate exporter
- Configurable output formatting
- Optimized for different use cases

### Storage

Storage components handle data persistence throughout the pipeline:

- **file_storage.py**: File-based storage for all data stages

Features:
- Consistent file naming with timestamps
- Directory organization by data stage
- Error handling and validation

### Utils

Utility modules provide common functionality across the project:

- **http.py**: HTTP request utilities with retry logic
- **exceptions.py**: Custom exception classes

## Installation and Setup

### Prerequisites

- Python 3.9 or higher
- [Poetry](https://python-poetry.org/) for dependency management

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/university_rankings.git
   cd university_rankings
   ```

2. Run the setup script:
   ```bash
   ./scripts/setup.sh
   ```

   This script will:
   - Check if Poetry is installed and install it if needed
   - Install all project dependencies
   - Create and activate a virtual environment

3. Alternatively, you can manually set up the project:
   ```bash
   # Install dependencies
   poetry install
   
   # Activate the virtual environment
   poetry shell
   ```

## Configuration

The project uses YAML configuration files located in the `config/` directory:

- **default.yml**: Base configuration with default values
- **development.yml**: Development environment configuration
- **production.yml**: Production environment configuration

You can customize these files or create new ones for different environments.

### Configuration Options

```yaml
# Example configuration options
scraper:
  url: "https://www.timeshighereducation.com/world-university-rankings/latest/world-ranking#!/length/-1/sort_by/rank/sort_order/asc/cols/scores"
  request_delay: 3  # Seconds between requests
  max_retries: 3
  timeout: 30  # Request timeout in seconds

parser:
  use_lxml: true

processor:
  missing_values_strategy: "zero"  # Options: zero, mean, median

export:
  formats: ["csv", "json", "excel"]

storage:
  base_path: "data"
```

## Usage

### Running the Scraper

Use the provided script to run the scraper:

```bash
./scripts/run_scraper.sh --config config/production.yml --log-level INFO
```

Or run it directly using Poetry:

```bash
poetry run python -m university_rankings --config config/production.yml --log-level INFO
```

### Command-line Options

- `--config`: Path to the configuration file (default: `config/default.yml`)
- `--log-level`: Logging level (default: `INFO`)

## Testing

The project includes a comprehensive test suite using pytest. Tests mirror the structure of the source code:

```
tests/
├── test_core/          # Tests for core modules
├── test_scrapers/      # Tests for scrapers
├── test_parsers/       # Tests for parsers
├── test_processors/    # Tests for data processors
├── test_exporters/     # Tests for exporters
├── test_storage/       # Tests for storage
└── test_utils/         # Tests for utilities
```

Run the tests with:

```bash
poetry run pytest
```

Or with coverage:

```bash
poetry run pytest --cov=src --cov-report=html
```

## Development Guidelines

### Adding New Features

1. Create a new module in the appropriate directory
2. Add corresponding tests
3. Update documentation as needed
4. Make sure all tests pass before submitting

### Code Style

This project follows these style guidelines:

- Code formatting with Black
- Import sorting with isort
- Linting with flake8
- Type annotations with Python's typing module
- Comprehensive docstrings in Google style

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality. Install them with:

```bash
pre-commit install
```

## Handling Dynamic Content

Since the THE World University Rankings page is dynamic and uses JavaScript to load content, this project employs several strategies:

1. **Selenium WebDriver**: For pages where JavaScript execution is necessary, the project can use Selenium to render the full page content before extraction.

2. **API Identification**: The scraper attempts to identify any underlying APIs that the website uses to load data and directly accesses those when possible.

3. **Pagination Handling**: For rankings that span multiple pages, the scraper intelligently navigates through all pages to collect complete data.


## Error Handling and Resilience

The project implements robust error handling:

- Comprehensive exception hierarchy for specific error types
- Automatic retries with exponential backoff
- Detailed logging for troubleshooting
- Graceful degradation when parts of the pipeline fail


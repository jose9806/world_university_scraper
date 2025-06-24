#!/usr/bin/env python3
"""Setup script for World University Scraper."""

import sys
from pathlib import Path



def create_directories():
    """Create necessary directories."""
    directories = [
        "logs",
        "data/raw",
        "data/processed",
        "data/universities",
        "data/exports/csv",
        "data/exports/excel",
        "data/exports/json",
        "data/pipeline_results",
        "data/backups",
        "scripts",
    ]

    print("Creating directory structure...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created: {directory}")


def copy_scripts():
    """Copy script files to scripts directory."""
    script_files = [
        ("scripts/scrape_rankings.py", "Script for rankings scraping"),
        ("scripts/scrape_universities.py", "Script for university details scraping"),
    ]

    print("\nScript files to copy:")
    for file_path, description in script_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path} - {description}")
        else:
            print(f"  ✗ {file_path} - {description} (MISSING - copy manually)")


def copy_configs():
    """Copy configuration files."""
    config_files = [
        ("config/default_selenium.yml", "Main rankings configuration"),
        ("config/university_detail.yml", "University details configuration"),
        ("config/full_pipeline.yml", "Complete pipeline configuration"),
    ]

    print("\nConfiguration files to copy:")
    for file_path, description in config_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path} - {description}")
        else:
            print(f"  ✗ {file_path} - {description} (MISSING - copy manually)")


def update_source_files():
    """Show which source files need to be updated."""
    source_updates = [
        (
            "src/parsers/rankings_parser.py",
            "Enhanced parser with URL extraction and error handling",
        ),
        (
            "src/scrapers/university_detail_scraper.py",
            "New scraper for individual universities",
        ),
        (
            "src/parsers/university_detail_parser.py",
            "New parser for university details",
        ),
        ("src/core/university_pipeline.py", "New pipeline for university processing"),
        ("src/__main__.py", "Updated main orchestrator"),
        ("src/scrapers/__init__.py", "Updated imports"),
        ("src/parsers/__init__.py", "Updated imports"),
    ]

    print("\nSource files to update:")
    for file_path, description in source_updates:
        print(f"  → {file_path} - {description}")


def create_env_template():
    """Create .env template file."""
    env_template = """# Environment variables for World University Scraper

# PostgreSQL settings (if using database export)
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
"""

    env_file = Path(".env.template")
    if not env_file.exists():
        with open(env_file, "w") as f:
            f.write(env_template)
        print(f"\n✓ Created: .env.template")
        print("  Copy to .env and update with your actual values")
    else:
        print(f"\n✓ .env.template already exists")


def create_gitignore():
    """Create/update .gitignore file."""
    gitignore_content = """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Data files
data/
logs/
*.html
*.json
*.pkl
*.csv
*.xlsx
*.parquet

# Environment variables
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Selenium
geckodriver.log
selenium.log

# Jupyter Notebook
.ipynb_checkpoints

# pytest
.pytest_cache/

# Coverage reports
htmlcov/
.coverage
.coverage.*
coverage.xml
"""

    gitignore_file = Path(".gitignore")
    with open(gitignore_file, "w") as f:
        f.write(gitignore_content)
    print(f"\n✓ Created/Updated: .gitignore")


def show_next_steps():
    """Show next steps after setup."""
    next_steps = """
🎉 SETUP COMPLETE!

📋 NEXT STEPS:

1. Copy the provided code files:
   • Copy rankings_parser.py to src/parsers/rankings_parser.py (REPLACE existing)
   • Copy university_detail_scraper.py to src/scrapers/
   • Copy university_detail_parser.py to src/parsers/
   • Copy university_pipeline.py to src/core/
   • Copy __main__.py to src/__main__.py (REPLACE existing)
   • Copy script files to scripts/ directory
   • Copy config files to config/ directory

2. Update import files:
   • Update src/scrapers/__init__.py with new imports
   • Update src/parsers/__init__.py with new imports

3. Install/update dependencies (if needed):
   poetry install
   poetry update

4. Test the installation:
   python -m src --mode rankings-only --limit 5 --log-level DEBUG

5. Run your first complete pipeline:
   python -m src --mode full-pipeline --limit 10

📖 DOCUMENTATION:
   • Read the updated README.md for detailed usage examples
   • Check config files for customization options
   • Review logs/ directory for debugging information

🔧 CONFIGURATION:
   • Copy .env.template to .env and update values
   • Customize config/*.yml files as needed
   • Adjust batch sizes and timeouts for your environment

🚀 READY TO GO!
   Your scraper is now ready for production use.
"""
    print(next_steps)


def main():
    """Run the setup process."""
    print("=" * 60)
    print("🔧 WORLD UNIVERSITY SCRAPER SETUP")
    print("=" * 60)

    try:
        create_directories()
        copy_scripts()
        copy_configs()
        update_source_files()
        create_env_template()
        create_gitignore()
        show_next_steps()

    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

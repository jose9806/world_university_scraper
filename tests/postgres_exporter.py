# tests/test_exporters/test_postgres_exporter.py
"""Tests for PostgreSQL exporter."""

import os
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.exporters.postgres_exporter import PostgresExporter
from src.utils.exceptions import ExporterException


@pytest.fixture
def db_config():
    """Sample database configuration for testing."""
    return {
        "database": {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "user": "test_user",
            "password": "test_password",
            "schema": "public",
            "table_name": "test_rankings",
            "if_exists": "replace",
            "create_schema": True,
            "manage_schema": True
        }
    }


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing."""
    return pd.DataFrame({
        "rank": [1, 2, 3],
        "name": ["University A", "University B", "University C"],
        "country": ["Country A", "Country B", "Country C"],
        "overall_score": [95.5, 94.3, 93.1],
        "teaching_score": [92.3, 91.0, 89.5]
    })


class TestPostgresExporter:
    """Test cases for PostgresExporter class."""

    @patch('src.exporters.postgres_exporter.create_engine')
    def test_init_creates_engine(self, mock_create_engine, db_config):
        """Test that the exporter initializes and creates an engine."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        exporter = PostgresExporter(db_config)
        
        assert exporter.engine == mock_engine
        mock_create_engine.assert_called_once()
    
    @patch('src.exporters.postgres_exporter.create_engine')
    def test_init_handles_engine_creation_error(self, mock_create_engine, db_config):
        """Test that the exporter handles engine creation errors."""
        mock_create_engine.side_effect = Exception("Connection error")
        
        with pytest.raises(ExporterException) as excinfo:
            PostgresExporter(db_config)
        
        assert "Failed to create database engine" in str(excinfo.value)
    
    def test_get_connection_string_with_valid_config(self, db_config):
        """Test that a valid connection string is generated from config."""
        with patch('src.exporters.postgres_exporter.create_engine'):
            exporter = PostgresExporter(db_config)
            conn_string = exporter._get_connection_string()
            
            assert "postgresql://" in conn_string
            assert "test_user" in conn_string
            assert "test_password" in conn_string
            assert "localhost" in conn_string
            assert "5432" in conn_string
            assert "test_db" in conn_string
    
    def test_get_connection_string_with_missing_params(self):
        """Test that missing connection parameters raise an exception."""
        config = {
            "database": {
                "host": "localhost",
                # Missing database, user, and password
            }
        }
        
        with patch('src.exporters.postgres_exporter.create_engine'):
            exporter = PostgresExporter(config)
            
            with pytest.raises(ExporterException) as excinfo:
                exporter._get_connection_string()
            
            assert "Missing required database connection parameters" in str(excinfo.value)
    
    def test_get_sanitized_connection_string(self, db_config):
        """Test that the sanitized connection string hides the password."""
        with patch('src.exporters.postgres_exporter.create_engine'):
            exporter = PostgresExporter(db_config)
            sanitized = exporter._get_sanitized_connection_string()
            
            assert "postgresql://" in sanitized
            assert "test_user" in sanitized
            assert "******" in sanitized  # Password should be masked
            assert "test_password" not in sanitized
    
    @patch('src.exporters.postgres_exporter.create_engine')
    def test_export_success(self, mock_create_engine, db_config, sample_dataframe):
        """Test successful export to database."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        # Mock DataFrame's to_sql method
        with patch.object(pd.DataFrame, 'to_sql', return_value=None) as mock_to_sql:
            exporter = PostgresExporter(db_config)
            
            # Mock _ensure_table_schema method
            with patch.object(exporter, '_ensure_table_schema', return_value=None) as mock_ensure:
                result = exporter.export(sample_dataframe)
                
                assert result is True
                mock_to_sql.assert_called_once()
                mock_ensure.assert_called_once()
    
    @patch('src.exporters.postgres_exporter.create_engine')
    def test_export_sql_error(self, mock_create_engine, db_config, sample_dataframe):
        """Test handling of SQLAlchemy errors during export."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        # Mock DataFrame's to_sql method to raise an exception
        with patch.object(pd.DataFrame, 'to_sql', side_effect=SQLAlchemyError("Database error")):
            exporter = PostgresExporter(db_config)
            
            # Mock _ensure_table_schema method
            with patch.object(exporter, '_ensure_table_schema', return_value=None):
                with pytest.raises(ExporterException) as excinfo:
                    exporter.export(sample_dataframe)
                
                assert "Database export failed" in str(excinfo.value)
    
    @patch('src.exporters.postgres_exporter.create_engine')
    @patch('src.exporters.postgres_exporter.inspect')
    @patch('src.exporters.postgres_exporter.MetaData')
    @patch('src.exporters.postgres_exporter.Table')
    def test_ensure_table_schema_table_exists(self, mock_table, mock_metadata, mock_inspect, 
                                             mock_create_engine, db_config, sample_dataframe):
        """Test that _ensure_table_schema checks if table exists."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.has_table.return_value = True
        
        exporter = PostgresExporter(db_config)
        exporter._ensure_table_schema(sample_dataframe, "test_rankings", "public")
        
        mock_inspector.has_table.assert_called_once_with("test_rankings", schema="public")
        mock_table.assert_not_called()  # Table should not be created if it exists
    
    @patch('src.exporters.postgres_exporter.create_engine')
    @patch('src.exporters.postgres_exporter.inspect')
    @patch('src.exporters.postgres_exporter.MetaData')
    @patch('src.exporters.postgres_exporter.Table')
    @patch('src.exporters.postgres_exporter.Column')
    def test_ensure_table_schema_create_table(self, mock_column, mock_table, mock_metadata, 
                                             mock_inspect, mock_create_engine, 
                                             db_config, sample_dataframe):
        """Test table creation when it doesn't exist."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.has_table.return_value = False
        
        mock_metadata_instance = MagicMock()
        mock_metadata.return_value = mock_metadata_instance
        
        exporter = PostgresExporter(db_config)
        exporter._ensure_table_schema(sample_dataframe, "test_rankings", "public")
        
        mock_inspector.has_table.assert_called_once_with("test_rankings", schema="public")
        mock_table.assert_called_once()  # Table should be created
        mock_metadata_instance.create_all.assert_called_once_with(mock_engine)
    
    @patch('src.exporters.postgres_exporter.create_engine')
    @patch('src.exporters.postgres_exporter.inspect')
    def test_ensure_table_schema_sql_error(self, mock_inspect, mock_create_engine, 
                                          db_config, sample_dataframe):
        """Test handling of SQLAlchemy errors during schema creation."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.has_table.side_effect = SQLAlchemyError("Schema error")
        
        exporter = PostgresExporter(db_config)
        
        with pytest.raises(ExporterException) as excinfo:
            exporter._ensure_table_schema(sample_dataframe, "test_rankings", "public")
        
        assert "Failed to create table schema" in str(excinfo.value)
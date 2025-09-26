#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFITEC.AI - DATABASE UTILITIES
==============================

Módulo centralizado para utilidades de base de datos.
Elimina duplicación de código DB en el sistema.
"""

from __future__ import annotations
import sqlite3
import logging
from typing import Any, Dict, List, Optional, Union, Iterator
from contextlib import contextmanager
from config import DB_PATH

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Database Connection Management
# ----------------------------------------------------------------------------

@contextmanager
def get_db_connection(db_path: Optional[str] = None,
                      timeout: float = 30.0,
                      row_factory: bool = True) -> Iterator[sqlite3.Connection]:
    """
    Context manager for database connections.
    
    Args:
        db_path: Path to database file (default: config.DB_PATH)
        timeout: Connection timeout in seconds
        row_factory: Whether to use Row factory for dict-like access
    
    Yields:
        sqlite3.Connection: Database connection
    """
    path = db_path or DB_PATH
    conn = None
    
    try:
        conn = sqlite3.connect(path, timeout=timeout)
        if row_factory:
            conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_query(query: str,
                  params: Union[tuple, dict, None] = None,
                  db_path: Optional[str] = None,
                  fetch_one: bool = False,
                  fetch_all: bool = True) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
    """
    Execute a SELECT query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters
        db_path: Database path (optional)
        fetch_one: Return single row as dict
        fetch_all: Return all rows as list of dicts (default)
    
    Returns:
        Query results or None
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.execute(query, params or ())
            
            if fetch_one:
                row = cursor.fetchone()
                return dict(row) if row else None
            elif fetch_all:
                return [dict(row) for row in cursor.fetchall()]
            else:
                return None
                
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise


def execute_update(query: str,
                   params: Union[tuple, dict, None] = None,
                   db_path: Optional[str] = None) -> int:
    """
    Execute an INSERT, UPDATE, or DELETE query.
    
    Args:
        query: SQL query string
        params: Query parameters
        db_path: Database path (optional)
    
    Returns:
        Number of affected rows
    """
    try:
        with get_db_connection(db_path, row_factory=False) as conn:
            cursor = conn.execute(query, params or ())
            conn.commit()
            return cursor.rowcount
            
    except Exception as e:
        logger.error(f"Update execution failed: {e}")
        raise


def execute_many(query: str,
                 param_list: List[Union[tuple, dict]],
                 db_path: Optional[str] = None) -> int:
    """
    Execute a query with multiple parameter sets.
    
    Args:
        query: SQL query string
        param_list: List of parameter tuples/dicts
        db_path: Database path (optional)
    
    Returns:
        Number of affected rows
    """
    try:
        with get_db_connection(db_path, row_factory=False) as conn:
            cursor = conn.executemany(query, param_list)
            conn.commit()
            return cursor.rowcount
            
    except Exception as e:
        logger.error(f"Batch execution failed: {e}")
        raise


# ----------------------------------------------------------------------------
# Common Database Operations
# ----------------------------------------------------------------------------

def table_exists(table_name: str, db_path: Optional[str] = None) -> bool:
    """Check if a table exists in the database."""
    query = """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """
    result = execute_query(query, (table_name,), db_path, fetch_one=True)
    return result is not None


def get_table_info(table_name: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get column information for a table."""
    query = f"PRAGMA table_info({table_name})"
    return execute_query(query, db_path=db_path) or []


def get_table_count(table_name: str, db_path: Optional[str] = None) -> int:
    """Get row count for a table."""
    query = f"SELECT COUNT(*) as count FROM {table_name}"
    result = execute_query(query, db_path=db_path, fetch_one=True)
    return result['count'] if result else 0


def vacuum_database(db_path: Optional[str] = None) -> None:
    """VACUUM the database to reclaim space."""
    try:
        with get_db_connection(db_path, row_factory=False) as conn:
            conn.execute("VACUUM")
            conn.commit()
    except Exception as e:
        logger.error(f"Database VACUUM failed: {e}")
        raise


# ----------------------------------------------------------------------------
# Database Schema Utilities
# ----------------------------------------------------------------------------

def create_table_if_not_exists(table_name: str,
                               schema: str,
                               db_path: Optional[str] = None) -> bool:
    """
    Create table if it doesn't exist.
    
    Args:
        table_name: Name of the table
        schema: SQL CREATE TABLE statement (without CREATE TABLE part)
        db_path: Database path (optional)
    
    Returns:
        True if table was created, False if already existed
    """
    if table_exists(table_name, db_path):
        return False
    
    query = f"CREATE TABLE {table_name} {schema}"
    execute_update(query, db_path=db_path)
    return True


def drop_table_if_exists(table_name: str, db_path: Optional[str] = None) -> bool:
    """
    Drop table if it exists.
    
    Returns:
        True if table was dropped, False if didn't exist
    """
    if not table_exists(table_name, db_path):
        return False
    
    query = f"DROP TABLE {table_name}"
    execute_update(query, db_path=db_path)
    return True


# ----------------------------------------------------------------------------
# Transaction Management
# ----------------------------------------------------------------------------

@contextmanager
def db_transaction(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    """
    Context manager for database transactions.
    Automatically commits on success, rolls back on exception.
    """
    with get_db_connection(db_path, row_factory=False) as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# ----------------------------------------------------------------------------
# Database Health Checks
# ----------------------------------------------------------------------------

def check_database_health(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform basic database health checks.
    
    Returns:
        Dictionary with health check results
    """
    try:
        with get_db_connection(db_path) as conn:
            # Basic connectivity test
            conn.execute("SELECT 1")
            
            # Get database info
            cursor = conn.execute("PRAGMA database_list")
            db_info = cursor.fetchall()
            
            # Get schema version if available
            try:
                cursor = conn.execute("PRAGMA user_version")
                schema_version = cursor.fetchone()[0]
            except:
                schema_version = None
            
            return {
                "status": "healthy",
                "database_info": [dict(row) for row in db_info],
                "schema_version": schema_version,
                "check_time": __import__("time").time()
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "check_time": __import__("time").time()
        }

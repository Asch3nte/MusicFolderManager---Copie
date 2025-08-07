#!/usr/bin/env python3
"""
Module de backup basé sur une base de données
Ne duplique pas les fichiers, mais trace toutes les opérations
"""

from .backup_database import get_backup_database, record_file_operation
from .backup_handler import (
    record_metadata_change,
    record_file_move, 
    record_file_organization,
    get_backup_statistics,
    get_file_history
)

__all__ = [
    'get_backup_database',
    'record_file_operation',
    'record_metadata_change',
    'record_file_move',
    'record_file_organization', 
    'get_backup_statistics',
    'get_file_history'
]

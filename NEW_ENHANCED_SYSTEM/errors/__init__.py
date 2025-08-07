"""
Module de gestion centralisée des erreurs et messages
Respecte les principes de la POO pour une architecture maintenable
"""

from .error_manager import ErrorManager, ErrorType, MessageLevel, get_error_manager
from .error_codes import ErrorCodes
from .exceptions import *

__all__ = [
    'ErrorManager',
    'ErrorType', 
    'MessageLevel',
    'get_error_manager',
    'ErrorCodes',
    'AudioProcessingError',
    'ConfigurationError',
    'FileAccessError',
    'MetadataError',
    'NetworkError',
    'OrganizationError',
    'MusicFolderManagerError'
]

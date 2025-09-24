"""Dependency Injection module for enhanced DevClaude_bot architecture."""

from .container import ApplicationContainer, initialize_di, shutdown_di, get_di_container

__all__ = [
    "ApplicationContainer",
    "initialize_di",
    "shutdown_di",
    "get_di_container",
]
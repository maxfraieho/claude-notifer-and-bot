"""
Health Service for DI Container monitoring.

Provides health checks for all major components managed by the DI container.
"""

from typing import Dict, Any
import asyncio
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)


class HealthService:
    """
    Health monitoring service for DI-managed components.

    Monitors the health of all major application components and provides
    comprehensive health status information.
    """

    def __init__(self, storage, claude_integration, security):
        self.storage = storage
        self.claude_integration = claude_integration
        self.security = security
        self._last_check = None
        self._cached_status = None

    async def get_health_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get comprehensive health status of all components."""
        now = datetime.utcnow()

        # Use cached status if recent (< 30 seconds) and not forced refresh
        if (
            not force_refresh
            and self._cached_status
            and self._last_check
            and (now - self._last_check).total_seconds() < 30
        ):
            return self._cached_status

        logger.info("Performing health check")

        status = {
            "overall": "healthy",
            "timestamp": now.isoformat(),
            "components": {},
            "metrics": {},
        }

        # Check storage health
        try:
            storage_healthy = await self._check_storage_health()
            status["components"]["storage"] = "healthy" if storage_healthy else "degraded"
        except Exception as e:
            logger.error("Storage health check failed", error=str(e))
            status["components"]["storage"] = "error"

        # Check Claude integration health
        try:
            claude_healthy = await self._check_claude_health()
            status["components"]["claude"] = "healthy" if claude_healthy else "degraded"
        except Exception as e:
            logger.error("Claude health check failed", error=str(e))
            status["components"]["claude"] = "error"

        # Check security components health
        try:
            security_healthy = await self._check_security_health()
            status["components"]["security"] = "healthy" if security_healthy else "degraded"
        except Exception as e:
            logger.error("Security health check failed", error=str(e))
            status["components"]["security"] = "error"

        # Determine overall status
        component_statuses = list(status["components"].values())
        if "error" in component_statuses:
            status["overall"] = "error"
        elif "degraded" in component_statuses:
            status["overall"] = "degraded"

        # Add metrics
        status["metrics"] = await self._collect_metrics()

        # Cache results
        self._cached_status = status
        self._last_check = now

        logger.info("Health check completed", overall_status=status["overall"])
        return status

    async def _check_storage_health(self) -> bool:
        """Check storage component health."""
        try:
            if hasattr(self.storage, 'health_check'):
                return await self.storage.health_check()
            else:
                # Basic connection check
                if hasattr(self.storage, 'db_manager'):
                    async with self.storage.db_manager.get_connection() as conn:
                        await conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("Storage health check error", error=str(e))
            return False

    async def _check_claude_health(self) -> bool:
        """Check Claude integration health."""
        try:
            if hasattr(self.claude_integration, 'health_check'):
                return await self.claude_integration.health_check()
            else:
                # Basic availability check
                return self.claude_integration.is_available()
        except Exception as e:
            logger.error("Claude health check error", error=str(e))
            return False

    async def _check_security_health(self) -> bool:
        """Check security components health."""
        try:
            # Check if auth manager is functional
            if hasattr(self.security, 'is_healthy'):
                return await self.security.is_healthy()
            else:
                # Basic functionality check
                return self.security is not None
        except Exception as e:
            logger.error("Security health check error", error=str(e))
            return False

    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect performance and usage metrics."""
        metrics = {
            "uptime_seconds": 0,  # Would need to track from startup
            "memory_usage_mb": 0,  # Could use psutil
            "active_sessions": 0,
            "error_rate": 0.0,
        }

        try:
            # Collect session metrics if available
            if hasattr(self.storage, 'get_session_count'):
                metrics["active_sessions"] = await self.storage.get_session_count()

            # Additional metrics can be added here

        except Exception as e:
            logger.error("Metrics collection error", error=str(e))

        return metrics

    async def get_component_details(self, component_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific component."""
        details = {
            "name": component_name,
            "status": "unknown",
            "details": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            if component_name == "storage":
                details.update(await self._get_storage_details())
            elif component_name == "claude":
                details.update(await self._get_claude_details())
            elif component_name == "security":
                details.update(await self._get_security_details())
            else:
                details["status"] = "unknown"
                details["details"] = {"error": f"Unknown component: {component_name}"}

        except Exception as e:
            logger.error("Component details collection failed", component=component_name, error=str(e))
            details["status"] = "error"
            details["details"] = {"error": str(e)}

        return details

    async def _get_storage_details(self) -> Dict[str, Any]:
        """Get detailed storage information."""
        return {
            "status": "healthy" if await self._check_storage_health() else "error",
            "details": {
                "type": "SQLite",
                "connected": True,  # Could check actual connection
            }
        }

    async def _get_claude_details(self) -> Dict[str, Any]:
        """Get detailed Claude integration information."""
        return {
            "status": "healthy" if await self._check_claude_health() else "error",
            "details": {
                "mode": "CLI" if not hasattr(self.claude_integration, 'use_sdk') else "SDK",
                "available": self.claude_integration.is_available() if hasattr(self.claude_integration, 'is_available') else True,
            }
        }

    async def _get_security_details(self) -> Dict[str, Any]:
        """Get detailed security information."""
        return {
            "status": "healthy" if await self._check_security_health() else "error",
            "details": {
                "auth_enabled": True,
                "providers": "whitelist+token",  # Could be more dynamic
            }
        }
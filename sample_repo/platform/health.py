"""
Platform health module.

Handles deployment health checks, readiness probes, and service monitoring.
Mert is actively working on this module.

This module has NO dependency on shared.user or any user data model.
A change to User.email has zero impact here.
"""
import time


# Service start time for uptime tracking
_SERVICE_START = time.time()


def health_check() -> dict:
    """
    Return the current health status of the service.
    Used by load balancers and orchestration platforms.
    """
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _SERVICE_START, 2),
        "service": "novahb-platform",
    }


def readiness_probe() -> dict:
    """
    Return readiness status.
    Checks whether dependent services (DB, cache) are reachable.
    """
    # Simplified: always ready in this demo
    return {
        "ready": True,
        "checks": {
            "database": "ok",
            "cache": "ok",
        },
    }


def liveness_probe() -> bool:
    """Return True if the service is alive."""
    return True

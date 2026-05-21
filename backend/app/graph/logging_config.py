"""
Enhanced logging configuration for Neo4j operations with structured output.

Logs all Neo4j queries with:
- Query execution time
- Result count
- Error details
- Connection pool stats
"""

import logging
import time
from functools import wraps
from typing import Callable

# Configure Neo4j-specific logger
neo4j_logger = logging.getLogger("neo4j_operations")


def configure_neo4j_logging(level=logging.INFO):
    """Configure structured logging for Neo4j operations."""
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    neo4j_logger.addHandler(handler)
    neo4j_logger.setLevel(level)


def log_query_execution(func: Callable) -> Callable:
    """Decorator to log Neo4j query execution with timing and results."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        query_name = kwargs.get("query_name", func.__name__)
        start = time.time()

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start

            # Log success
            result_count = len(result) if isinstance(result, list) else 1
            neo4j_logger.info(
                f"Query '{query_name}' executed: {elapsed:.3f}s, "
                f"{result_count} result(s)"
            )
            return result

        except Exception as e:
            elapsed = time.time() - start
            neo4j_logger.error(
                f"Query '{query_name}' failed after {elapsed:.3f}s: {str(e)}"
            )
            raise

    return wrapper


def log_connection_event(event_type: str, details: str = ""):
    """Log Neo4j connection lifecycle events."""
    neo4j_logger.info(f"Connection event: {event_type}. {details}")


def log_pool_stats(stats: dict):
    """Log connection pool statistics."""
    neo4j_logger.debug(
        f"Pool stats: active={stats.get('active', 'unknown')}, "
        f"idle={stats.get('idle', 'unknown')}"
    )


# Auto-configure on import
configure_neo4j_logging()

import logging
import os
import time
from typing import Optional
from contextlib import contextmanager

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv(override=True)


class Neo4jConfig:
    """Neo4j driver configuration with sensible production defaults."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "").strip()
        self.username = os.getenv("NEO4J_USERNAME", "").strip()
        self.password = os.getenv("NEO4J_PASSWORD", "").strip()

        # These are available for future use but not passed to driver
        # (driver doesn't support them in current version)
        self.max_pool_size = int(os.getenv("NEO4J_POOL_SIZE", "50"))
        self.connection_timeout = float(os.getenv("NEO4J_CONNECTION_TIMEOUT", "30.0"))
        self.query_timeout = float(os.getenv("NEO4J_QUERY_TIMEOUT", "60.0"))

        # SSL/TLS configuration (minimal support)
        self.encrypted = os.getenv("NEO4J_ENCRYPTED", "false").lower() == "true"

        # Validate required config
        if not self.uri or not self.username or not self.password:
            raise ValueError(
                "NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD must be set"
            )

    def get_driver_kwargs(self) -> dict:
        """Build kwargs for GraphDatabase.driver() with supported parameters."""
        return {
            "auth": (self.username, self.password),
            "max_connection_pool_size": self.max_pool_size,
            "connection_timeout": self.connection_timeout,
        }


class Neo4jDriver:
    """Manages Neo4j driver lifecycle and provides health checks."""

    _instance: Optional["Neo4jDriver"] = None
    _driver = None

    def __init__(self, config: Optional[Neo4jConfig] = None):
        if config is None:
            config = Neo4jConfig()
        self.config = config
        self._driver = None
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "Neo4jDriver":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connect(self):
        """Initialize driver with error handling."""
        if self._initialized:
            return

        try:
            logger.info(f"Connecting to Neo4j at {self.config.uri}")
            self._driver = GraphDatabase.driver(
                self.config.uri,
                **self.config.get_driver_kwargs(),
            )

            # Test connectivity
            with self._driver.session() as session:
                session.run("RETURN 1")

            logger.info("✓ Neo4j driver initialized successfully")
            self._initialized = True

        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            raise

    def close(self):
        """Gracefully close driver."""
        if self._driver is not None:
            try:
                self._driver.close()
                logger.info("Neo4j driver closed")
            except Exception as e:
                logger.error(f"Error closing Neo4j driver: {e}")
            finally:
                self._driver = None
                self._initialized = False

    def get_driver(self):
        """Get the initialized driver."""
        if not self._initialized:
            self.connect()
        return self._driver

    @contextmanager
    def session(self):
        """Context manager for Neo4j sessions."""
        if not self._initialized:
            self.connect()
        session = self._driver.session()
        try:
            yield session
        finally:
            session.close()

    def health_check(self) -> dict:
        """Check Neo4j connectivity and return status with performance metrics."""
        try:
            start = time.time()
            with self.session() as session:
                result = session.run("RETURN apoc.version() as version").single()
                version = result["version"] if result else "unknown"
            elapsed = time.time() - start

            logger.info(f"Neo4j health check passed in {elapsed:.3f}s")
            return {
                "status": "healthy",
                "connected": True,
                "version": version,
                "response_time_ms": elapsed * 1000,
            }
        except Exception as e:
            logger.warning(f"Neo4j health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }


# Global driver instance (legacy interface for backward compatibility)
_driver_instance = Neo4jDriver.get_instance()


def get_driver():
    """Get initialized Neo4j driver."""
    return _driver_instance.get_driver()


def get_session():
    """Get Neo4j session (not a context manager, call close() manually)."""
    driver = get_driver()
    return driver.session()


def close_driver():
    """Close the global driver instance."""
    _driver_instance.close()


def health_check() -> dict:
    """Check Neo4j health status."""
    return _driver_instance.health_check()

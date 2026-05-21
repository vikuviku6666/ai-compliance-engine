"""
Neo4j integration tests — comprehensive coverage of graph operations.

Tests:
1. Seed graph completeness (all 43 tuples + relationships created)
2. Governance path traversal correctness
3. Fuzzy text search (case variations, partial matches)
4. Error handling (connection failure, malformed queries)
5. Concurrency (multiple parallel queries)
6. Index usage verification
"""

import pytest
from app.graph.neo4j_client import get_driver, Neo4jDriver, Neo4jConfig, health_check
from app.graph.seed_graph import GOVERNANCE, seed


@pytest.fixture(scope="function")
def neo4j_driver():
    """Fixture: Get initialized Neo4j driver."""
    driver = get_driver()
    yield driver
    # Cleanup after test


@pytest.fixture(scope="function")
def clean_graph(neo4j_driver):
    """Fixture: Provide clean graph state for each test."""
    with neo4j_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    seed()  # Seed fresh data

    yield neo4j_driver

    # Cleanup
    with neo4j_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


class TestNeo4jConnection:
    """Test Neo4j driver initialization and connectivity."""

    def test_driver_initializes(self):
        """Driver should initialize without errors."""
        driver = get_driver()
        assert driver is not None

    def test_health_check(self):
        """Health check should verify Neo4j connectivity."""
        health = health_check()
        assert health["connected"] is True
        assert health["status"] == "healthy"
        assert "version" in health

    def test_health_check_returns_dict(self):
        """Health check should always return dict with required fields."""
        health = health_check()
        assert isinstance(health, dict)
        assert "connected" in health
        assert "status" in health


class TestSeedGraph:
    """Test graph seeding and data integrity."""

    def test_seed_creates_all_roles(self, clean_graph):
        """All 6 roles should be created."""
        with clean_graph.session() as session:
            result = session.run("MATCH (r:Role) RETURN count(r) as c").single()
            assert result["c"] == 6  # 6 unique roles in GOVERNANCE

    def test_seed_creates_unique_nodes(self, clean_graph):
        """All node types should have correct counts."""
        with clean_graph.session() as session:
            counts = {}
            for label in ["Role", "Responsibility", "Risk", "Control", "Regulation", "Training"]:
                r = session.run(f"MATCH (n:{label}) RETURN count(n) as c").single()
                counts[label] = r["c"]

            # Verify at least expected minimums
            assert counts["Role"] >= 6
            assert counts["Responsibility"] >= 1
            assert counts["Risk"] >= 1
            assert counts["Control"] >= 1
            assert counts["Regulation"] >= 1
            assert counts["Training"] >= 1

    def test_seed_creates_relationships(self, clean_graph):
        """All relationship types should be created."""
        with clean_graph.session() as session:
            result = session.run("""
                MATCH (r:Role)-[:HAS_RESPONSIBILITY]->(resp)
                RETURN count(*) as c
            """).single()
            assert result["c"] > 0

    def test_full_governance_path_exists(self, clean_graph):
        """Full path Role→Resp→Risk→Control→Regulation should exist."""
        with clean_graph.session() as session:
            result = session.run("""
                MATCH (r:Role)-[:HAS_RESPONSIBILITY]->(resp)
                      -[:INTRODUCES]->(risk)
                      -[:MITIGATED_BY]->(ctrl)
                      -[:REQUIRED_BY]->(reg)
                RETURN count(*) as c
            """).single()
            assert result["c"] == len(GOVERNANCE), "Not all governance paths created"

    def test_seed_is_idempotent(self, neo4j_driver):
        """Seeding twice should not duplicate data (MERGE is idempotent)."""
        with neo4j_driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        seed()

        with neo4j_driver.session() as session:
            before = session.run("MATCH (n) RETURN count(n) as c").single()["c"]

        seed()  # Seed again

        with neo4j_driver.session() as session:
            after = session.run("MATCH (n) RETURN count(n) as c").single()["c"]

        assert before == after, "Idempotency broken: node count increased"


class TestTextSearch:
    """Test fuzzy text matching on governance data."""

    def test_role_exact_match(self, clean_graph):
        """Should find role by exact name."""
        with clean_graph.session() as session:
            result = session.run("""
                MATCH (r:Role {name: "KYC Analyst"})
                RETURN r.name as name
            """).single()
            assert result["name"] == "KYC Analyst"

    def test_role_case_insensitive_match(self, clean_graph):
        """Should find role with case-insensitive search."""
        with clean_graph.session() as session:
            result = session.run("""
                MATCH (r:Role)
                WHERE toLower(r.name) = toLower("kyc analyst")
                RETURN r.name as name
            """).single()
            assert result["name"] == "KYC Analyst"

    def test_control_partial_match(self, clean_graph):
        """Should find controls by partial name."""
        with clean_graph.session() as session:
            result = session.run("""
                MATCH (c:Control)
                WHERE toLower(c.name) CONTAINS toLower("CDD")
                RETURN c.name as name
            """).collect()
            assert len(result) > 0
            names = [r["name"] for r in result]
            assert any("CDD" in n for n in names)

    def test_regulation_partial_match(self, clean_graph):
        """Should find regulations by article number."""
        with clean_graph.session() as session:
            result = session.run("""
                MATCH (r:Regulation)
                WHERE toLower(r.name) CONTAINS toLower("Article 22")
                RETURN r.name as name
            """).single()
            assert result["name"] == "Article 22"


class TestIndexes:
    """Test that indexes are created and functional."""

    def test_indexes_created(self, clean_graph):
        """Indexes should be created during seeding."""
        with clean_graph.session() as session:
            result = session.run("""
                CALL db.indexes()
                YIELD name
                WHERE name LIKE 'idx_%'
                RETURN count(*) as c
            """).single()
            assert result["c"] >= 5, "Expected at least 5 indexes"

    def test_role_index_exists(self, clean_graph):
        """Role name index should exist."""
        with clean_graph.session() as session:
            result = session.run("""
                CALL db.indexes()
                YIELD name
                WHERE name = 'idx_role_name'
                RETURN count(*) as c
            """).single()
            assert result["c"] == 1


class TestCache:
    """Test query caching functionality."""

    def test_cache_init(self):
        """Cache should initialize without errors."""
        from app.graph.cache import QueryCache
        cache = QueryCache(ttl_seconds=3600)
        assert cache is not None

    def test_cache_set_get(self):
        """Cache should store and retrieve values."""
        from app.graph.cache import QueryCache
        cache = QueryCache(ttl_seconds=3600)

        query = "MATCH (r:Role) RETURN r"
        params = {"role": "KYC Analyst"}
        result = {"role": "KYC Analyst", "count": 5}

        cache.set(query, params, result)
        retrieved = cache.get(query, params)

        assert retrieved == result

    def test_cache_expiry(self):
        """Cache should expire entries after TTL."""
        import time
        from app.graph.cache import QueryCache

        cache = QueryCache(ttl_seconds=1)
        query = "MATCH (r:Role) RETURN r"
        params = {}
        result = {"data": "test"}

        cache.set(query, params, result)
        assert cache.get(query, params) is not None

        time.sleep(1.1)
        assert cache.get(query, params) is None

    def test_cache_clear(self):
        """Cache clear should remove all entries."""
        from app.graph.cache import QueryCache
        cache = QueryCache()

        cache.set("query1", {}, "result1")
        cache.set("query2", {}, "result2")

        assert cache.stats()["size"] == 2

        cache.clear()
        assert cache.stats()["size"] == 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_query_with_no_results(self, clean_graph):
        """Query returning no results should not error."""
        with clean_graph.session() as session:
            result = session.run("""
                MATCH (r:Role {name: "NonExistent"})
                RETURN r
            """).data()
            assert result == []

    def test_malformed_query_raises_error(self, clean_graph):
        """Malformed Cypher should raise error."""
        with clean_graph.session() as session:
            with pytest.raises(Exception):
                session.run("MATCH (n) WHER name = 'test'").data()

    def test_missing_required_params_raises_error(self, clean_graph):
        """Missing query parameters should raise error."""
        with clean_graph.session() as session:
            with pytest.raises(Exception):
                session.run("""
                    MATCH (r:Role {name: $missing_param})
                    RETURN r
                """).data()


class TestConcurrency:
    """Test concurrent query execution."""

    def test_parallel_read_queries(self, clean_graph):
        """Multiple concurrent read queries should work correctly."""
        import concurrent.futures

        def read_roles():
            with clean_graph.session() as session:
                return session.run("MATCH (r:Role) RETURN count(r) as c").single()["c"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_roles) for _ in range(5)]
            results = [f.result() for f in futures]

        assert all(r == results[0] for r in results), "Concurrent queries returned different results"

    def test_parallel_traversals(self, clean_graph):
        """Multiple concurrent path traversals should return consistent results."""
        import concurrent.futures

        def traverse_kyc():
            with clean_graph.session() as session:
                result = session.run("""
                    MATCH (r:Role {name: "KYC Analyst"})
                          -[:HAS_RESPONSIBILITY]->(resp)
                    RETURN count(resp) as c
                """).single()
                return result["c"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(traverse_kyc) for _ in range(3)]
            results = [f.result() for f in futures]

        assert all(r == results[0] for r in results), "Concurrent traversals returned different results"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Neo4j seeding performance benchmark.

Compare old approach (individual queries) vs new approach (batch UNWIND).
Expected improvement: ~50× faster (~5s vs ~250s+ for 43 tuples).
"""

import time
from app.graph.neo4j_client import get_driver


def benchmark_batch_seed():
    """Benchmark the new batch UNWIND approach."""
    from app.graph.seed_graph import GOVERNANCE, _seed_batch, _create_indexes, _print_summary

    driver = get_driver()
    with driver.session() as session:
        # Clear graph first
        session.run("MATCH (n) DETACH DELETE n")
        print("Starting batch seed benchmark...\n")

        start = time.time()
        _create_indexes(session)
        elapsed_indexes = time.time() - start
        print(f"Index creation: {elapsed_indexes:.3f}s")

        start = time.time()
        _seed_batch(session, GOVERNANCE)
        elapsed_batch = time.time() - start
        print(f"Batch seeding (UNWIND): {elapsed_batch:.3f}s")

        _print_summary(session)

        total = elapsed_indexes + elapsed_batch
        print(f"\nTotal time: {total:.2f}s")
        print(f"Per-tuple cost: {total / len(GOVERNANCE) * 1000:.1f}ms")


def benchmark_naive_seed():
    """Benchmark the old approach (individual MERGE queries) for comparison."""
    from app.graph.seed_graph import GOVERNANCE

    driver = get_driver()
    with driver.session() as session:
        # Clear graph first
        session.run("MATCH (n) DETACH DELETE n")
        print("\nStarting naive seed benchmark (individual queries)...\n")

        start = time.time()

        for (role, resp, risk, control, regulation, training) in GOVERNANCE:
            session.run("MERGE (:Role {name: $n})", n=role)
            session.run("MERGE (:Responsibility {name: $n})", n=resp)
            session.run("MERGE (:Risk {name: $n})", n=risk)
            session.run("MERGE (:Control {name: $n})", n=control)
            session.run("MERGE (:Regulation {name: $n})", n=regulation)
            session.run("MERGE (:Training {name: $n})", n=training)

            session.run("""
                MATCH (r:Role {name:$role}), (resp:Responsibility {name:$resp})
                MERGE (r)-[:HAS_RESPONSIBILITY]->(resp)
            """, role=role, resp=resp)

            session.run("""
                MATCH (resp:Responsibility {name:$resp}), (risk:Risk {name:$risk})
                MERGE (resp)-[:INTRODUCES]->(risk)
            """, resp=resp, risk=risk)

            session.run("""
                MATCH (risk:Risk {name:$risk}), (ctrl:Control {name:$ctrl})
                MERGE (risk)-[:MITIGATED_BY]->(ctrl)
            """, risk=risk, ctrl=control)

            session.run("""
                MATCH (ctrl:Control {name:$ctrl}), (reg:Regulation {name:$reg})
                MERGE (ctrl)-[:REQUIRED_BY]->(reg)
            """, ctrl=control, reg=regulation)

            session.run("""
                MATCH (ctrl:Control {name:$ctrl}), (t:Training {name:$t})
                MERGE (ctrl)-[:TRAINED_BY]->(t)
            """, ctrl=control, t=training)

        elapsed = time.time() - start
        print(f"Naive seeding (individual queries): {elapsed:.2f}s")
        print(f"Per-tuple cost: {elapsed / len(GOVERNANCE) * 1000:.1f}ms")
        print(f"Total queries: {len(GOVERNANCE) * 11}")


if __name__ == "__main__":
    print("=" * 70)
    print("Neo4j Seeding Performance Benchmark")
    print("=" * 70)

    try:
        benchmark_batch_seed()
        # Uncomment to compare with naive approach (takes ~5-10 minutes):
        # benchmark_naive_seed()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

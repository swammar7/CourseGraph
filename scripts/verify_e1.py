"""Read-only E1 evidence: on-disk SHACL plus negative control mutations.

Run from repository root:
    python scripts/verify_e1.py --course SEN0414
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from rdflib import Graph, Literal
from rdflib.namespace import RDF, XSD

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from coursegraph.graph_store import CG, GraphStore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify existing CourseGraph RDF and SHACL")
    parser.add_argument("--graph", default="data/graph.ttl", help="Existing RDF/Turtle file")
    parser.add_argument("--course", default="SEN0414", help="Course ID to query")
    parser.add_argument("--topic", default=None, help="Optional SKOS topic label")
    args = parser.parse_args()

    graph_path = Path(args.graph)
    if not graph_path.is_file():
        print(f"ERROR: RDF graph not found: {graph_path}")
        return 2

    store = GraphStore(graph_path=graph_path)
    graph = store.load_graph()
    conforms, report = store.validate_graph(graph)
    print(f"Saved graph SHACL conforms: {conforms}")
    if not conforms:
        print(report)
        return 1

    chunks = store.get_course_chunks(args.course, topic=args.topic)
    print(f"SPARQL chunks: {len(chunks)} (course={args.course}, topic={args.topic or '*'})")
    for row in chunks[:3]:
        print(f"  {row['filename']} p.{row['page_number']}, chunk={row['chunk_index']}, embedding_dim={len(row['embedding'])}")

    first_chunk = next(graph.subjects(RDF.type, CG.Chunk), None)
    if first_chunk is None:
        print("ERROR: No chunks found for SHACL negative controls")
        return 2

    for name, mutate in [
        ("missing chunk page number", lambda g: g.remove((first_chunk, CG.chunkPageNumber, None))),
        ("blank chunk text", lambda g: g.set((first_chunk, CG.text, Literal("", datatype=XSD.string)))),
        ("whitespace-only chunk text", lambda g: g.set((first_chunk, CG.text, Literal("  \t", datatype=XSD.string)))),
    ]:
        # Clone into memory; the source .ttl is NEVER overwritten.
        broken = Graph()
        for triple in graph:
            broken.add(triple)
        mutate(broken)
        negative_conforms, _ = store.validate_graph(broken)
        print(f"SHACL rejects {name}: {not negative_conforms}")
        if negative_conforms:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

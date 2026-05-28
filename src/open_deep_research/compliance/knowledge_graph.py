"""Lightweight compliance knowledge graph for relationship navigation."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from open_deep_research.compliance.schemas import KnowledgeEdge, KnowledgeNode


DEFAULT_GRAPH_DIR = Path("data/compliance_graph")


class ComplianceKnowledgeGraph:
    """A lightweight knowledge graph for compliance relationships.

    Stores nodes and edges in JSONL files for easy versioning and human review.
    Supports navigation between clauses, processes, procedures, records, and departments.
    """

    def __init__(
        self,
        nodes: list[KnowledgeNode] | None = None,
        edges: list[KnowledgeEdge] | None = None,
    ):
        self.nodes = nodes or []
        self.edges = edges or []

        self._nodes_by_id: dict[str, KnowledgeNode] = {n.node_id: n for n in self.nodes}
        self._edges_by_source: dict[str, list[KnowledgeEdge]] = defaultdict(list)
        self._edges_by_target: dict[str, list[KnowledgeEdge]] = defaultdict(list)
        self._edges_by_type: dict[str, list[KnowledgeEdge]] = defaultdict(list)

        for edge in self.edges:
            self._edges_by_source[edge.source_id].append(edge)
            self._edges_by_target[edge.target_id].append(edge)
            self._edges_by_type[edge.relation_type].append(edge)

    @classmethod
    def from_directory(cls, directory: str | Path | None = None) -> ComplianceKnowledgeGraph:
        """Load a knowledge graph from a directory containing nodes.jsonl and edges.jsonl."""

        graph_dir = Path(directory) if directory else DEFAULT_GRAPH_DIR
        nodes_path = graph_dir / "nodes.jsonl"
        edges_path = graph_dir / "edges.jsonl"

        nodes = _load_jsonl(nodes_path, KnowledgeNode) if nodes_path.exists() else []
        edges = _load_jsonl(edges_path, KnowledgeEdge) if edges_path.exists() else []

        return cls(nodes, edges)

    def save(self, directory: str | Path | None = None) -> None:
        """Save the knowledge graph to a directory."""

        graph_dir = Path(directory) if directory else DEFAULT_GRAPH_DIR
        graph_dir.mkdir(parents=True, exist_ok=True)

        _save_jsonl(graph_dir / "nodes.jsonl", self.nodes)
        _save_jsonl(graph_dir / "edges.jsonl", self.edges)

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Get a node by its ID."""

        return self._nodes_by_id.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> list[KnowledgeNode]:
        """Get all nodes of a specific type."""

        return [n for n in self.nodes if n.node_type == node_type]

    def get_related_nodes(
        self,
        node_id: str,
        relation_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[tuple[KnowledgeNode, KnowledgeEdge]]:
        """Get nodes related to the given node.

        Args:
            node_id: The source node ID
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of (node, edge) tuples
        """

        results: list[tuple[KnowledgeNode, KnowledgeEdge]] = []

        if direction in ("outgoing", "both"):
            for edge in self._edges_by_source.get(node_id, []):
                if relation_type and edge.relation_type != relation_type:
                    continue
                target = self._nodes_by_id.get(edge.target_id)
                if target:
                    results.append((target, edge))

        if direction in ("incoming", "both"):
            for edge in self._edges_by_target.get(node_id, []):
                if relation_type and edge.relation_type != relation_type:
                    continue
                source = self._nodes_by_id.get(edge.source_id)
                if source:
                    results.append((source, edge))

        return results

    def get_clause_processes(self, standard: str, clause_id: str) -> list[KnowledgeNode]:
        """Get processes that a clause applies to."""

        clause_node_id = f"clause:{standard}:{clause_id}"
        related = self.get_related_nodes(clause_node_id, "applies_to", "outgoing")
        return [node for node, edge in related if node.node_type == "process"]

    def get_process_procedures(self, process_id: str) -> list[KnowledgeNode]:
        """Get procedures that control a process."""

        related = self.get_related_nodes(process_id, "controlled_by", "outgoing")
        return [node for node, edge in related if node.node_type == "procedure"]

    def get_procedure_records(self, procedure_id: str) -> list[KnowledgeNode]:
        """Get records produced by a procedure."""

        related = self.get_related_nodes(procedure_id, "produces", "outgoing")
        return [node for node, edge in related if node.node_type == "record"]

    def get_evidence_chain(
        self,
        standard: str,
        clause_id: str,
    ) -> dict[str, list[KnowledgeNode]]:
        """Get the full evidence chain for a clause: processes -> procedures -> records."""

        processes = self.get_clause_processes(standard, clause_id)
        procedures: list[KnowledgeNode] = []
        records: list[KnowledgeNode] = []

        for process in processes:
            procs = self.get_process_procedures(process.node_id)
            procedures.extend(procs)
            for proc in procs:
                recs = self.get_procedure_records(proc.node_id)
                records.extend(recs)

        return {
            "processes": processes,
            "procedures": procedures,
            "records": records,
        }

    def find_files_for_topic(self, topic_keywords: list[str]) -> list[str]:
        """Find relevant files based on topic keywords using graph navigation."""

        matching_files: set[str] = set()
        keywords_lower = [k.lower() for k in topic_keywords]

        for node in self.nodes:
            label_lower = node.label.lower()
            if any(kw in label_lower for kw in keywords_lower):
                if node.node_type == "procedure":
                    related = self.get_related_nodes(node.node_id, "produces", "outgoing")
                    for record, _ in related:
                        if "file_path" in record.metadata:
                            matching_files.add(record.metadata["file_path"])

                if "file_path" in node.metadata:
                    matching_files.add(node.metadata["file_path"])

        return sorted(matching_files)

    def add_clause_process_mapping(
        self,
        standard: str,
        clause_id: str,
        process_id: str,
        process_label: str,
    ) -> None:
        """Add a mapping between a clause and a process."""

        clause_node_id = f"clause:{standard}:{clause_id}"
        if not self.get_node(clause_node_id):
            self.nodes.append(KnowledgeNode(
                node_id=clause_node_id,
                node_type="clause",
                label=f"{standard} {clause_id}",
                metadata={"standard": standard, "clause_id": clause_id},
            ))

        if not self.get_node(process_id):
            self.nodes.append(KnowledgeNode(
                node_id=process_id,
                node_type="process",
                label=process_label,
            ))

        edge = KnowledgeEdge(
            source_id=clause_node_id,
            target_id=process_id,
            relation_type="applies_to",
            metadata={"standard": standard, "clause_id": clause_id},
        )
        self.edges.append(edge)
        self._edges_by_source[clause_node_id].append(edge)
        self._edges_by_target[process_id].append(edge)
        self._edges_by_type["applies_to"].append(edge)

    def add_process_procedure_mapping(
        self,
        process_id: str,
        procedure_id: str,
        procedure_label: str,
        file_path: str | None = None,
    ) -> None:
        """Add a mapping between a process and a procedure."""

        if not self.get_node(procedure_id):
            metadata = {}
            if file_path:
                metadata["file_path"] = file_path
            self.nodes.append(KnowledgeNode(
                node_id=procedure_id,
                node_type="procedure",
                label=procedure_label,
                metadata=metadata,
            ))

        edge = KnowledgeEdge(
            source_id=process_id,
            target_id=procedure_id,
            relation_type="controlled_by",
        )
        self.edges.append(edge)
        self._edges_by_source[process_id].append(edge)
        self._edges_by_target[procedure_id].append(edge)
        self._edges_by_type["controlled_by"].append(edge)

    def add_procedure_record_mapping(
        self,
        procedure_id: str,
        record_id: str,
        record_label: str,
        file_path: str | None = None,
    ) -> None:
        """Add a mapping between a procedure and a record."""

        if not self.get_node(record_id):
            metadata = {}
            if file_path:
                metadata["file_path"] = file_path
            self.nodes.append(KnowledgeNode(
                node_id=record_id,
                node_type="record",
                label=record_label,
                metadata=metadata,
            ))

        edge = KnowledgeEdge(
            source_id=procedure_id,
            target_id=record_id,
            relation_type="produces",
        )
        self.edges.append(edge)
        self._edges_by_source[procedure_id].append(edge)
        self._edges_by_target[record_id].append(edge)
        self._edges_by_type["produces"].append(edge)

    def get_statistics(self) -> dict[str, int]:
        """Get statistics about the knowledge graph."""

        stats = {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
        }

        for node_type in ["clause", "process", "procedure", "record", "department", "risk", "control"]:
            count = len([n for n in self.nodes if n.node_type == node_type])
            stats[f"nodes_{node_type}"] = count

        for rel_type in self._edges_by_type:
            stats[f"edges_{rel_type}"] = len(self._edges_by_type[rel_type])

        return stats


def _load_jsonl(path: Path, model_class) -> list:
    """Load objects from a JSONL file."""

    objects = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    objects.append(model_class.model_validate_json(line))
                except Exception:
                    continue
    return objects


def _save_jsonl(path: Path, objects: list) -> None:
    """Save objects to a JSONL file."""

    with path.open("w", encoding="utf-8") as f:
        for obj in objects:
            f.write(obj.model_dump_json() + "\n")


def build_initial_compliance_graph() -> ComplianceKnowledgeGraph:
    """Build an initial compliance graph with common ISO 13485 relationships."""

    graph = ComplianceKnowledgeGraph()

    common_mappings = [
        {
            "clause": ("ISO 13485:2016", "4.2.4"),
            "process": ("document_control", "文件控制"),
            "procedures": [
                ("doc_mgmt_procedure", "文件管理程序", "TP_001"),
            ],
            "records": [
                ("doc_approval_record", "文件审批记录"),
                ("doc_distribution_record", "文件分发记录"),
            ],
        },
        {
            "clause": ("ISO 13485:2016", "4.2.5"),
            "process": ("record_control", "记录控制"),
            "procedures": [
                ("record_mgmt_procedure", "记录管理程序"),
            ],
            "records": [
                ("retention_schedule", "记录保存期限表"),
                ("disposal_record", "记录处置记录"),
            ],
        },
        {
            "clause": ("ISO 13485:2016", "8.5.2"),
            "process": ("capa_process", "CAPA流程"),
            "procedures": [
                ("capa_procedure", "CAPA程序", "TP_020"),
                ("q_reporting_procedure", "Q-Reporting程序"),
            ],
            "records": [
                ("capa_report", "CAPA报告"),
                ("root_cause_analysis", "根因分析记录"),
                ("effectiveness_check", "有效性验证记录"),
            ],
        },
        {
            "clause": ("ISO 13485:2016", "8.2.4"),
            "process": ("internal_audit", "内部审核"),
            "procedures": [
                ("audit_procedure", "内部审核程序", "TP_032"),
            ],
            "records": [
                ("audit_plan", "审核计划"),
                ("audit_report", "审核报告"),
                ("ncr_report", "不符合项报告"),
            ],
        },
        {
            "clause": ("ISO 13485:2016", "7.4.1"),
            "process": ("supplier_mgmt", "供应商管理"),
            "procedures": [
                ("supplier_eval_procedure", "供应商评价程序", "TP_038"),
            ],
            "records": [
                ("supplier_evaluation", "供应商评价记录"),
                ("supplier_audit_report", "供应商审核报告"),
            ],
        },
    ]

    for mapping in common_mappings:
        standard, clause_id = mapping["clause"]
        process_id, process_label = mapping["process"]

        graph.add_clause_process_mapping(standard, clause_id, process_id, process_label)

        for proc_id, proc_label, *file_path in mapping["procedures"]:
            graph.add_process_procedure_mapping(
                process_id, proc_id, proc_label,
                file_path[0] if file_path else None,
            )

        for record_id, record_label in mapping["records"]:
            graph.add_procedure_record_mapping(
                mapping["procedures"][0][0], record_id, record_label,
            )

    return graph

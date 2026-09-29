"""Текстовый рендер карточки узла (v0). HTML-дашборд — следующий этап."""
from __future__ import annotations

from scc.geometry.context import context_density
from scc.models import ContextNode


def render_node_card(node: ContextNode, d_before: float | None = None, recommendation: str = "") -> str:
    c = node.context
    lines = [
        node.id,
        "─" * 32,
        f"Context:     {c.total:,} tokens",
        f"  useful {c.useful:,} · redundant {c.redundant:,} · stale {c.stale:,} · conflict {c.conflict:,}",
        f"Density ρ:   {context_density(c):.2f}",
        (f"Goal dist:   {d_before:.2f} → {node.goal_distance:.2f}" if d_before is not None
         else f"Goal dist:   {node.goal_distance:.2f}"),
        f"Uncertainty: ±{node.uncertainty:.2f}",
        f"Tokens spent:{node.tokens_spent:,}",
    ]
    if recommendation:
        lines.append(f"Recommendation: {recommendation}")
    return "\n".join(lines)

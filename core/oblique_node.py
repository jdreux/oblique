from uuid import uuid4
from typing import Any, Dict, Set


class ObliqueNode:
    """
    Base class for all nodes in the Oblique patch DAG (inputs, modules, processing operators).
    Provides unique ID, parent/child management, and node info for graph construction.
    """

    def __init__(self) -> None:
        self.id: str = str(uuid4())
        self.parents: Set["ObliqueNode"] = set()
        self.children: Set["ObliqueNode"] = set()

    def add_parent(self, parent: "ObliqueNode") -> None:
        """Add a parent node (upstream in the DAG)."""
        self.parents.add(parent)
        parent.children.add(self)

    def add(self, child: "ObliqueNode") -> "ObliqueNode":
        """Add a child node (downstream in the DAG)."""
        self.children.add(child)
        if self not in child.parents:
            child.parents.add(self)
        return self

    def get_node_info(self) -> Dict[str, Any]:
        """Return basic info for graph introspection."""
        return {
            "id": self.id,
            "type": self.__class__.__name__,
            "parents": [p.id for p in self.parents],
            "children": [c.id for c in self.children],
        }

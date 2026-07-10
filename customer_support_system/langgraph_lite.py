"""
langgraph_lite.py
A minimal LangGraph-compatible StateGraph implementation.
Supports: add_node, add_edge, add_conditional_edges,
          set_entry_point, compile, invoke — same API as LangGraph.
"""

END = "__end__"


class _CompiledGraph:
    def __init__(self, entry, nodes, edges, conditional_edges):
        self._entry = entry
        self._nodes = nodes           # name -> callable
        self._edges = edges           # name -> name (fixed)
        self._cond  = conditional_edges  # name -> (fn, mapping)

    def invoke(self, state: dict) -> dict:
        current = self._entry
        visited = []

        while current != END:
            if current in visited[-10:]:   # simple cycle guard
                break
            visited.append(current)

            # Run the node
            fn = self._nodes.get(current)
            if fn is None:
                raise ValueError(f"Node '{current}' not found.")
            state = fn(state)

            # Determine next node
            if current in self._cond:
                route_fn, mapping = self._cond[current]
                key = route_fn(state)
                nxt = mapping.get(key)
                if nxt is None:
                    raise ValueError(f"Conditional edge key '{key}' not in mapping for node '{current}'.")
                current = nxt
            elif current in self._edges:
                current = self._edges[current]
            else:
                break   # No outgoing edge → stop

        return state


class StateGraph:
    """Drop-in replacement for langgraph.graph.StateGraph."""

    def __init__(self, schema=None):
        self._nodes = {}
        self._edges = {}
        self._cond  = {}
        self._entry = None

    def add_node(self, name: str, fn):
        self._nodes[name] = fn

    def add_edge(self, src: str, dst: str):
        self._edges[src] = dst

    def add_conditional_edges(self, src: str, route_fn, mapping: dict):
        self._cond[src] = (route_fn, mapping)

    def set_entry_point(self, name: str):
        self._entry = name

    def compile(self):
        return _CompiledGraph(self._entry, self._nodes, self._edges, self._cond)

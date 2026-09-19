from dataclasses import dataclass, field

@dataclass
class Entity:
    """A permanent thing that gets observed over time.

    Entities survive across observations. They can be renamed,
    superseded, or marked dead. They never get overwritten.
    """
    entity_id: str               # stable ID (never changes)
    garden: str                  # which garden
    entity_type: str             # e.g. "chain", "item", "occupation", "task"
    name: str                    # current canonical name
    name_history: list = field(default_factory=list)  # [{name, valid_from, valid_to}]

    # Status
    status: str = "active"       # active, superseded, dead
    superseded_by: str = ""      # entity_id of successor

    # Source
    first_seen: str = ""         # ISO UTC
    last_seen: str = ""          # ISO UTC
    source_ids: list = field(default_factory=list)

    # Metadata
    attributes: dict = field(default_factory=dict)

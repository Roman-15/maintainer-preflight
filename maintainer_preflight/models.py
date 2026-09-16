"""Public result types shared by checks and reporters."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    path: str
    line: int
    message: str
    suggestion: str

    def to_dict(self) -> dict:
        return asdict(self)

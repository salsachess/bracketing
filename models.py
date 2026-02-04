"""
Моделі для жеребкувань: учасники, матчі, раунди, групи.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class BracketType(Enum):
    """Тип сітки (основна / втрати)."""
    UPPER = "upper"
    LOWER = "lower"
    FINAL = "final"


@dataclass
class Participant:
    """Учасник турніру."""
    id: str
    name: str
    seed: Optional[int] = None  # сіяний номер для жеребкування
    country: Optional[str] = None  # країна (для Country Lock / Max 2 per country)

    def __str__(self) -> str:
        return self.name


@dataclass
class Match:
    """Один матч."""
    match_id: str
    participant_a: Optional[Participant] = None
    participant_b: Optional[Participant] = None
    round_index: int = 0
    bracket: BracketType = BracketType.UPPER
    group_id: Optional[str] = None
    leg: int = 1  # для двоматчевих протистоянь: 1 або 2
    winner_advances_to: Optional[str] = None  # match_id наступного матчу
    loser_advances_to: Optional[str] = None  # для lower bracket

    def __str__(self) -> str:
        a = self.participant_a.name if self.participant_a else "?"
        b = self.participant_b.name if self.participant_b else "?"
        return f"{a} vs {b}"

    def str_with_winner_placeholders(
        self, matches_by_id: "dict[str, Match]"
    ) -> str:
        """Як __str__, але для матчів без пар: «Переможець Mx vs Переможець My»."""
        if self.participant_a is not None and self.participant_b is not None:
            return f"{self.participant_a.name} vs {self.participant_b.name}"
        # Знайти матчі, переможці яких грають у цьому
        sources = [
            m for m in matches_by_id.values()
            if m.winner_advances_to == self.match_id
        ]
        sources.sort(key=lambda m: m.match_id)
        if len(sources) >= 2:
            return f"Переможець {sources[0].match_id} vs Переможець {sources[1].match_id}"
        if len(sources) == 1:
            return f"Переможець {sources[0].match_id} vs ?"
        return "? vs ?"


@dataclass
class Group:
    """Група (наприклад у груповому етапі)."""
    group_id: str
    name: str
    participants: list[Participant] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)


@dataclass
class DrawResult:
    """Результат жеребкування: матчі та структура."""
    matches: list[Match] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    rounds: list[list[Match]] = field(default_factory=list)  # матчі по раундах
    description: str = ""

    def _matches_by_id(self) -> dict[str, "Match"]:
        if self.matches:
            return {m.match_id: m for m in self.matches}
        all_m = [m for r in self.rounds for m in r]
        return {m.match_id: m for m in all_m}

    def summary(self) -> str:
        lines = [self.description, ""]
        if self.groups:
            for g in self.groups:
                lines.append(f"Група {g.name}: {', '.join(p.name for p in g.participants)}")
            lines.append("")
        by_id = self._matches_by_id()
        for i, round_matches in enumerate(self.rounds, 1):
            lines.append(f"--- Раунд {i} ---")
            for m in round_matches:
                line = m.str_with_winner_placeholders(by_id)
                lines.append(f"  [{m.match_id}] {line}")
            lines.append("")
        if self.matches and not self.rounds:
            lines.append("--- Усі матчі ---")
            for m in self.matches:
                line = m.str_with_winner_placeholders(by_id)
                lines.append(f"  [{m.match_id}] {line}")
        return "\n".join(lines)

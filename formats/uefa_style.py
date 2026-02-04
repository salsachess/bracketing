"""
Формат на кшталт Ліги чемпіонів УЄФА: груповий етап (колова в групах) + плей-оф нокаут.
"""
from models import Participant, Match, DrawResult, Group
from draw_utils import distribute_into_groups, next_power_of_two
from .round_robin import _round_robin_pairs
from .knockout import _build_single_knockout_bracket


def draw_uefa_style(
    participants: list[Participant],
    num_groups: int = 8,
    advance_per_group: int = 2,
    shuffle_seed: int | None = None,
    seeded: bool = True,
) -> DrawResult:
    """
    Стиль Ліги чемпіонів УЄФА:
    - Груповий етап: учасники розподілені по групах, в кожній групі колова система.
    - З кожної групи виходять advance_per_group (за замовчуванням 2).
    - Плей-оф: нокаут серед команд, що вийшли.

    num_groups: кількість груп (наприклад 8).
    advance_per_group: скільки з кожної групи виходить далі (наприклад 2).
    """
    n = len(participants)
    needed = num_groups * 4  # типова група по 4 команди
    if n < num_groups * 2:
        raise ValueError(f"Потрібно мінімум {num_groups * 2} учасників для {num_groups} груп")

    group_lists = distribute_into_groups(participants, num_groups, seeded=seeded, shuffle_seed=shuffle_seed)
    groups: list[Group] = []
    all_matches: list[Match] = []
    all_rounds: list[list[Match]] = []
    round_offset = 0

    for gi, g_participants in enumerate(group_lists):
        name = chr(ord("A") + gi) if gi < 26 else f"G{gi+1}"
        g = Group(group_id=f"G{gi}", name=name, participants=g_participants)
        g_rounds: list[list[Match]] = []
        g_matches = _round_robin_pairs(g_participants, g_rounds, round_offset=round_offset)
        for m in g_matches:
            m.group_id = g.group_id
        g.matches = g_matches
        num_rounds_in_group = len(g_rounds)
        round_offset += num_rounds_in_group
        groups.append(g)
        all_matches.extend(g_matches)
        all_rounds.extend(g_rounds)

    # Плей-оф: advance_per_group * num_groups = кількість команд
    playoff_count = advance_per_group * num_groups
    # Заглушки учасників плей-оф (реальні будуть визначені після групового етапу)
    # Для жеребкування просто генеруємо сітку нокауту з placeholder-ами
    placeholders = [
        Participant(id=f"PO-{i}", name=f"1-ше/2-ге місце групи (жереб)")
        for i in range(playoff_count)
    ]
    knockout_matches, knockout_rounds = _build_single_knockout_bracket(
        placeholders, shuffle_seed=shuffle_seed, seeded=False
    )
    for m in knockout_matches:
        m.match_id = "PO-" + m.match_id
        m.round_index += round_offset
    all_matches.extend(knockout_matches)
    all_rounds.extend(knockout_rounds)

    return DrawResult(
        matches=all_matches,
        groups=groups,
        rounds=all_rounds,
        description=(
            f"Стиль Ліги чемпіонів УЄФА: {num_groups} груп, по {len(group_lists[0])} в групі, "
            f"по {advance_per_group} виходять у плей-оф, далі нокаут."
        ),
    )

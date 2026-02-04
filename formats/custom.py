"""
Кастомні правила жеребкування: формула задається текстом.

Приклади формул:
  knockout
  double_knockout
  triple_knockout
  round_robin
  double_round_robin
  uefa(8, 2)          — 8 груп, по 2 виходять
  groups(4).round_robin().top(2).knockout()   — групи по 4, колова в групі, топ-2 далі, потім нокаут
  groups(3).round_robin().top(1).knockout()
"""
import re
from typing import Any

from models import Participant, DrawResult
from draw_utils import distribute_into_groups, next_power_of_two
from .knockout import draw_knockout, draw_double_knockout, draw_triple_knockout, _build_single_knockout_bracket
from .round_robin import draw_round_robin, draw_double_round_robin, _round_robin_pairs
from .uefa_league_phase import draw_uefa_league_phase


# Іменовані формати без параметрів
NAMED = {
    "knockout": lambda p, **kw: draw_knockout(p, shuffle_seed=kw.get("shuffle_seed"), seeded=kw.get("seeded", True), num_seeded=kw.get("num_seeded")),
    "double_knockout": lambda p, **kw: draw_double_knockout(p, shuffle_seed=kw.get("shuffle_seed"), seeded=kw.get("seeded", True), num_seeded=kw.get("num_seeded")),
    "triple_knockout": lambda p, **kw: draw_triple_knockout(p, shuffle_seed=kw.get("shuffle_seed"), seeded=kw.get("seeded", True), num_seeded=kw.get("num_seeded")),
    "round_robin": lambda p, **kw: draw_round_robin(p, shuffle_seed=kw.get("shuffle_seed"), seeded=kw.get("seeded", False), num_seeded=kw.get("num_seeded")),
    "double_round_robin": lambda p, **kw: draw_double_round_robin(p, shuffle_seed=kw.get("shuffle_seed"), seeded=kw.get("seeded", False), num_seeded=kw.get("num_seeded")),
    "league_phase": lambda p, **kw: draw_uefa_league_phase(p, shuffle_seed=kw.get("shuffle_seed"), country_lock=False, max_per_country=2),
    "uefa_league_phase": lambda p, **kw: draw_uefa_league_phase(p, shuffle_seed=kw.get("shuffle_seed"), country_lock=False, max_per_country=2),
}


def _parse_args(s: str) -> list[Any]:
    """Парсинг аргументів у дужках: числа та name=value."""
    s = s.strip()
    if not s:
        return []
    args = []
    for part in re.split(r",\s*", s):
        if "=" in part:
            key, val = part.split("=", 1)
            args.append((key.strip(), int(val.strip()) if val.strip().isdigit() else val.strip()))
        elif part.isdigit():
            args.append(int(part))
        else:
            args.append(part)
    return args


def _parse_formula(formula: str) -> list[tuple[str, list]]:
    """
    Розбити формулу на кроки.
    "groups(4).round_robin().top(2).knockout()" -> [("groups", [4]), ("round_robin", []), ("top", [2]), ("knockout", [])]
    """
    formula = formula.strip().lower().replace(" ", "")
    steps = []
    # Витягнути виклики: word(num) або word()
    pattern = re.compile(r"(\w+)\s*\((.*?)\)")
    pos = 0
    while True:
        m = pattern.search(formula, pos)
        if not m:
            break
        name, arg_str = m.group(1), m.group(2)
        args = _parse_args(arg_str)
        steps.append((name, args))
        pos = m.end()
    if not steps and formula:
        # Один токен без дужок: "knockout"
        steps.append((formula, []))
    return steps


def draw_custom(
    participants: list[Participant],
    formula: str,
    shuffle_seed: int | None = None,
    seeded: bool = True,
    num_seeded: int | None = None,
) -> DrawResult:
    """
    Провести жеребкування за кастомною формулою.
    num_seeded: кількість сіяних (для нокауту та колової).
    """
    formula = formula.strip().lower()
    kw = {"shuffle_seed": shuffle_seed, "seeded": seeded, "num_seeded": num_seeded}

    # Один іменований формат без дужок
    if formula in NAMED:
        return NAMED[formula](participants, **kw)

    # uefa(8, 2) або uefa(groups=8, advance=2)
    uefa_match = re.match(r"uefa\s*\(\s*(.*)\s*\)", formula)
    if uefa_match:
        from .uefa_style import draw_uefa_style
        args = _parse_args(uefa_match.group(1))
        num_groups = 8
        advance = 2
        for a in args:
            if isinstance(a, tuple):
                if a[0] == "groups":
                    num_groups = int(a[1])
                elif a[0] in ("advance", "advance_per_group"):
                    advance = int(a[1])
            elif isinstance(a, int):
                if num_groups == 8 and advance == 2:
                    num_groups = a
                else:
                    advance = a
        return draw_uefa_style(participants, num_groups=num_groups, advance_per_group=advance, **kw)

    steps = _parse_formula(formula)
    if not steps:
        raise ValueError(f"Невідома формула: {formula}")

    # Ланцюжок: groups(N) -> round_robin() -> top(K) -> knockout()
    current: list[Participant] = list(participants)
    all_matches: list = []
    all_rounds: list = []
    round_offset = 0
    description_parts = []

    for step_name, step_args in steps:
        if step_name == "groups":
            if not step_args or not isinstance(step_args[0], int):
                raise ValueError("groups(N): вкажіть N — кількість учасників у групі")
            group_size = step_args[0]
            num_groups = (len(current) + group_size - 1) // group_size
            group_lists = distribute_into_groups(current, num_groups, seeded=seeded, shuffle_seed=shuffle_seed)
            description_parts.append(f"групи по {group_size}")
            # Зберігаємо для наступного кроку: список груп (списків учасників)
            current = group_lists  # type: ignore  # тепер current = list[list[Participant]]
            continue

        if step_name == "round_robin":
            if isinstance(current, list) and current and isinstance(current[0], list):
                # current = list of groups
                groups_data = current
                current = []
                for g in groups_data:
                    rounds_here: list[list] = []
                    ms = _round_robin_pairs(g, rounds_here, round_offset)
                    all_matches.extend(ms)
                    for r in rounds_here:
                        all_rounds.append(r)
                    round_offset += len(rounds_here)
                    # Після кругів "учасники" для наступного етапу — це групи (списки учасників)
                    current.append(g)
            else:
                dr = draw_round_robin(current, shuffle_seed=shuffle_seed, seeded=seeded)
                return dr
            description_parts.append("колова система")
            continue

        if step_name == "top":
            if not step_args or not isinstance(step_args[0], int):
                raise ValueError("top(K): вкажіть K — скільки з кожної групи виходять")
            k = step_args[0]
            # current має бути list[list[Participant]] після groups+round_robin
            if isinstance(current, list) and current and isinstance(current[0], list):
                advance_list: list[Participant] = []
                for g in current:
                    # "Топ K" — для жеребкування просто беремо перших K з групи (реальний топ визначається за результатами)
                    advance_list.extend(g[:k])
                current = advance_list
            description_parts.append(f"топ-{k} з групи")
            continue

        if step_name == "knockout":
            if isinstance(current, list) and current and isinstance(current[0], Participant):
                knockout_matches, knockout_rounds = _build_single_knockout_bracket(
                    current, shuffle_seed=shuffle_seed, seeded=seeded
                )
                for m in knockout_matches:
                    m.round_index += round_offset
                all_matches.extend(knockout_matches)
                all_rounds.extend(knockout_rounds)
            description_parts.append("нокаут")
            break

    return DrawResult(
        matches=all_matches,
        rounds=all_rounds,
        description="Кастомна формула: " + " → ".join(description_parts),
    )

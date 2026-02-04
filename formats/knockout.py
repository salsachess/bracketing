"""
Нокаут: одиночний, подвійний, потрійний.
Сітка: 1 проти останнього, 2 проти передостаннього тощо; повна сітка відома наперед.
Якщо кількість не ступінь двійки — перші номери отримують bye (проходять далі).
Підтримка сіяних: num_seeded — скільки сіяних; вони в жорсткій сітці, решта жереб.
"""
from __future__ import annotations

import random
from typing import Optional

from models import Participant, Match, DrawResult, BracketType
from draw_utils import next_power_of_two, bracket_seed_order, sort_by_seed


def _build_single_knockout_bracket(
    participants: list[Participant],
    shuffle_seed: int | None,
    num_seeded: Optional[int],
) -> tuple[list[Match], list[list[Match]]]:
    """
    Сітка нокауту: 1 vs останній, 2 vs передостанній, ...
    Bye: якщо n не 2^k, перші (2^k - n) учасників проходять у наступне коло без гри.
    num_seeded: якщо задано, перші num_seeded — сіяні (жорстка сітка), решта — жереб по несіяних позиціях.
    """
    n = len(participants)
    size = next_power_of_two(n)
    byes = size - n

    ordered = sort_by_seed(participants)
    # ordered[0] = 1-й сіяний, ordered[-1] = останній

    if num_seeded is not None and num_seeded > 0:
        bracket_order = bracket_seed_order(size)
        slots = [None] * size
        if num_seeded >= n:
            # Усі сіяні: жорстка сітка 1 vs останній, 2 vs передостанній тощо
            for i in range(size):
                if bracket_order[i] <= n:
                    slots[i] = ordered[bracket_order[i] - 1]
        else:
            # Сіяні — фіксовані позиції; несіяні — жереб (випадкові суперники для сіяних)
            seed_positions = sorted(range(size), key=lambda i: bracket_order[i])[:num_seeded]
            unseeded_positions = sorted(range(size), key=lambda i: bracket_order[i])[num_seeded : num_seeded + (n - num_seeded)]
            unseeded_list = ordered[num_seeded:n]
            rng = random.Random(shuffle_seed)
            rng.shuffle(unseeded_list)
            for idx, pos in enumerate(seed_positions):
                slots[pos] = ordered[idx]
            for idx, pos in enumerate(unseeded_positions):
                if idx < len(unseeded_list):
                    slots[pos] = unseeded_list[idx]
    else:
        # Усі в порядку сіяння; розставляємо по стандартній сітці (1 vs n, 2 vs n-1, ...)
        bracket_order = bracket_seed_order(size)
        slots = [None] * size
        for i in range(size):
            seed_1based = bracket_order[i]
            if seed_1based <= n:
                # Позиція для учасника з номером seed_1based (1..n)
                slots[i] = ordered[seed_1based - 1]
        # Bye: перші `byes` учасників (1, 2, ... byes) мають бути в позиціях, які не грають у R1
        # У bracket_order позиції 0 і 1 грають між собою — це 1 vs size. Якщо byes=8, то учасники 1..8 не грають.
        # Тобто позиції, що відповідають сіяним 1..byes, — це "bye" позиції. Вони вже заповнені.
        # Позиції для сіяних byes+1..n мають суперників. Все вже коректно: slots заповнені за bracket_order.
        pass

    matches: list[Match] = []
    round_matches: list[list[Match]] = []
    num_rounds = size.bit_length() - 1
    match_counter = 1  # глобальна нумерація M1, M2, ...

    # Раунд 1: пари (0,1), (2,3), ...; кожен матч отримує номер M1, M2, ...
    round1: list[Match] = []
    for i in range(0, size, 2):
        a, b = slots[i], slots[i + 1]
        if a is None and b is None:
            continue
        if a is None or b is None:
            continue
        m = Match(
            match_id=f"M{match_counter}",
            participant_a=a,
            participant_b=b,
            round_index=1,
            bracket=BracketType.UPPER,
        )
        matches.append(m)
        round1.append(m)
        match_counter += 1
    round_matches.append(round1)

    # Наступні раунди: повна сітка, кожен матч — номер M..., зв'язок переможець -> наступний матч
    for r in range(2, num_rounds + 1):
        curr_round: list[Match] = []
        num_in_round = max(1, (size // (2 ** r)))
        for i in range(num_in_round):
            m = Match(
                match_id=f"M{match_counter}",
                participant_a=None,
                participant_b=None,
                round_index=r,
                bracket=BracketType.UPPER,
            )
            matches.append(m)
            curr_round.append(m)
            match_counter += 1
        round_matches.append(curr_round)

    # Зв'язати переможців з наступним раундом: переможець матчу 2*i та 2*i+1 грають у матчі i наступного раунду
    for r in range(len(round_matches) - 1):
        curr = round_matches[r]
        next_round = round_matches[r + 1]
        for i, next_match in enumerate(next_round):
            left_idx = 2 * i
            right_idx = 2 * i + 1
            if left_idx < len(curr):
                curr[left_idx].winner_advances_to = next_match.match_id
            if right_idx < len(curr):
                curr[right_idx].winner_advances_to = next_match.match_id

    return matches, round_matches


def draw_knockout(
    participants: list[Participant],
    shuffle_seed: int | None = None,
    seeded: bool = True,
    num_seeded: Optional[int] = None,
) -> DrawResult:
    """
    Одиночний нокаут: 1 vs останній, 2 vs передостанній, …; сітка жорстка.
    Якщо кількість не 2^k — перші отримують bye. num_seeded: кількість сіяних (решта — жереб).
    """
    if num_seeded is None and seeded:
        num_seeded = len(participants) // 2
    elif not seeded:
        num_seeded = None
    matches, rounds = _build_single_knockout_bracket(participants, shuffle_seed, num_seeded)
    desc = f"Одиночний нокаут ({len(participants)} учасників)"
    if num_seeded is not None:
        desc += f", {num_seeded} сіяних"
    return DrawResult(matches=matches, rounds=rounds, description=desc)


def draw_double_knockout(
    participants: list[Participant],
    shuffle_seed: int | None = None,
    seeded: bool = True,
    num_seeded: Optional[int] = None,
) -> DrawResult:
    """Подвійний нокаут: верхня сітка (як одиночний) + нижня сітка + фінал."""
    if num_seeded is None and seeded:
        num_seeded = len(participants) // 2
    elif not seeded:
        num_seeded = None
    upper_matches, upper_rounds = _build_single_knockout_bracket(participants, shuffle_seed, num_seeded)
    for m in upper_matches:
        m.match_id = "U-" + m.match_id
        if m.winner_advances_to:
            m.winner_advances_to = "U-" + m.winner_advances_to
    matches = list(upper_matches)
    rounds = list(upper_rounds)
    size = next_power_of_two(len(participants))
    num_rounds_upper = size.bit_length() - 1
    r1_count = len(upper_rounds[0])
    lower_round_idx = num_rounds_upper + 1
    lower_r1: list[Match] = []
    for i in range(max(1, r1_count // 2)):
        m = Match(
            match_id=f"L-R1-M{i+1}",
            round_index=lower_round_idx,
            bracket=BracketType.LOWER,
        )
        matches.append(m)
        lower_r1.append(m)
    if lower_r1:
        rounds.append(lower_r1)
    final = Match(match_id="FINAL", round_index=lower_round_idx + 1, bracket=BracketType.FINAL)
    matches.append(final)
    rounds.append([final])
    desc = f"Подвійний нокаут ({len(participants)} учасників)"
    if num_seeded is not None:
        desc += f", {num_seeded} сіяних"
    return DrawResult(matches=matches, rounds=rounds, description=desc)


def draw_triple_knockout(
    participants: list[Participant],
    shuffle_seed: int | None = None,
    seeded: bool = True,
    num_seeded: Optional[int] = None,
) -> DrawResult:
    """Потрійний нокаут (структура як подвійний)."""
    result = draw_double_knockout(participants, shuffle_seed, seeded, num_seeded)
    result.description = (
        f"Потрійний нокаут ({len(participants)} учасників). Виліт після третьої поразки."
    )
    return result

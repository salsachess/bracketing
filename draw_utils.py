"""
Допоміжні функції для жеребкування: перемішування, сіяння, розподіл по групах.
"""
import random
from typing import TypeVar

from models import Participant

T = TypeVar("T")


def shuffle_participants(participants: list[Participant], seed: int | None = None) -> list[Participant]:
    """Перемішати учасників (з опційним seed для відтворюваності)."""
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random
    out = list(participants)
    rng.shuffle(out)
    return out


def sort_by_seed(participants: list[Participant]) -> list[Participant]:
    """Відсортувати за сіяним номером; без номера — в кінець."""
    return sorted(participants, key=lambda p: (p.seed is None, p.seed or 0))


def distribute_into_groups(
    participants: list[Participant],
    num_groups: int,
    seeded: bool = True,
    shuffle_seed: int | None = None,
) -> list[list[Participant]]:
    """
    Розподілити учасників по групах «змією» (як у УЄФА):
    Група A: 1, 8, 9, 16...
    Група B: 2, 7, 10, 15...
    """
    if seeded:
        ordered = sort_by_seed(participants)
    else:
        ordered = shuffle_participants(participants, shuffle_seed)
    groups: list[list[Participant]] = [[] for _ in range(num_groups)]
    for i, p in enumerate(ordered):
        # змійка: 0,1,2,3,3,2,1,0,0,1,2,3...
        round_trip = i // num_groups
        if round_trip % 2 == 1:
            idx = num_groups - 1 - (i % num_groups)
        else:
            idx = i % num_groups
        groups[idx].append(p)
    return groups


def next_power_of_two(n: int) -> int:
    """Найменша ступінь двійки >= n."""
    if n <= 1:
        return 1
    p = 1
    while p < n:
        p *= 2
    return p


def count_byes(num_participants: int) -> int:
    """Кількість «вільних» місць у першому раунді нокауту (щоб було 2^k)."""
    p2 = next_power_of_two(num_participants)
    return p2 - num_participants


def bracket_seed_order(n: int) -> list[int]:
    """
    Стандартний порядок сіяння в сітці нокауту для 2^k учасників.
    Повертає список довжини n: позиція i отримує сіяний номер (1..n).
    1 і 2 можуть зустрітися лише у фіналі.
    """
    if n <= 0 or (n & (n - 1)) != 0:
        raise ValueError("n має бути ступенем двійки")
    if n == 1:
        return [1]
    half = n // 2
    left = bracket_seed_order(half)
    right = [n + 1 - s for s in left]
    return [x for pair in zip(left, right) for x in pair]

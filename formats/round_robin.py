"""
Колова система: кожен з кожним один раз (або двічі — подвійна колова).
"""
from models import Participant, Match, DrawResult
from draw_utils import shuffle_participants, sort_by_seed


def _round_robin_pairs(participants: list[Participant], rounds: list[list[Match]], round_offset: int = 0) -> list[Match]:
    """Класичний алгоритм кругів: фіксований один, решта обертаються."""
    n = len(participants)
    if n < 2:
        return []
    all_matches: list[Match] = []
    # Парна кількість: кожен грає кожен раунд. Непарна: додаємо "дубль" і він отримує bye.
    if n % 2 == 1:
        participants = list(participants) + [None]  # type: ignore
        n += 1
    fixed = participants[0]
    rest = list(participants[1:])
    num_rounds = n - 1
    for r in range(num_rounds):
        round_matches: list[Match] = []
        # Пара: fixed vs rest[0]; rest[1] vs rest[-1], rest[2] vs rest[-2], ...
        opp = rest[0]
        if fixed is not None and opp is not None:
            m = Match(
                match_id=f"R{r+1+round_offset}-M1",
                participant_a=fixed,
                participant_b=opp,
                round_index=r + 1 + round_offset,
            )
            all_matches.append(m)
            round_matches.append(m)
        for i in range(1, (n - 1) // 2 + 1):
            a, b = rest[i], rest[n - 1 - i]
            if a is not None and b is not None:
                m = Match(
                    match_id=f"R{r+1+round_offset}-M{i+1}",
                    participant_a=a,
                    participant_b=b,
                    round_index=r + 1 + round_offset,
                )
                all_matches.append(m)
                round_matches.append(m)
        rounds.append(round_matches)
        # Обертання: останній елемент йде на друге місце (класичний круг)
        rest = [rest[-1]] + rest[0:-1]
    return all_matches


def draw_round_robin(
    participants: list[Participant],
    shuffle_seed: int | None = None,
    seeded: bool = False,
    num_seeded: int | None = None,
) -> DrawResult:
    """
    Колова система: кожен з кожним один раз. num_seeded: кількість сіяних (в порядку спочатку).
    """
    if seeded:
        ordered = sort_by_seed(participants)
    else:
        ordered = shuffle_participants(participants, shuffle_seed)

    rounds: list[list[Match]] = []
    matches = _round_robin_pairs(ordered, rounds, round_offset=0)
    return DrawResult(
        matches=matches,
        rounds=rounds,
        description=f"Колова система ({len(participants)} учасників). Кожен з кожним один раз.",
    )


def draw_double_round_robin(
    participants: list[Participant],
    shuffle_seed: int | None = None,
    seeded: bool = False,
    num_seeded: int | None = None,
) -> DrawResult:
    """
    Подвійна колова система: кожен з кожним двічі (дома та в гостях).
    """
    if seeded:
        ordered = sort_by_seed(participants)
    else:
        ordered = shuffle_participants(participants, shuffle_seed)

    rounds: list[list[Match]] = []
    n = len(participants)
    num_single_rounds = n - 1 if n % 2 == 0 else n
    # Перший круг
    matches = _round_robin_pairs(ordered, rounds, round_offset=0)
    # Другий круг: ті самі пари, але місця (дома/гості) змінені
    round_start = len(rounds)
    for r in range(num_single_rounds):
        round_matches_2: list[Match] = []
        for m in rounds[r]:
            # обмін гостей: A vs B -> B vs A
            m2 = Match(
                match_id=f"R{r+1+round_start}-M{m.match_id.split('-M')[-1]}",
                participant_a=m.participant_b,
                participant_b=m.participant_a,
                round_index=r + 1 + round_start,
            )
            matches.append(m2)
            round_matches_2.append(m2)
        rounds.append(round_matches_2)

    return DrawResult(
        matches=matches,
        rounds=rounds,
        description=f"Подвійна колова система ({len(participants)} учасників). Кожен з кожним двічі.",
    )

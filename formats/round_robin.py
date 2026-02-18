"""
Колова система: кожен з кожним один чи більше разів (залежно від кількості кіл).
"""
from models import Participant, Match, DrawResult
from draw_utils import shuffle_participants, sort_by_seed


def _round_robin_pairs(participants: list[Participant], rounds: list[list[Match]], round_offset: int = 0, num_rounds: int = 1) -> list[Match]:
    """
    Класичний алгоритм кругів: фіксований один, решта обертаються.
    num_rounds: скільки кіл (повизму) провести. За замовчуванням 1 (одна колова система).
    """
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
    num_rounds_single = n - 1
    
    for round_num in range(num_rounds):
        for r in range(num_rounds_single):
            round_matches: list[Match] = []
            # Глобальний номер раунду: якщо 2 кола, то R1, R2 для першої, R3, R4 для другої.
            global_round_index = round_offset + round_num * num_rounds_single + r + 1
            # Пара: fixed vs rest[0]; rest[1] vs rest[-1], rest[2] vs rest[-2], ...
            opp = rest[0]
            if fixed is not None and opp is not None:
                m = Match(
                    match_id=f"R{global_round_index}-M1",
                    participant_a=fixed,
                    participant_b=opp,
                    round_index=global_round_index,
                )
                all_matches.append(m)
                round_matches.append(m)
            for i in range(1, (n - 1) // 2 + 1):
                a, b = rest[i], rest[n - 1 - i]
                if a is not None and b is not None:
                    m = Match(
                        match_id=f"R{global_round_index}-M{i+1}",
                        participant_a=a,
                        participant_b=b,
                        round_index=global_round_index,
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
    num_rounds: int = 1,
) -> DrawResult:
    """
    Колова система: кожен з кожним num_rounds разів.
    num_rounds: скільки кіл (за замовчуванням 1 — одна колова, 2 — подвійна колова).
    num_seeded: кількість сіяних (в порядку спочатку).
    """
    if seeded:
        ordered = sort_by_seed(participants)
    else:
        ordered = shuffle_participants(participants, shuffle_seed)

    num_rounds = max(1, int(num_rounds))  # Переконатися, що це позитивне ціле число
    rounds: list[list[Match]] = []
    matches = _round_robin_pairs(ordered, rounds, round_offset=0, num_rounds=num_rounds)
    
    description = f"Колова система ({len(participants)} учасників)"
    if num_rounds == 1:
        description += ". Кожен з кожним один раз."
    elif num_rounds == 2:
        description += ". Кожен з кожним двічі (подвійна колова)."
    else:
        description += f". Кожен з кожним {num_rounds} разів ({num_rounds}-кратна колова)."
    
    return DrawResult(
        matches=matches,
        rounds=rounds,
        description=description,
    )

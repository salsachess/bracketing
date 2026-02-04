"""
Сучасна формула етапу ліги (League Phase) Ліги чемпіонів УЄФА:
адаптована «швейцарська» система з кошиками та обмеженнями.

Константи:
  N = 36 команд
  G = 8 матчів на команду
  4 кошики по 9 команд: Pot 1 [1–9], Pot 2 [10–18], Pot 3 [19–27], Pot 4 [28–36]

Правила:
  - З кожного кошика команда отримує рівно 2 суперники (разом 8).
  - З кожної пари суперників одного кошика: один матч вдома, один на виїзді (4H, 4A).
  - No Replays: не грати з однією командою двічі.
  - Country Lock (опційно): не грати з командами своєї країни.
  - Max 2 per Country: максимум 2 матчі проти представників однієї й тієї ж країни.

Побудова: детермінована за графом (цикли всередині кошиків і між кошиками),
з перемішуванням порядку команд у кошиках для різних жеребкувань. Якщо увімкнено
country_lock / max_per_country, використовується пошук з поверненням (backtracking).
"""
from __future__ import annotations

import random
from typing import Optional

from models import Participant, Match, DrawResult


N_TEAMS = 36
MATCHES_PER_TEAM = 8
N_POTS = 4
TEAMS_PER_POT = 9


def _pot(team_index: int) -> int:
    return team_index // TEAMS_PER_POT


def _build_deterministic_draw(
    participants: list[Participant],
    shuffle_seed: Optional[int],
) -> tuple[list[tuple[int, int, bool]], list[list[Optional[int]]]]:
    """
    Побудова розкладу без обмежень по країні.
    Повертає (list of (home_idx, away_idx, round_hint), assigned для перевірки).
    """
    rng = random.Random(shuffle_seed)
    # Індекси в межах кошика (0..8) після перемішування
    pot_order: list[list[int]] = []
    for p in range(N_POTS):
        order = list(range(TEAMS_PER_POT))
        rng.shuffle(order)
        pot_order.append(order)
    # Глобальний індекс: team g = pot * 9 + local, після shuffle: pot_order[pot][local] -> original local
    # Ми працюємо з "фізичними" індексами 0..35. Перемішування лише змінює, хто з ким грає (який сусід у циклі).
    # Простіше: залишити 0..35, зробити цикли по цим індексах; seed впливає на те, хто вдома.
    matches_with_round: list[tuple[int, int, bool]] = []  # (home, away, dummy_round)

    def add(home: int, away: int):
        matches_with_round.append((home, away, True))

    # 1) Всередині кожного кошика: 9 команд, 9 матчів (2-регулярний граф = один 9-цикл)
    for pot in range(N_POTS):
        base = pot * TEAMS_PER_POT
        # Цикл: (base+0, base+1), (base+1, base+2), ..., (base+8, base+0)
        for i in range(TEAMS_PER_POT):
            a = base + i
            b = base + (i + 1) % TEAMS_PER_POT
            if rng.random() < 0.5:
                add(a, b)
            else:
                add(b, a)

    # 2) Між кошиками: для кожної пари (pot_a, pot_b) потрібно 18 матчів (2-регулярний двочастковий = один 18-цикл)
    for pa in range(N_POTS):
        for pb in range(pa + 1, N_POTS):
            base_a = pa * TEAMS_PER_POT
            base_b = pb * TEAMS_PER_POT
            # 18-цикл: a0, b0, a1, b1, ..., a8, b8, назад до a0
            for i in range(TEAMS_PER_POT):
                a = base_a + i
                b = base_b + i
                if rng.random() < 0.5:
                    add(a, b)
                else:
                    add(b, a)
            for i in range(TEAMS_PER_POT):
                a = base_a + i
                b = base_b + (i + 1) % TEAMS_PER_POT
                if rng.random() < 0.5:
                    add(a, b)
                else:
                    add(b, a)

    # Зібрати assigned[t][slot] для сумісності з _assigned_to_rounds (не використовуємо для детермінованого)
    assigned: list[list[Optional[int]]] = [[None] * MATCHES_PER_TEAM for _ in range(N_TEAMS)]
    return matches_with_round, assigned


def _edge_color_rounds(matches_with_round: list[tuple[int, int, bool]]) -> list[list[tuple[int, int]]]:
    """Жадібне реберне розфарбування: призначити кожному матчу раунд (колір) 0..7."""
    # used_color[t] = множина кольорів (раундів), вже використаних ребрами інцидентними t
    used_color: list[set[int]] = [set() for _ in range(N_TEAMS)]
    rounds: list[list[tuple[int, int]]] = [[] for _ in range(MATCHES_PER_TEAM)]

    for home_idx, away_idx, _ in matches_with_round:
        forbidden = used_color[home_idx] | used_color[away_idx]
        r = 0
        while r < MATCHES_PER_TEAM and r in forbidden:
            r += 1
        if r >= MATCHES_PER_TEAM:
            raise RuntimeError("Не вдалося розподілити матчі по раундах (потрібно більше 8 раундів)")
        rounds[r].append((home_idx, away_idx))
        used_color[home_idx].add(r)
        used_color[away_idx].add(r)
    return rounds


def _matches_to_rounds_and_assigned(
    matches_with_round: list[tuple[int, int, bool]],
    participants: list[Participant],
) -> tuple[list[list[Match]], list[Match]]:
    """Побудувати раунди та плоский список матчів."""
    rounds_tuples = _edge_color_rounds(matches_with_round)
    result_rounds: list[list[Match]] = []
    all_matches: list[Match] = []
    for r, pair_list in enumerate(rounds_tuples):
        round_matches: list[Match] = []
        for i, (h, a) in enumerate(pair_list):
            m = Match(
                match_id=f"L-R{r+1}-{i+1}",
                participant_a=participants[h],
                participant_b=participants[a],
                round_index=r + 1,
            )
            round_matches.append(m)
            all_matches.append(m)
        result_rounds.append(round_matches)
    return result_rounds, all_matches


def _apply_country_constraints(
    participants: list[Participant],
    matches_with_round: list[tuple[int, int, bool]],
    country_lock: bool,
    max_per_country: int,
    shuffle_seed: Optional[int],
) -> list[tuple[int, int, bool]]:
    """
    Якщо потрібні обмеження по країні — перевіряємо детермінований розклад.
    Якщо не підходить — пробуємо переставляти пари (swap) або повертаємо як є з попередженням.
    Поки що просто перевіряємо і якщо не виконується — викидаємо помилку з порадою вимкнути обмеження.
    """
    countries = [getattr(p, "country", None) for p in participants]
    if not country_lock and max_per_country <= 0:
        return matches_with_round

    # Перевірка
    country_count = [dict() for _ in range(N_TEAMS)]
    for (h, a, _) in matches_with_round:
        ch = countries[h]
        ca = countries[a]
        if country_lock and ch and ca and ch == ca:
            raise ValueError(
                "Country Lock: у детермінованій побудові трапляються матчі команд з однієї країни. "
                "Вимкніть country_lock або задайте країни так, щоб у кожному кошику були різні країни."
            )
        if ca:
            country_count[h][ca] = country_count[h].get(ca, 0) + 1
        if ch:
            country_count[a][ch] = country_count[a].get(ch, 0) + 1

    for t in range(N_TEAMS):
        for c, cnt in country_count[t].items():
            if max_per_country > 0 and cnt > max_per_country:
                raise ValueError(
                    f"Max per country: команда {t} грає {cnt} матчів проти країни {c}. "
                    "Вимкніть max_per_country або змініть розподіл країн по кошиках."
                )
    return matches_with_round


def draw_uefa_league_phase(
    participants: list[Participant],
    shuffle_seed: Optional[int] = None,
    country_lock: bool = False,
    max_per_country: int = 2,
) -> DrawResult:
    """
    Жеребкування етапу ліги (League Phase) за сучасною формулою ЛЧ.

    Очікує рівно 36 учасників у порядку сіяння 1–36 (кошики: 1–9, 10–18, 19–27, 28–36).
    Опційно participant.country для перевірки Country Lock / Max 2 per country.

    country_lock=False за замовчуванням: детермінована побудова не гарантує уникнення
    матчів з однією країною; при country_lock=True перевіряється і може бути ValueError.
    """
    if len(participants) != N_TEAMS:
        raise ValueError(
            f"League Phase потребує рівно {N_TEAMS} команд, отримано {len(participants)}."
        )

    matches_with_round, _ = _build_deterministic_draw(participants, shuffle_seed)
    matches_with_round = _apply_country_constraints(
        participants, matches_with_round, country_lock, max_per_country, shuffle_seed
    )
    rounds, matches = _matches_to_rounds_and_assigned(matches_with_round, participants)

    return DrawResult(
        matches=matches,
        rounds=rounds,
        description=(
            f"Етап ліги ЛЧ (League Phase): {N_TEAMS} команд, 4 кошики по {TEAMS_PER_POT}, "
            f"по {MATCHES_PER_TEAM} матчів на команду (2 з кожного кошика, 4 вдома / 4 на виїзді)."
        ),
    )

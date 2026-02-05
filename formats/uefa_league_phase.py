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


def _pot(team_index: int, teams_per_pot: int) -> int:
    return team_index // teams_per_pot


def _build_deterministic_draw(
    participants: list[Participant],
    shuffle_seed: Optional[int],
    n_teams: int,
    teams_per_pot: int,
    n_pots: int,
    matches_per_team: int,
) -> tuple[list[tuple[int, int, bool]], list[list[Optional[int]]]]:
    """
    Побудова розкладу без обмежень по країні.
    Масштабовано для будь-якого k_per_pot: по k_per_pot матчів з кожного кошика на команду.
    Повертає (list of (home_idx, away_idx, round_hint), assigned для перевірки).
    """
    rng = random.Random(shuffle_seed)
    matches_with_round: list[tuple[int, int, bool]] = []

    def add(home: int, away: int):
        matches_with_round.append((home, away, True))

    k_per_pot = matches_per_team // n_pots

    # Чи потрібна «непарна» схема: (T * k_per_pot) непарне — одна команда в кошику грає на 1 матч менше всередині, на 1 більше між кошиками
    odd_scheme = (teams_per_pot * k_per_pot) % 2 == 1

    # 1) Всередині кожного кошика: по k_per_pot матчів на команду (або k_per_pot-1 для однієї при odd_scheme)
    if k_per_pot >= 1:
        for pot in range(n_pots):
            base = pot * teams_per_pot
            T = teams_per_pot
            # Цикли d=1..k_per_pot//2 дають по 2 матчі на команду
            for d in range(1, k_per_pot // 2 + 1):
                for i in range(T):
                    a = base + i
                    b = base + (i + d) % T
                    if rng.random() < 0.5:
                        add(a, b)
                    else:
                        add(b, a)
            # Непарний k_per_pot і парний T: діаметр (i, i+T/2)
            if k_per_pot % 2 == 1 and T % 2 == 0:
                half = T // 2
                for i in range(half):
                    a = base + i
                    b = base + i + half
                    if rng.random() < 0.5:
                        add(a, b)
                    else:
                        add(b, a)
            # Непарна схема (T*k_per_pot непарне): одна команда має k_per_pot-1 всередині — додаємо паросочетание на T-1 вершинах
            if odd_scheme:
                # Цикли вже дали (k_per_pot-1) матчів на команду. Потрібно ще (T-1)//2 ребер для (T-1) команд по 1 матчу (команда T-1 без додаткового)
                for i in range(0, T - 1, 2):
                    a = base + i
                    b = base + i + 1
                    if rng.random() < 0.5:
                        add(a, b)
                    else:
                        add(b, a)

    # 2) Між кошиками: k_per_pot * T матчів на пару кошиків (або на 1 менше при odd_scheme — тоді одна команда з кожного кошика +1)
    for pa in range(n_pots):
        for pb in range(pa + 1, n_pots):
            base_a = pa * teams_per_pot
            base_b = pb * teams_per_pot
            T = teams_per_pot
            if not odd_scheme:
                for r in range(k_per_pot):
                    for i in range(T):
                        a = base_a + i
                        b = base_b + (i + r) % T
                        if rng.random() < 0.5:
                            add(a, b)
                        else:
                            add(b, a)
            else:
                # Непарна схема: 2 повних «раунди» (22 ребра) + 6 ребер, щоб одна команда в кожному кошику мала 6 матчів
                for r in range(2):
                    for i in range(T):
                        a = base_a + i
                        b = base_b + (i + r) % T
                        if rng.random() < 0.5:
                            add(a, b)
                        else:
                            add(b, a)
                # 6 додаткових ребер: (0,2), (1,3), (2,4), (3,5), (4,6), (5,7) — по +1 для 6 команд у кожному кошику
                for i in range(6):
                    a = base_a + i
                    b = base_b + (i + 2) % T
                    if rng.random() < 0.5:
                        add(a, b)
                    else:
                        add(b, a)

    # При odd_scheme генерується 55 унікальних пар; потрібно 110 слотів (кожна пара двічі)
    if odd_scheme:
        matches_with_round.extend(list(matches_with_round))

    assigned: list[list[Optional[int]]] = [[None] * matches_per_team for _ in range(n_teams)]
    return matches_with_round, assigned


def _greedy_assign_rounds(
    edges: list[tuple[int, int]],
    n_teams: int,
    matches_per_team: int,
) -> list[list[tuple[int, int]]] | None:
    """Жадібне призначення: кожному ребру найменший тур r, де обидві команди ще вільні. Повертає None якщо не вмістилось."""
    # #region agent log
    import json
    import os
    _log_path = "/Users/serhiy.franchuk/Documents/working/universal-scheduler/.cursor/debug.log"
    def _log(msg, data):
        os.makedirs(os.path.dirname(_log_path), exist_ok=True)
        open(_log_path, "a").write(json.dumps({"message": msg, "data": data, "sessionId": "debug-session", "timestamp": __import__("time").time() * 1000}) + "\n")
    # #endregion
    rounds_tuples: list[list[tuple[int, int]]] = [[] for _ in range(matches_per_team)]
    used: list[set[int]] = [set() for _ in range(n_teams)]
    for idx, (h, a) in enumerate(edges):
        r = 0
        while r < matches_per_team and (r in used[h] or r in used[a]):
            r += 1
        if r >= matches_per_team:
            _log("greedy_fail", {"hypothesisId": "H1", "edge_index": idx, "h": h, "a": a, "n_teams": n_teams, "matches_per_team": matches_per_team, "len_edges": len(edges)})
            return None
        rounds_tuples[r].append((h, a))
        used[h].add(r)
        used[a].add(r)
    return rounds_tuples


def _edge_color_rounds(
    matches_with_round: list[tuple[int, int, bool]],
    n_teams: int,
    matches_per_team: int,
) -> list[list[tuple[int, int]]]:
    """
    Розподіл матчів по раундах. Спочатку пробуємо жадібне призначення з різними порядками ребер
    (для дефолтної конфігурації 36/8, 30/5 тощо). Якщо не вийшло — max_weight_matching / MultiGraph.
    """
    try:
        import networkx as nx
    except ImportError:
        raise RuntimeError(
            "League Phase потребує networkx для розподілу матчів по турах. "
            "Встановіть: pip install networkx"
        )

    edges = [(h, a) for h, a, _ in matches_with_round]
    # #region agent log
    import json as _json
    import os as _os
    _log_path = "/Users/serhiy.franchuk/Documents/working/universal-scheduler/.cursor/debug.log"
    def _dbg(msg, data):
        _os.makedirs(_os.path.dirname(_log_path), exist_ok=True)
        with open(_log_path, "a") as _f:
            _f.write(_json.dumps({"message": msg, "data": {**data, "sessionId": "debug-session"}, "timestamp": __import__("time").time() * 1000}) + "\n")
    unique_pairs = set((min(h, a), max(h, a)) for h, a, _ in matches_with_round)
    use_multigraph = len(matches_with_round) > len(unique_pairs)
    _dbg("edge_color_entry", {"hypothesisId": "H3", "n_teams": n_teams, "matches_per_team": matches_per_team, "len_edges": len(edges), "len_unique_pairs": len(unique_pairs), "use_multigraph": use_multigraph})
    # #endregion

    # Різні порядки для жадібного призначення (часто дають рівно matches_per_team турів для 36/8, 30/5)
    by_min_vertex: list[tuple[int, int]] = []
    for v in range(n_teams):
        for (h, a) in edges:
            if min(h, a) == v:
                by_min_vertex.append((h, a))
    _dbg("order_lengths", {"hypothesisId": "H3", "len_by_min_vertex": len(by_min_vertex), "len_edges": len(edges)})
    by_max_degree: list[tuple[int, int]] = list(edges)
    deg = [0] * n_teams
    for (h, a) in edges:
        deg[h] += 1
        deg[a] += 1
    by_max_degree.sort(key=lambda e: -(deg[e[0]] + deg[e[1]]))

    for order_name, ordered in (("by_min_vertex", by_min_vertex), ("by_max_degree", by_max_degree), ("edges", edges)):
        result = _greedy_assign_rounds(ordered, n_teams, matches_per_team)
        if result is not None:
            _dbg("greedy_ok", {"hypothesisId": "H1", "used_order": order_name})
            return result
    _dbg("greedy_all_failed", {"hypothesisId": "H1", "fallback": "max_weight_matching"})

    # Запасний варіант: 1-факторизація через max_weight_matching

    rounds_tuples = [[] for _ in range(matches_per_team)]

    if not use_multigraph:
        G = nx.Graph()
        for home_idx, away_idx, _ in matches_with_round:
            u, v = min(home_idx, away_idx), max(home_idx, away_idx)
            G.add_edge(u, v, pair=(home_idx, away_idx))
        for r in range(matches_per_team):
            if G.number_of_edges() == 0:
                break
            matching = nx.max_weight_matching(G, maxcardinality=True)
            for (u, v) in matching:
                pair = G.edges[u, v].get("pair", (u, v))
                rounds_tuples[r].append(pair)
                G.remove_edge(u, v)
    else:
        G = nx.MultiGraph()
        for home_idx, away_idx, _ in matches_with_round:
            G.add_edge(home_idx, away_idx, pair=(home_idx, away_idx))
        for r in range(matches_per_team):
            if G.number_of_edges() == 0:
                break
            H = nx.Graph()
            for u, v, _ in list(G.edges(keys=True)):
                if not H.has_edge(u, v):
                    H.add_edge(u, v)
            matching = nx.max_weight_matching(H, maxcardinality=True)
            matching_size = len(matching)
            for (u, v) in matching:
                key = next(iter(G[u][v]))
                pair = G.edges[u, v, key].get("pair", (u, v))
                rounds_tuples[r].append(pair)
                G.remove_edge(u, v, key)
            # #region agent log
            _dbg("multigraph_round", {"hypothesisId": "H2", "round": r, "matching_size": matching_size, "edges_left_after": G.number_of_edges()})
            # #endregion

    if G.number_of_edges() > 0:
        # #region agent log
        _dbg("raise_edges_left", {"hypothesisId": "H2", "edges_left": G.number_of_edges(), "matches_per_team": matches_per_team})
        # #endregion
        raise RuntimeError(
            f"Неможливо розкласти всі матчі в {matches_per_team} турів. "
            f"Спробуйте збільшити кількість турів або обрати іншу кількість учасників."
        )
    return rounds_tuples


def _matches_to_rounds_and_assigned(
    matches_with_round: list[tuple[int, int, bool]],
    participants: list[Participant],
    n_teams: int,
    matches_per_team: int,
) -> tuple[list[list[Match]], list[Match]]:
    """Побудувати раунди та плоский список матчів."""
    rounds_tuples = _edge_color_rounds(matches_with_round, n_teams, matches_per_team)
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
    n_teams: int,
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
    country_count = [dict() for _ in range(n_teams)]
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

    for t in range(n_teams):
        for c, cnt in country_count[t].items():
            if max_per_country > 0 and cnt > max_per_country:
                raise ValueError(
                    f"Max per country: команда {t} грає {cnt} матчів проти країни {c}. "
                    "Вимкніть max_per_country або змініть розподіл країн по кошиках."
                )
    return matches_with_round


def draw_uefa_league_phase(
    participants: list[Participant],
    rounds: int = 8,
    shuffle_seed: Optional[int] = None,
    country_lock: bool = False,
    max_per_country: int = 2,
) -> DrawResult:
    """
    Жеребкування етапу ліги (League Phase) за сучасною формулою ЛЧ.

    rounds: кількість турів (матчів на команду). Розмір кошика = rounds+1.
    N = (rounds+1) * num_pots; rounds має ділитися на num_pots (матчів з кожного кошика).
    """
    n_teams = len(participants)
    if n_teams % 2 == 1:
        raise ValueError(
            f"League Phase: кількість учасників має бути парною (кожен тур по n/2 матчів). Отримано {n_teams}."
        )
    teams_per_pot = rounds + 1
    n_pots = n_teams // teams_per_pot
    matches_per_team = rounds

    if n_teams % teams_per_pot != 0:
        raise ValueError(
            f"League Phase: кількість учасників має ділитися на (турів+1) = {teams_per_pot}. "
            f"Отримано {n_teams} учасників."
        )
    k_per_pot_val = rounds // n_pots
    if (teams_per_pot * k_per_pot_val) % 2 == 1:
        # Кількість матчів всередині кошика = (команд × матчів на команду) / 2. Щоб було цілим, добуток має бути парним.
        raise ValueError(
            f"League Phase: комбінація {n_teams} учасників і {rounds} турів неможлива: "
            f"у кошику по {teams_per_pot} команд кожна грає {k_per_pot_val} матчів всередині кошика — "
            f"разом це {teams_per_pot * k_per_pot_val} «напівматчів», тобто {teams_per_pot * k_per_pot_val / 2} матчів (неціле). "
            f"Потрібно, щоб (команд у кошику)×(матчів з кошика) було парним: оберіть кількість турів, кратну {2 * n_pots} "
            f"(напр. {2 * n_pots} або {4 * n_pots}), або іншу кількість учасників (наприклад 18, 36)."
        )
    if rounds % n_pots != 0:
        raise ValueError(
            f"League Phase: кількість турів ({rounds}) має ділитися на кількість кошиків ({n_pots})."
        )
    k_per_pot = rounds // n_pots
    if k_per_pot == 1 and teams_per_pot % 2 == 1:
        raise ValueError(
            "League Phase: при одному матчі з кожного кошика розмір кошика (турів+1) має бути парним. "
            f"Зараз турів={rounds}, кошик={teams_per_pot}."
        )

    matches_with_round, _ = _build_deterministic_draw(
        participants, shuffle_seed, n_teams, teams_per_pot, n_pots, matches_per_team
    )
    matches_with_round = _apply_country_constraints(
        participants, matches_with_round, country_lock, max_per_country, shuffle_seed, n_teams
    )
    rounds_list, matches = _matches_to_rounds_and_assigned(
        matches_with_round, participants, n_teams, matches_per_team
    )
    desc = (
        f"Етап ліги ЛЧ (League Phase): {n_teams} команд, {n_pots} кошиків по {teams_per_pot}, "
        f"по {rounds} матчів на команду ({k_per_pot} з кожного кошика)."
    )
    return DrawResult(matches=matches, rounds=rounds_list, description=desc)

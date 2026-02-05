#!/usr/bin/env python3
"""
Універсальний генератор жеребкувань.

Формати:
  1 — нокаут (одиночний)
  2 — нокаут подвійний
  3 — нокаут потрійний
  4 — колова система
  5 — подвійна колова система
  6 — стиль Ліги чемпіонів УЄФА (групи + плей-оф)
  7 — кастомна формула

Запуск: python main.py [номер або формула]
Без аргументів — інтерактивний вибір.
"""
import sys
import os

# Додати корінь проєкту в шлях
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Participant, DrawResult
from formats import (
    draw_knockout,
    draw_double_knockout,
    draw_triple_knockout,
    draw_round_robin,
    draw_double_round_robin,
    draw_uefa_style,
    draw_uefa_league_phase,
    draw_custom,
)


def league_phase_valid_participant_counts(rounds: int) -> tuple[int, list[int]]:
    """
    Для League Phase при заданій кількості турів: дійсні кількості учасників.
    Умови: n = (rounds+1)*k (k — дільник rounds); n парне (кожен тур по n/2 матчів, без баїв);
    при одному матчі з кошика розмір кошика парний; (команд у кошику)×(матчів з кошика) парне.
    Повертає (мінімум_учасників, відсортований список допустимих n).
    """
    pot_size = rounds + 1
    divisors = [d for d in range(1, rounds + 1) if rounds % d == 0]
    valid = []
    for k in divisors:
        n = pot_size * k
        if n % 2 == 1:
            continue  # тільки парна кількість: кожен тур по n/2 матчів, інакше не вмістити в rounds турів
        n_pots = n // pot_size
        k_per_pot = rounds // n_pots
        if k_per_pot == 1 and pot_size % 2 == 1:
            continue  # заборонено: один матч з кошика при непарному розмірі кошика
        if n_pots == 1 and pot_size % 2 == 1:
            continue  # один кошик з непарним числом: не вмістити всі матчі в rounds турів без баїв
        if (pot_size * k_per_pot) % 2 == 1:
            continue  # неціла кількість матчів у кошику (27.5 тощо)
        valid.append(n)
    return (min(valid) if valid else 0, sorted(valid))


def make_sample_participants(
    n: int,
    num_seeded: int | None = None,
    format_kind: str = "default",
    rounds: int | None = None,
) -> list[Participant]:
    """
    Згенерувати n учасників для прикладу.
    format_kind: "default" — номери та сіяний/жереб; "league_phase" — номери та кошики.
    num_seeded: кількість сіяних (для default; 0 = жереб, n = усі сіяні).
    rounds: для league_phase — кількість турів (розмір кошика = rounds+1).
    """
    if format_kind == "league_phase":
        teams_per_pot = (rounds + 1) if rounds is not None else 9
        participants = []
        for i in range(1, n + 1):
            pot = (i - 1) // teams_per_pot + 1
            participants.append(
                Participant(id=str(i), name=f"{i}-кошик{pot}", seed=i)
            )
        return participants
    # default: 1-сіяний, 2-сіяний, ..., num_seeded-сіяний, (num_seeded+1)-жереб, ..., n-жереб
    if num_seeded is None:
        num_seeded = n // 2
    participants = []
    for i in range(1, n + 1):
        label = "сіяний" if i <= num_seeded else "жереб"
        participants.append(
            Participant(id=str(i), name=f"{i}-{label}", seed=i)
        )
    return participants


def run_draw(
    choice: str,
    participants: list[Participant],
    seed: int | None = 42,
    num_seeded: int | None = None,
    league_rounds: int | None = None,
) -> DrawResult:
    """Запустити жеребкування за вибором. num_seeded: 0=повний жереб, n=усі сіяні. league_rounds: кількість турів для формату 8."""
    seed = seed if seed is not None else None
    n = len(participants)
    if num_seeded is None and choice not in ("8", "league_phase", "етап ліги", "league phase"):
        num_seeded = n // 2
    if choice in ("1", "нокаут", "knockout"):
        return draw_knockout(participants, shuffle_seed=seed, seeded=True, num_seeded=num_seeded)
    if choice in ("2", "подвійний нокаут", "double_knockout"):
        return draw_double_knockout(participants, shuffle_seed=seed, seeded=True, num_seeded=num_seeded)
    if choice in ("3", "потрійний нокаут", "triple_knockout"):
        return draw_triple_knockout(participants, shuffle_seed=seed, seeded=True, num_seeded=num_seeded)
    if choice in ("4", "колова", "round_robin"):
        return draw_round_robin(participants, shuffle_seed=seed, seeded=True, num_seeded=num_seeded)
    if choice in ("5", "подвійна колова", "double_round_robin"):
        return draw_double_round_robin(participants, shuffle_seed=seed, seeded=True, num_seeded=num_seeded)
    if choice in ("6", "uefa", "ліга чемпіонів"):
        return draw_uefa_style(participants, num_groups=8, advance_per_group=2, shuffle_seed=seed, seeded=True)
    if choice in ("8", "league_phase", "етап ліги", "league phase"):
        rounds = league_rounds if league_rounds is not None else 8
        return draw_uefa_league_phase(participants, rounds=rounds, shuffle_seed=seed, country_lock=False, max_per_country=2)
    # Інакше — кастомна формула
    return draw_custom(participants, formula=choice, shuffle_seed=seed, seeded=True, num_seeded=num_seeded, rounds=league_rounds)


def main() -> None:
    print("Універсальний генератор жеребкувань\n")
    print("Формати:")
    print("  1 — нокаут (одиночний)")
    print("  2 — нокаут подвійний")
    print("  3 — нокаут потрійний")
    print("  4 — колова система")
    print("  5 — подвійна колова система")
    print("  6 — стиль Ліги чемпіонів УЄФА (групи + плей-оф)")
    print("  8 — етап ліги ЛЧ (League Phase): 36 команд, 4 кошики, 8 матчів на команду")
    print("  7 — кастомна формула (наприклад: groups(4).round_robin().top(2).knockout())")
    print()

    argv = sys.argv[1:]
    if argv:
        choice = " ".join(argv).strip()
    else:
        choice = input("Оберіть формат (1–8 або формулу): ").strip()

    if not choice:
        print("Нічого не обрано.")
        return

    num_seeded_arg: int | None = None
    league_rounds_arg: int | None = None
    is_league_phase = choice.strip() in ("8", "league_phase", "етап ліги", "league phase")

    if is_league_phase:
        while True:
            try:
                r_input = input("Кількість турів (за замовч. 8): ").strip() or "8"
                league_rounds_arg = int(r_input)
            except (EOFError, ValueError):
                league_rounds_arg = 8
            pot_size = league_rounds_arg + 1
            min_n, valid_n_list = league_phase_valid_participant_counts(league_rounds_arg)
            if valid_n_list:
                break
            print(
                f"При {league_rounds_arg} турах немає допустимої (парної) кількості учасників. "
                "Оберіть іншу кількість турів (наприклад 8 або 12)."
            )
        while True:
            try:
                n_input = input(
                    f"Кількість учасників (мін. {min_n}, допустимі: {valid_n_list}, за замовч. 36): "
                ).strip() or "36"
                n = int(n_input)
            except (EOFError, ValueError):
                n = 36
            if n in valid_n_list:
                break
            print(
                f"При {league_rounds_arg} турах кількість учасників має бути така, щоб кількість турів "
                f"ділилася на кількість кошиків (кошик = {pot_size})."
            )
            print(f"Мінімум учасників: {min_n}. Допустимі значення: {valid_n_list}. Спробуйте ще раз.")
        participants = make_sample_participants(n, format_kind="league_phase", rounds=league_rounds_arg)
        print(f"Етап ліги ЛЧ: {n} учасників, {league_rounds_arg} турів, кошики по {pot_size}.\n")
    else:
        if argv and len(argv) >= 2 and argv[-1].isdigit():
            n = int(argv[-1])
            choice = " ".join(argv[:-1]).strip() or "1"
        else:
            try:
                n_input = input("Кількість учасників (за замовч. 8): ").strip() or "8"
                n = int(n_input)
            except (EOFError, ValueError):
                n = 32 if choice.strip() in ("6", "uefa", "ліга чемпіонів") else 8

        needs_seeded = choice.strip() in ("1", "2", "3", "4", "5", "нокаут", "колова", "round_robin", "knockout")
        if needs_seeded:
            try:
                s_input = input("Кількість сіяних (0 = повний жереб, n = усі сіяні, за замовч. n/2): ").strip()
                if s_input != "":
                    num_seeded_arg = int(s_input)
            except (EOFError, ValueError):
                pass

        if choice in ("6", "uefa", "ліга чемпіонів") and n < 16:
            participants = make_sample_participants(32, num_seeded=16, format_kind="default")
            print("Для формату УЄФА використано 32 учасники.\n")
        else:
            participants = make_sample_participants(
                n, num_seeded=num_seeded_arg if num_seeded_arg is not None else n // 2, format_kind="default"
            )

    try:
        result = run_draw(choice, participants, num_seeded=num_seeded_arg, league_rounds=league_rounds_arg)
        print(result.summary())
    except Exception as e:
        print(f"Помилка: {e}")
        raise


if __name__ == "__main__":
    main()

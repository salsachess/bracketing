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


def make_sample_participants(
    n: int,
    num_seeded: int | None = None,
    format_kind: str = "default",
) -> list[Participant]:
    """
    Згенерувати n учасників для прикладу.
    format_kind: "default" — номери та сіяний/жереб; "league_phase" — номери та кошики.
    num_seeded: кількість сіяних (для default; якщо None — n//2 для нокауту/колової).
    """
    if format_kind == "league_phase":
        # 1-кошик1, 2-кошик1, ..., 9-кошик1, 10-кошик2, ..., 36-кошик4
        participants = []
        teams_per_pot = 9
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
) -> DrawResult:
    """Запустити жеребкування за вибором. num_seeded передається у формати, де є сіяння."""
    seed = seed if seed is not None else None
    n = len(participants)
    if num_seeded is None:
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
        return draw_uefa_league_phase(participants, shuffle_seed=seed, country_lock=False, max_per_country=2)
    # Інакше — кастомна формула
    return draw_custom(participants, formula=choice, shuffle_seed=seed, seeded=True, num_seeded=num_seeded)


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

    # Кількість учасників
    if argv and len(argv) >= 2 and argv[-1].isdigit():
        n = int(argv[-1])
        choice = " ".join(argv[:-1]).strip() or "1"
    else:
        try:
            n_input = input("Кількість учасників (за замовч. 8): ").strip() or "8"
            n = int(n_input)
        except (EOFError, ValueError):
            if choice.strip() in ("8", "league_phase", "етап ліги", "league phase"):
                n = 36
            elif choice.strip() in ("6", "uefa", "ліга чемпіонів"):
                n = 32
            else:
                n = 8

    if choice in ("8", "league_phase", "етап ліги", "league phase"):
        participants = make_sample_participants(36, format_kind="league_phase")
        print("Для етапу ліги ЛЧ використано 36 учасників (4 кошики по 9).\n")
    elif choice in ("6", "uefa", "ліга чемпіонів") and n < 16:
        participants = make_sample_participants(32, num_seeded=16, format_kind="default")
        print("Для формату УЄФА використано 32 учасники.\n")
    else:
        participants = make_sample_participants(n, num_seeded=n // 2, format_kind="default")

    try:
        result = run_draw(choice, participants)
        print(result.summary())
    except Exception as e:
        print(f"Помилка: {e}")
        raise


if __name__ == "__main__":
    main()

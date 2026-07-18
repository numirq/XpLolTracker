from __future__ import annotations


# Account XP bar sizes for the road to ranked. The current level value read
# from the League client takes priority, so a future Riot change repairs itself.
LEVEL_XP_REQUIREMENTS = {
    1: 144, 2: 144, 3: 192, 4: 240, 5: 336, 6: 432, 7: 528, 8: 624,
    9: 720, 10: 816, 11: 912, 12: 984, 13: 1056, 14: 1128, 15: 1344,
    16: 1440, 17: 1536, 18: 1680, 19: 1824, 20: 1968, 21: 2112,
    22: 2208, 23: 2304, 24: 2304, 25: 2496, 26: 2496, 27: 2592,
    28: 2688, 29: 2688,
}


def calculate_xp_gain(
    before_level: int,
    before_xp: int,
    before_required: int,
    after_level: int,
    after_xp: int,
) -> int | None:
    """Calculate gained account XP when enough bar information is available."""
    if after_level < before_level:
        return None
    if after_level == before_level:
        gain = after_xp - before_xp
        return gain if gain >= 0 else None
    if after_level == before_level + 1 and before_required > 0:
        gain = (before_required - before_xp) + after_xp
        return gain if gain >= 0 else None
    return None


def progress_percent(current_xp: int, required_xp: int) -> float:
    if required_xp <= 0:
        return 0.0
    return max(0.0, min(100.0, current_xp / required_xp * 100.0))


def games_to_next_level(current_xp: int, required_xp: int, average_gain: float) -> int | None:
    if required_xp <= 0 or average_gain <= 0:
        return None
    remaining = max(0, required_xp - current_xp)
    return int((remaining + average_gain - 1) // average_gain)


def xp_to_level_30(current_level: int, current_xp: int, current_required: int = 0) -> int:
    if current_level >= 30:
        return 0
    required_now = current_required or LEVEL_XP_REQUIREMENTS.get(current_level, 0)
    remaining = max(0, required_now - current_xp)
    for level in range(current_level + 1, 30):
        remaining += LEVEL_XP_REQUIREMENTS.get(level, 0)
    return remaining


def games_to_level_30(
    current_level: int,
    current_xp: int,
    current_required: int,
    average_gain: float,
) -> int | None:
    if average_gain <= 0:
        return None
    remaining = xp_to_level_30(current_level, current_xp, current_required)
    return int((remaining + average_gain - 1) // average_gain)

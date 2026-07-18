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

# Riot exposes the exact size of the current XP bar through the local client,
# but not every future bar.  For goals above level 30 we keep the estimate
# useful by repeating the current post-30 bar (or the last known pre-30 bar).
POST_30_FALLBACK_XP = LEVEL_XP_REQUIREMENTS[29]


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


def xp_to_level(
    current_level: int,
    current_xp: int,
    target_level: int,
    current_required: int = 0,
) -> int:
    """Return XP remaining to any future target level.

    Values through level 30 use the known level table.  Later levels are an
    estimate based on the current post-30 XP bar, refreshed whenever the
    League client is read.
    """
    target_level = max(1, int(target_level))
    if current_level >= target_level:
        return 0
    required_now = current_required or LEVEL_XP_REQUIREMENTS.get(current_level, 0)
    remaining = max(0, required_now - current_xp)
    known_stop = min(target_level, 30)
    for level in range(current_level + 1, known_stop):
        remaining += LEVEL_XP_REQUIREMENTS.get(level, 0)

    first_post_30_bar = max(current_level + 1, 30)
    post_30_bars = max(0, target_level - first_post_30_bar)
    if post_30_bars:
        post_30_required = (
            current_required
            if current_level >= 30 and current_required > 0
            else POST_30_FALLBACK_XP
        )
        remaining += post_30_bars * post_30_required
    return remaining


def goal_estimate_is_approximate(target_level: int) -> bool:
    """Whether a target crosses bars Riot does not expose in advance."""
    return int(target_level) > 30


def games_to_level(
    current_level: int,
    current_xp: int,
    current_required: int,
    target_level: int,
    average_gain: float,
) -> int | None:
    if average_gain <= 0:
        return None
    remaining = xp_to_level(current_level, current_xp, target_level, current_required)
    return int((remaining + average_gain - 1) // average_gain)


def xp_to_level_30(current_level: int, current_xp: int, current_required: int = 0) -> int:
    return xp_to_level(current_level, current_xp, 30, current_required)


def games_to_level_30(
    current_level: int,
    current_xp: int,
    current_required: int,
    average_gain: float,
) -> int | None:
    return games_to_level(current_level, current_xp, current_required, 30, average_gain)

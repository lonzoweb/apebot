"""
Numerology Engine for ApeBot
Calculates universal day numbers and fetches readings from the database.
"""

from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

# Master numbers — reduction stops here
MASTER_NUMBERS = {11, 22, 33}

# Days that are master numbers — kept whole in the primary sum (not digit-split)
MASTER_DAYS = {11, 22, 33}

# Special pre-reduced sums that map to master numbers
# 20 → digits 2+0=2, same reduced form as 11; treated as 11's special case
# 40 → digits 4+0=4, same reduced form as 22
# 60 → digits 6+0=6, same reduced form as 33
SPECIAL_MASTER_MAP = {
    20: 11,
    40: 22,
    60: 33,
}

# ============================================================
# DEFAULT CONTENT — seeded into DB on first use if no entry exists
# ============================================================

DEFAULT_NUMBER_DESCS = {
    1:  "1 is the number of the leader, of masculine energy. Expect people to be arguing more, more road rage, and dominant energy today.",
    2:  "2 is the number of feminine energy, more diplomatic and peaceful. 2 is also a hidden 11 (1+1=2). 11 is a master number, the number of the guide/visionary. It is a good day to start or release something that you want to be influential. It is also a number of emotionality, people could be more emotional today. It is often a day chosen for important events that shock people, so beware.",
    3:  "3 is a number of communication. It's a good day to be social.",
    4:  "4 is the number of hard work and law and order. Work hard and avoid problems with the law.",
    5:  "5 is the number of change, freedom, travelling, health, and sex. If you have difficulties procreating, today might work. Beware cheaters: travelling and sex can go together.",
    6:  "6 is the number of family and home, and services.",
    7:  "7 is the number of intelligence, knowledge, of the loner, but also injuries, and the unlucky number, of the gambler. Avoid working out today to avoid injuries. Spend some time alone to reflect, and learn. Don't get married or gamble on a 7 day.",
    8:  "8 is the number of power, money and karma. Work on making money in priority on that day.",
    9:  (
        "9 is the number of completion and endings — when 9 enters a situation, everything either becomes a better version of itself or is brought to its conclusion. "
        "9 is also the ultimate number of manifestation: it is the number of reality and illusion, and keeping 9 energy close amplifies your ability to attract what you want. "
        "9 is one of the smarter numbers — a good leader and a good follower (the Vice President to 1's President). "
        "9 represents the end of the separation between master numbers (11, 22, 33) and non-master numbers (1–8), making it secretly the most masterful of all. "
        "9 is strongly linked to 2 (Femi-NINE). It is adaptable and quick on its feet. "
        "Warning: Do not marry or start a relationship on 9 days or dates."
    ),
    11: "11 is a master number, the number of the guide/visionary. It is a good day to start or release something that you want to be influential. It is also a number of emotionality, people could be more emotional today. It is often a day chosen for important events that shock people, so beware (of how you perceive events, if you go out, ...). Avoid flying on 11 days — technology may not work as reliably.",
    22: "22 is the number of the master builder, or destroyer.",
    33: "33 is the number of the master teacher. It is a very influential number.",
}

DEFAULT_COMBOS = {
    # (primary, secondary): combo_desc
    (3, 8):   "Work on making money (8) through communication (3).\nNetwork and socialize (3) to build wealth (8).",
    (5, 1):   "Start (1) planning a travel (5).\nTravel (5) and beware of road rage tendencies (1).\nAthletic (1) sex (5).\nStart (1) health (5) programs.",
    (6, 2):   "Seek harmony (2) with your family (6) — a good moment to make up.\nA 6 day or date could be good to marry. The other main number of the date confers properties to the relationship (11+6: more emotional, 5+6: more sensual, etc.).",
    (7, 3):   "Learn (7) how to improve your communication (3).\nCommunicate (3) on knowledge and intelligence (7).\nTeach (7) to a group of people (3).\nWarning: Do not marry or start a relationship on 7 or 9 days or dates.\nWarning: Avoid intense exercise on 7 days.",
    (8, 4):   "Work hard (4) to make money (8).\nPay (8) your bills or fees (4).\nWarning: Avoid breaking the law, especially on 4 days — higher chances of it backfiring.",
    (11, 7):  "Take an action related to knowledge or intelligence or teaching (7) that you want to be influential (11).\nThe 11 could emphasize the characteristics of the 7.\nWarning: Do not marry or start a relationship on 7 or 9 days or dates.\nWarning: Avoid intense exercise on 7 days.\nWarning: Avoid flying on 11 days — technology may not work as reliably.",
    (22, 9):  "Warning: Do not marry or start a relationship on 7 or 9 days or dates.",
    (33, 22): "Both master numbers — this is perhaps the most powerful combination possible.\nBuild (22) a pioneering project (33).",
}


def _digit_sum(n: int) -> int:
    """Sum all digits of n."""
    return sum(int(d) for d in str(n))


def _reduce_to_numerology(n: int) -> tuple:
    """
    Reduce n to a numerology number, preserving master numbers.
    Returns (reduced, unreduced_original).
    """
    unreduced = n

    if unreduced in SPECIAL_MASTER_MAP:
        return SPECIAL_MASTER_MAP[unreduced], unreduced

    if unreduced in MASTER_NUMBERS:
        return unreduced, unreduced

    if 1 <= unreduced <= 9:
        return unreduced, unreduced

    while True:
        reduced = _digit_sum(unreduced)

        if reduced in MASTER_NUMBERS:
            return reduced, unreduced

        if reduced in SPECIAL_MASTER_MAP:
            return SPECIAL_MASTER_MAP[reduced], unreduced

        if 1 <= reduced <= 9:
            return reduced, unreduced

        unreduced = reduced


def _primary_raw_sum(d: date) -> int:
    """
    Compute the raw digit sum for the primary (universal day) number.
    Rule: if the day number itself is a master number (11, 22, 33), add it
    as a whole rather than splitting into digits. All other components split normally.
    """
    if d.day in MASTER_DAYS:
        day_part = d.day
    else:
        day_part = sum(int(ch) for ch in str(d.day))

    month_part = sum(int(ch) for ch in str(d.month))
    year_part  = sum(int(ch) for ch in str(d.year))
    return day_part + month_part + year_part


def calculate_primary(d: date) -> dict:
    """
    Primary (Universal Day) = sum of digits of day + month + year.
    Master-number days (11, 22, 33) contribute their full value, not digit-sum.
    Returns {reduced, unreduced}.
    """
    raw_sum = _primary_raw_sum(d)
    reduced, unreduced = _reduce_to_numerology(raw_sum)
    return {"reduced": reduced, "unreduced": unreduced}


def calculate_secondary(d: date) -> dict:
    """
    Secondary = reduce the day number.
    Master-number days are preserved as master numbers.
    Returns {reduced, unreduced}.
    """
    if d.day in MASTER_DAYS:
        return {"reduced": d.day, "unreduced": d.day}
    raw_sum = sum(int(ch) for ch in str(d.day))
    reduced, unreduced = _reduce_to_numerology(raw_sum)
    return {"reduced": reduced, "unreduced": unreduced}


def calculate_numerology(d: date) -> dict:
    """Full numerology calculation for a given date."""
    return {
        "primary": calculate_primary(d),
        "secondary": calculate_secondary(d),
        "date_str": f"{d.month}/{d.day}/{d.year}",
    }


def format_primary_label(primary: dict) -> str:
    """Format like '3/21' or '11/20' or '33' (if reduced==unreduced)."""
    r, u = primary["reduced"], primary["unreduced"]
    if r == u:
        return str(r)
    return f"{r}/{u}"


def format_secondary_label(secondary: dict) -> str:
    """Format like '8' or '22'."""
    r, u = secondary["reduced"], secondary["unreduced"]
    if r == u:
        return str(r)
    return f"{r}/{u}"


def _display_digits(n: int, keep_whole: bool = False) -> list:
    """
    Return list of display tokens for n.
    Zeros are omitted from display (they don't change the sum).
    If keep_whole=True, return [n] as a single token.
    """
    if keep_whole:
        return [n]
    return [int(ch) for ch in str(n) if ch != '0']


def build_digit_chain_primary(d: date) -> str:
    """
    Build the display digit chain for the primary number.
    Zeros are omitted from display. Master-number days shown whole.
    Example: Oct 22 2026 → '22 + 1 + 2 + 2 + 6\n= 33'
    Example: Mar 26 2026 → '2 + 6 + 3 + 2 + 2 + 6\n= 21\n2 + 1\n= 3'
    """
    is_master_day = d.day in MASTER_DAYS

    day_tokens   = _display_digits(d.day, keep_whole=is_master_day)
    month_tokens = _display_digits(d.month)
    year_tokens  = _display_digits(d.year)

    all_tokens = day_tokens + month_tokens + year_tokens
    raw_sum = _primary_raw_sum(d)
    reduced, _ = _reduce_to_numerology(raw_sum)

    lines = [" + ".join(str(x) for x in all_tokens), f"= {raw_sum}"]

    if raw_sum in SPECIAL_MASTER_MAP:
        master = SPECIAL_MASTER_MAP[raw_sum]
        r_digits = [int(ch) for ch in str(raw_sum) if ch != '0']
        if r_digits:
            lines.append(" + ".join(str(x) for x in r_digits))
        lines.append(f"= {master}")
        lines.append(f"{raw_sum} is a special case of {master} number")
    elif raw_sum not in MASTER_NUMBERS and raw_sum > 9:
        r_digits = [int(ch) for ch in str(raw_sum) if ch != '0']
        if r_digits:
            lines.append(" + ".join(str(x) for x in r_digits))
        lines.append(f"= {reduced}")

    return "\n".join(lines)


def build_digit_chain_secondary(d: date) -> str:
    """
    Build the display digit chain for the secondary (day) number.
    """
    if d.day in MASTER_DAYS:
        return f"{d.day}\n= {d.day}"

    digits = [int(ch) for ch in str(d.day) if ch != '0']
    raw_sum = sum(int(ch) for ch in str(d.day))
    reduced, _ = _reduce_to_numerology(raw_sum)

    lines = [" + ".join(str(x) for x in digits), f"= {raw_sum}"]
    if raw_sum != reduced:
        r_digits = [int(ch) for ch in str(raw_sum) if ch != '0']
        if r_digits:
            lines.append(" + ".join(str(x) for x in r_digits))
        lines.append(f"= {reduced}")
    return "\n".join(lines)


# Single brand color for all numerology embeds — red/orange blend
NUMEROLOGY_COLOR = 0xE8490F


def _truncate(text: str, limit: int = 1024) -> str:
    """Truncate to Discord field value limit."""
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


async def get_embed(d: date, db_module, label: str = "") -> "discord.Embed":
    """
    Build a rich discord.Embed for the numerology reading of a given date.
    label: e.g. "Daily Numerology Reading 🌅" or "Tomorrow's Preview 🌙"
    """
    import discord as _discord  # imported here so numerology.py stays bot-independent

    nums = calculate_numerology(d)
    p = nums["primary"]["reduced"]
    s = nums["secondary"]["reduced"]
    p_full = format_primary_label(nums["primary"])
    s_full = format_secondary_label(nums["secondary"])
    date_str = nums["date_str"]

    chain_p = build_digit_chain_primary(d)
    chain_s = build_digit_chain_secondary(d)

    p_desc = await db_module.get_numerology_number_desc(p)
    if not p_desc:
        p_desc = DEFAULT_NUMBER_DESCS.get(p, f"*(No description set for {p} yet)*")

    s_desc = await db_module.get_numerology_number_desc(s)
    if not s_desc:
        s_desc = DEFAULT_NUMBER_DESCS.get(s, f"*(No description set for {s} yet)*")

    combo_desc = await db_module.get_numerology_combo(p, s)
    if not combo_desc:
        combo_desc = DEFAULT_COMBOS.get((p, s), "*(No combination reading yet — add it in the dashboard)*")

    color = NUMEROLOGY_COLOR

    is_tomorrow = "tomorrow" in label.lower() if label else False
    title_prefix = "TOMORROW" if is_tomorrow else "TODAY"

    embed = _discord.Embed(
        title=f"{title_prefix}: {date_str}",
        color=color,
    )

    # Primary number block
    embed.add_field(
        name=f"🔢 Universal Day: **{p_full}**",
        value=f"```\n{chain_p}\n{p_full}\n```\n{_truncate(p_desc, 800)}",
        inline=False,
    )

    # Secondary number block
    embed.add_field(
        name=f"🔢 Secondary: **{s_full}**",
        value=f"```\n{chain_s}\n{s_full}\n```\n{_truncate(s_desc, 800)}",
        inline=False,
    )

    # Combination
    embed.add_field(
        name="✨ Combination",
        value=_truncate(combo_desc, 1024),
        inline=False,
    )

    embed.set_footer(text="Apeiron")
    return embed


async def get_reading(d: date, db_module) -> str:
    """
    Plain-text version of the reading (used by the dashboard preview API).
    """
    nums = calculate_numerology(d)
    p = nums["primary"]["reduced"]
    s = nums["secondary"]["reduced"]
    p_full = format_primary_label(nums["primary"])
    s_full = format_secondary_label(nums["secondary"])
    date_str = nums["date_str"]

    chain_p = build_digit_chain_primary(d)
    chain_s = build_digit_chain_secondary(d)

    p_desc = await db_module.get_numerology_number_desc(p)
    if not p_desc:
        p_desc = DEFAULT_NUMBER_DESCS.get(p, f"*(No description set for {p} yet)*")

    s_desc = await db_module.get_numerology_number_desc(s)
    if not s_desc:
        s_desc = DEFAULT_NUMBER_DESCS.get(s, f"*(No description set for {s} yet)*")

    combo_desc = await db_module.get_numerology_combo(p, s)
    if not combo_desc:
        combo_desc = DEFAULT_COMBOS.get((p, s), f"*(No combination reading set for {p}+{s} yet)*")

    return "\n".join([
        f"📅 **{date_str}**",
        "",
        f"🔢 Universal Day: **{p_full}**",
        f"```\n{chain_p}\n{p_full}\n```",
        p_desc,
        "",
        f"🔢 Secondary: **{s_full}**",
        f"```\n{chain_s}\n{s_full}\n```",
        s_desc,
        "",
        "✨ **Combination:**",
        combo_desc,
    ])


if __name__ == "__main__":
    tests = [
        (date(2026, 3, 26),  "3/21",  "8"),   # primary=3, secondary=8
        (date(2026, 3, 21),  "7/16",  "3"),   # primary=7, secondary=3
        (date(2026, 3, 25),  "11/20", "7"),   # primary=11, secondary=7
        (date(2026, 3,  1),  "5/14",  "1"),   # primary=5, secondary=1
        (date(2026, 3,  2),  "6/15",  "2"),   # primary=6, secondary=2
        (date(2026, 3,  4),  "8/17",  "4"),   # primary=8, secondary=4
        (date(2026, 3,  9),  "22",    "9"),   # primary=22, secondary=9
        (date(2026, 10, 22), "33",    "22"),  # primary=33, secondary=22 (master day)
    ]
    all_pass = True
    for dt, exp_p, exp_s in tests:
        nums = calculate_numerology(dt)
        p_label = format_primary_label(nums["primary"])
        s_label = format_secondary_label(nums["secondary"])
        ok_p = p_label == exp_p
        ok_s = s_label == exp_s
        status = "✅" if (ok_p and ok_s) else "❌"
        if not (ok_p and ok_s):
            all_pass = False
        print(f"{status} {dt}  primary={p_label!r} (exp {exp_p!r})  secondary={s_label!r} (exp {exp_s!r})")
        if not ok_p or not ok_s:
            print(f"   Chain P: {build_digit_chain_primary(dt)!r}")
    print()
    print("✅ All tests passed!" if all_pass else "❌ Some tests failed.")

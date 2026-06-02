"""Curated catalog of teacher recognition awards.

Each preset defines the award label, FontAwesome icon, color accent, and the
default XP value. The view enforces award_type ∈ AWARD_PRESETS and uses the
preset's xp value (teachers cannot mint arbitrary XP per recognition).
"""

AWARD_PRESETS = {
    "outstanding_work": {
        "label": "Outstanding Work",
        "icon": "fa-solid fa-star",
        "color": "#b7925a",
        "xp": 50,
        "blurb": "Exceptional effort that stood out.",
    },
    "perfect_score": {
        "label": "Perfect Score",
        "icon": "fa-solid fa-medal",
        "color": "#d4a373",
        "xp": 50,
        "blurb": "Aced an assessment with no mistakes.",
    },
    "early_passing": {
        "label": "Early Passing Assessment",
        "icon": "fa-solid fa-stopwatch",
        "color": "#5f8a72",
        "xp": 50,
        "blurb": "Passed an assessment well ahead of the deadline.",
    },
    "always_present": {
        "label": "Always Present",
        "icon": "fa-solid fa-calendar-check",
        "color": "#1b4332",
        "xp": 25,
        "blurb": "Consistent attendance across the period.",
    },
    "early_bird": {
        "label": "Early Bird",
        "icon": "fa-solid fa-sun",
        "color": "#e3a857",
        "xp": 10,
        "blurb": "First to arrive or first to submit.",
    },
    "most_improved": {
        "label": "Most Improved",
        "icon": "fa-solid fa-chart-line",
        "color": "#3a7d44",
        "xp": 25,
        "blurb": "Notable growth since the last checkpoint.",
    },
    "helpful_peer": {
        "label": "Helpful Peer",
        "icon": "fa-solid fa-handshake",
        "color": "#7a9e9f",
        "xp": 25,
        "blurb": "Supported classmates with their learning.",
    },
    "great_question": {
        "label": "Great Question",
        "icon": "fa-solid fa-lightbulb",
        "color": "#e9b44c",
        "xp": 10,
        "blurb": "Asked a question that sparked discussion.",
    },
    "creative_thinker": {
        "label": "Creative Thinker",
        "icon": "fa-solid fa-palette",
        "color": "#9b5de5",
        "xp": 25,
        "blurb": "Brought a fresh perspective to the problem.",
    },
    "team_player": {
        "label": "Team Player",
        "icon": "fa-solid fa-users",
        "color": "#4f6d7a",
        "xp": 25,
        "blurb": "Strong collaboration with the group.",
    },
}


def preset_list():
    """Return presets as an ordered list of dicts including the key."""
    return [{"key": k, **v} for k, v in AWARD_PRESETS.items()]

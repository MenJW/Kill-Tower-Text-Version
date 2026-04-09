from __future__ import annotations

from typing import Callable

from kill_tower.engine.cards.scripts import (
    bash_script,
    bodyguard_script,
    defend_script,
    dualcast_script,
    falling_star_script,
    neutralize_script,
    pacts_end_script,
    squeeze_script,
    strike_script,
    survivor_script,
    unsupported_card_script,
    unleash_script,
    venerate_script,
    zap_script,
)
from kill_tower.engine.state_models import CardInstance, MonsterState

CardScript = Callable[[object, CardInstance, MonsterState | None], None]

CARD_SCRIPTS: dict[str, CardScript] = {
    "strike-ironclad": strike_script,
    "defend-ironclad": defend_script,
    "bash": bash_script,
    "neutralize": neutralize_script,
    "survivor": survivor_script,
    "falling-star": falling_star_script,
    "venerate": venerate_script,
    "zap": zap_script,
    "dualcast": dualcast_script,
    "bodyguard": bodyguard_script,
    "unleash": unleash_script,
    "pacts-end": pacts_end_script,
    "squeeze": squeeze_script,
}


def resolve_card_script(card_id: str) -> CardScript:
    if card_id.startswith("strike-"):
        return strike_script
    if card_id.startswith("defend-"):
        return defend_script
    return CARD_SCRIPTS.get(card_id, unsupported_card_script)
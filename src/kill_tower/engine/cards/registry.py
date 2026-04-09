from __future__ import annotations

from typing import Callable

from kill_tower.engine.cards.scripts import bash_script, defend_script, strike_script, unsupported_card_script
from kill_tower.engine.state_models import CardInstance, MonsterState

CardScript = Callable[[object, CardInstance, MonsterState | None], None]

CARD_SCRIPTS: dict[str, CardScript] = {
    "strike-ironclad": strike_script,
    "defend-ironclad": defend_script,
    "bash": bash_script,
}


def resolve_card_script(card_id: str) -> CardScript:
    return CARD_SCRIPTS.get(card_id, unsupported_card_script)
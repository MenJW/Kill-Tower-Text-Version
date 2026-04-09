from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AscensionRules:
    level: int = 0
    more_elites: bool = False
    campfire_heal_multiplier: float = 1.0
    gold_multiplier: float = 1.0
    max_potion_slots: int = 3
    starting_curse_id: str | None = None
    fewer_rest_sites: bool = False
    rare_cards_less_often: bool = False
    enemy_hp_scale: float = 1.0
    enemy_damage_scale: float = 1.0
    double_boss_act3: bool = False


class AscensionService:
    def rules_for_level(self, level: int) -> AscensionRules:
        resolved_level = max(0, level)
        return AscensionRules(
            level=resolved_level,
            more_elites=resolved_level >= 1,
            campfire_heal_multiplier=0.8 if resolved_level >= 2 else 1.0,
            gold_multiplier=0.75 if resolved_level >= 3 else 1.0,
            max_potion_slots=2 if resolved_level >= 4 else 3,
            starting_curse_id="ascenders-bane" if resolved_level >= 5 else None,
            fewer_rest_sites=resolved_level >= 6,
            rare_cards_less_often=resolved_level >= 7,
            enemy_hp_scale=1.15 if resolved_level >= 8 else 1.0,
            enemy_damage_scale=1.15 if resolved_level >= 9 else 1.0,
            double_boss_act3=resolved_level >= 10,
        )
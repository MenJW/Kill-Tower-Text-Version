from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from kill_tower.data.loader import load_collection
from kill_tower.data.schemas import (
    AchievementDefinition,
    ActDefinition,
    AfflictionDefinition,
    CardDefinition,
    CharacterDefinition,
    EnchantmentDefinition,
    EncounterDefinition,
    EventDefinition,
    IntentDefinition,
    KeywordDefinition,
    ModifierDefinition,
    MonsterDefinition,
    OrbDefinition,
    PotionDefinition,
    PowerDefinition,
    RelicDefinition,
    AscensionDefinition,
)

ItemT = TypeVar("ItemT")


@dataclass(slots=True)
class ContentRegistry:
    characters: dict[str, CharacterDefinition] = field(default_factory=dict)
    cards: dict[str, CardDefinition] = field(default_factory=dict)
    relics: dict[str, RelicDefinition] = field(default_factory=dict)
    potions: dict[str, PotionDefinition] = field(default_factory=dict)
    enchantments: dict[str, EnchantmentDefinition] = field(default_factory=dict)
    monsters: dict[str, MonsterDefinition] = field(default_factory=dict)
    events: dict[str, EventDefinition] = field(default_factory=dict)
    encounters: dict[str, EncounterDefinition] = field(default_factory=dict)
    powers: dict[str, PowerDefinition] = field(default_factory=dict)
    keywords: dict[str, KeywordDefinition] = field(default_factory=dict)
    intents: dict[str, IntentDefinition] = field(default_factory=dict)
    orbs: dict[str, OrbDefinition] = field(default_factory=dict)
    afflictions: dict[str, AfflictionDefinition] = field(default_factory=dict)
    modifiers: dict[str, ModifierDefinition] = field(default_factory=dict)
    acts: dict[str, ActDefinition] = field(default_factory=dict)
    ascensions: dict[str, AscensionDefinition] = field(default_factory=dict)
    achievements: dict[str, AchievementDefinition] = field(default_factory=dict)

    def summary(self) -> dict[str, int]:
        return {
            "characters": len(self.characters),
            "cards": len(self.cards),
            "relics": len(self.relics),
            "potions": len(self.potions),
            "enchantments": len(self.enchantments),
            "monsters": len(self.monsters),
            "events": len(self.events),
            "encounters": len(self.encounters),
            "powers": len(self.powers),
            "keywords": len(self.keywords),
            "intents": len(self.intents),
            "orbs": len(self.orbs),
            "afflictions": len(self.afflictions),
            "modifiers": len(self.modifiers),
            "acts": len(self.acts),
            "ascensions": len(self.ascensions),
            "achievements": len(self.achievements),
        }


def _index_by_id(items: list[ItemT]) -> dict[str, ItemT]:
    return {getattr(item, "id"): item for item in items}


def build_registry(normalized_lang_dir: Path) -> ContentRegistry:
    registry = ContentRegistry()
    files = {
        "characters": ("characters.json", CharacterDefinition),
        "cards": ("cards.json", CardDefinition),
        "relics": ("relics.json", RelicDefinition),
        "potions": ("potions.json", PotionDefinition),
        "enchantments": ("enchantments.json", EnchantmentDefinition),
        "monsters": ("monsters.json", MonsterDefinition),
        "events": ("events.json", EventDefinition),
        "encounters": ("encounters.json", EncounterDefinition),
        "powers": ("powers.json", PowerDefinition),
        "keywords": ("keywords.json", KeywordDefinition),
        "intents": ("intents.json", IntentDefinition),
        "orbs": ("orbs.json", OrbDefinition),
        "afflictions": ("afflictions.json", AfflictionDefinition),
        "modifiers": ("modifiers.json", ModifierDefinition),
        "acts": ("acts.json", ActDefinition),
        "ascensions": ("ascensions.json", AscensionDefinition),
        "achievements": ("achievements.json", AchievementDefinition),
    }
    for attr_name, (file_name, model_type) in files.items():
        file_path = normalized_lang_dir / file_name
        if file_path.exists():
            setattr(registry, attr_name, _index_by_id(load_collection(file_path, model_type)))
    return registry
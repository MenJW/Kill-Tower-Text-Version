from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class ManifestCounts(BaseModel):
    characters: int = 0
    cards: int = 0
    relics: int = 0
    monsters: int = 0
    potions: int = 0
    encounters: int = 0
    events: int = 0
    powers: int = 0
    keywords: int = 0
    acts: int = 0
    ascensions: int = 0
    achievements: int = 0


class SnapshotManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    game: str = "Slay the Spire 2"
    app_id: int = 2868840
    game_version: str = "TBD"
    build_id: str = "TBD"
    snapshot_tag: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sources: list[str] = Field(default_factory=list)
    counts: ManifestCounts = Field(default_factory=ManifestCounts)


class LocalizedText(BaseModel):
    name: str
    description: str | None = None


class SourceMeta(BaseModel):
    source_name: str
    source_url: str | None = None
    fetched_at: datetime | None = None
    payload_version: str | None = None


class EntityReference(BaseModel):
    entity_type: str
    entity_id: str


class BaseEntity(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    source_id: str
    texts: dict[str, LocalizedText] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    scripted: bool = False
    implemented: bool = False
    source_meta: SourceMeta | None = None


class CharacterDefinition(BaseEntity):
    max_hp: int = 0
    starting_gold: int = 0
    starting_energy: int = 3
    starter_relics: list[EntityReference] = Field(default_factory=list)
    starter_deck: list[EntityReference] = Field(default_factory=list)


class CardNumbers(BaseModel):
    cost: int | None = None
    damage: int | None = None
    block: int | None = None
    magic: int | None = None


class CardDefinition(BaseEntity):
    character_id: str | None = None
    rarity: str | None = None
    card_type: str | None = None
    target: str | None = None
    upgraded_from: str | None = None
    keywords: list[str] = Field(default_factory=list)
    numbers: CardNumbers = Field(default_factory=CardNumbers)


class RelicDefinition(BaseEntity):
    rarity: str | None = None
    pool: str | None = None
    keywords: list[str] = Field(default_factory=list)


class PotionDefinition(BaseEntity):
    rarity: str | None = None
    pool: str | None = None
    target: str | None = None


class PowerDefinition(BaseEntity):
    power_type: str | None = None
    stack_type: str | None = None


class MonsterMove(BaseModel):
    id: str
    intent: str
    hits: int | None = None
    damage: int | None = None
    block: int | None = None
    description: str | None = None


class MonsterDefinition(BaseEntity):
    monster_type: str | None = None
    hp_min: int | None = None
    hp_max: int | None = None
    moves: list[MonsterMove] = Field(default_factory=list)


class EventOutcome(BaseModel):
    outcome_type: str
    value: str | int | float | None = None
    reference: EntityReference | None = None


class EventChoice(BaseModel):
    id: str
    label: str
    requirement: str | None = None
    outcomes: list[EventOutcome] = Field(default_factory=list)


class EventPage(BaseModel):
    id: str
    body: str
    choices: list[EventChoice] = Field(default_factory=list)


class EventDefinition(BaseEntity):
    event_type: str | None = None
    acts: list[int] = Field(default_factory=list)
    pages: list[EventPage] = Field(default_factory=list)


class EncounterDefinition(BaseEntity):
    act: int | None = None
    room_type: str | None = None
    monsters: list[EntityReference] = Field(default_factory=list)

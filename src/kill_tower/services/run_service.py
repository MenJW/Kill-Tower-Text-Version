from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from kill_tower.data.registry import ContentRegistry
from kill_tower.data.service import DataService, SnapshotBundle
from kill_tower.engine.combat import CombatRuntime
from kill_tower.services.ascension_service import AscensionService
from kill_tower.services.event_service import EventService
from kill_tower.services.map_service import MapService
from kill_tower.services.reward_service import RewardService
from kill_tower.services.replay_service import ReplayLog, ReplayService
from kill_tower.services.save_service import SaveService
from kill_tower.services.shop_service import ShopService


@dataclass(slots=True)
class PlannedRoom:
    floor: int
    act_id: str
    room_type: str
    encounter_id: str | None = None
    event_id: str | None = None


@dataclass(slots=True)
class CampaignPlayerState:
    character_id: str
    name: str
    max_hp: int
    hp: int
    gold: int
    starting_energy: int
    relic_ids: list[str] = field(default_factory=list)
    deck_definition_ids: list[str] = field(default_factory=list)
    potion_ids: list[str] = field(default_factory=list)
    max_potion_slots: int = 3


@dataclass(slots=True)
class RunRecord:
    snapshot_tag: str
    language: str
    seed: int
    ascension_level: int
    act_id: str
    character_id: str
    player: CampaignPlayerState
    rooms: list[PlannedRoom] = field(default_factory=list)
    cards_removed: int = 0
    floor: int = 0
    victory: bool | None = None
    transcript: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunRecord":
        return cls(
            snapshot_tag=str(payload["snapshot_tag"]),
            language=str(payload["language"]),
            seed=int(payload["seed"]),
            ascension_level=int(payload.get("ascension_level", 0)),
            act_id=str(payload["act_id"]),
            character_id=str(payload["character_id"]),
            player=CampaignPlayerState(**payload["player"]),
            rooms=[PlannedRoom(**room_payload) for room_payload in payload.get("rooms", [])],
            cards_removed=int(payload.get("cards_removed", 0)),
            floor=int(payload.get("floor", 0)),
            victory=payload.get("victory"),
            transcript=list(payload.get("transcript", [])),
        )


@dataclass(slots=True)
class AutoRunResult:
    record: RunRecord
    replay: ReplayLog


class RunService:
    def __init__(
        self,
        data_service: DataService | None = None,
        save_service: SaveService | None = None,
    ) -> None:
        self.data_service = data_service or DataService()
        self.save_service = save_service or SaveService()
        self.ascension_service = AscensionService()
        self.map_service = MapService()
        self.reward_service = RewardService()
        self.shop_service = ShopService(self.reward_service)

    def create_run(
        self,
        character_id: str = "ironclad",
        snapshot_tag: str | None = None,
        lang: str = "eng",
        act_id: str | None = None,
        seed: int = 0,
        floors: int | None = None,
        ascension_level: int = 0,
    ) -> RunRecord:
        bundle = self.data_service.load_bundle(snapshot_tag=snapshot_tag, lang=lang)
        resolved_act_id = self._resolve_act_id(bundle.registry, act_id)
        ascension_rules = self.ascension_service.rules_for_level(ascension_level)
        player = self._build_campaign_player(bundle.registry, character_id, ascension_level)
        rooms = [
            PlannedRoom(**payload)
            for payload in self.map_service.plan_rooms(
                bundle.registry,
                resolved_act_id,
                floors=floors,
                seed=seed,
                ascension_rules=ascension_rules,
            )
        ]
        act_name = bundle.registry.acts[resolved_act_id].name or resolved_act_id
        transcript = [f"Run started for {player.name} in {act_name} at Ascension {ascension_level}."]
        return RunRecord(
            snapshot_tag=bundle.snapshot.tag,
            language=bundle.language,
            seed=seed,
            ascension_level=ascension_level,
            act_id=resolved_act_id,
            character_id=character_id,
            player=player,
            rooms=rooms,
            transcript=transcript,
        )

    def run_auto(
        self,
        character_id: str = "ironclad",
        snapshot_tag: str | None = None,
        lang: str = "eng",
        act_id: str | None = None,
        seed: int = 0,
        floors: int | None = 5,
        max_turns: int = 18,
        ascension_level: int = 0,
    ) -> AutoRunResult:
        record = self.create_run(
            character_id=character_id,
            snapshot_tag=snapshot_tag,
            lang=lang,
            act_id=act_id,
            seed=seed,
            floors=floors,
            ascension_level=ascension_level,
        )
        replay = ReplayService(seed=seed)
        replay.record(
            0,
            "run_started",
            {
                "act_id": record.act_id,
                "character_id": character_id,
                "ascension_level": record.ascension_level,
            },
        )
        bundle = self.data_service.load_bundle(snapshot_tag=record.snapshot_tag, lang=record.language)

        while record.victory is None and record.floor < len(record.rooms):
            self.advance_one_floor(record, replay, bundle=bundle, max_turns=max_turns)

        if record.victory is None:
            record.victory = record.player.hp > 0
            if record.victory:
                record.transcript.append("Run slice complete.")
                replay.record(record.floor, "run_complete", {"victory": True})

        return AutoRunResult(record=record, replay=replay.build())

    def advance_one_floor(
        self,
        record: RunRecord,
        replay: ReplayService,
        bundle: SnapshotBundle | None = None,
        max_turns: int = 18,
    ) -> None:
        if record.victory is not None or record.floor >= len(record.rooms):
            return
        resolved_bundle = bundle or self.data_service.load_bundle(
            snapshot_tag=record.snapshot_tag,
            lang=record.language,
        )
        room = record.rooms[record.floor]
        payload = {"room_type": room.room_type}
        if room.encounter_id is not None:
            payload["encounter_id"] = room.encounter_id
        if room.event_id is not None:
            payload["event_id"] = room.event_id
        replay.record(room.floor, "enter_room", payload)
        record.transcript.append(f"Floor {room.floor}: entering {room.room_type} room.")

        if room.room_type in {"monster", "elite", "boss"} and room.encounter_id is not None:
            self._resolve_combat_room(record, room, resolved_bundle, replay, max_turns=max_turns)
        elif room.room_type == "event" and room.event_id is not None:
            self._resolve_event_room(record, room, resolved_bundle, replay)
        elif room.room_type == "merchant":
            self._resolve_merchant_room(record, room, replay)
        elif room.room_type == "campfire":
            self._resolve_campfire_room(record, room, replay)

        if record.victory is False:
            replay.record(room.floor, "run_failed", {"hp": record.player.hp})
            return

        record.floor += 1
        if record.floor == len(record.rooms) and record.victory is None:
            record.victory = record.player.hp > 0
            if record.victory:
                record.transcript.append(f"Completed {record.act_id} run slice.")
                replay.record(record.floor, "run_complete", {"victory": True})

    def save_run(self, slot: str, record: RunRecord, replay: ReplayLog | None = None) -> Path:
        payload = record.to_dict()
        if replay is not None:
            payload["replay"] = replay.to_dict()
        return self.save_service.save_run(slot, payload)

    def load_run(self, slot: str) -> RunRecord:
        return RunRecord.from_dict(self.save_service.load_run(slot))

    def _build_campaign_player(
        self,
        registry: ContentRegistry,
        character_id: str,
        ascension_level: int,
    ) -> CampaignPlayerState:
        character = registry.characters[character_id]
        ascension_rules = self.ascension_service.rules_for_level(ascension_level)
        deck_definition_ids = [ref.entity_id for ref in character.starter_deck]
        if ascension_rules.starting_curse_id is not None:
            deck_definition_ids.append(ascension_rules.starting_curse_id)
        return CampaignPlayerState(
            character_id=character.id,
            name=character.name or character_id,
            max_hp=character.max_hp,
            hp=character.max_hp,
            gold=character.starting_gold,
            starting_energy=character.starting_energy,
            relic_ids=[ref.entity_id for ref in character.starter_relics],
            deck_definition_ids=deck_definition_ids,
            max_potion_slots=ascension_rules.max_potion_slots,
        )

    def _build_room_plan(
        self,
        registry: ContentRegistry,
        act_id: str,
        floors: int | None,
        seed: int,
    ) -> list[PlannedRoom]:
        act = registry.acts[act_id]
        room_count = act.num_rooms or 0
        if room_count <= 0:
            raise ValueError(f"Act {act_id} has no room count.")
        planned_count = room_count if floors is None else min(floors, room_count)
        full_route = planned_count == room_count

        monster_ids = self._sorted_encounter_ids(registry, act_id, room_type="Monster")
        elite_ids = self._sorted_encounter_ids(registry, act_id, room_type="Elite")
        boss_ids = self._sorted_boss_ids(registry, act_id)
        event_ids = [ref.entity_id for ref in act.events if ref.entity_id in registry.events]

        monster_offset = seed % len(monster_ids) if monster_ids else 0
        elite_offset = seed % len(elite_ids) if elite_ids else 0
        boss_offset = seed % len(boss_ids) if boss_ids else 0
        event_offset = seed % len(event_ids) if event_ids else 0

        monster_cursor = 0
        elite_cursor = 0
        event_cursor = 0
        rooms: list[PlannedRoom] = []
        for floor in range(1, planned_count + 1):
            if full_route and floor == planned_count and boss_ids:
                encounter_id = boss_ids[(boss_offset + floor - 1) % len(boss_ids)]
                rooms.append(PlannedRoom(floor=floor, act_id=act_id, room_type="boss", encounter_id=encounter_id))
                continue
            if floor in {4, 9, 14} and event_ids:
                event_id = event_ids[(event_offset + event_cursor) % len(event_ids)]
                event_cursor += 1
                rooms.append(PlannedRoom(floor=floor, act_id=act_id, room_type="event", event_id=event_id))
                continue
            if floor in {5, 10}:
                rooms.append(PlannedRoom(floor=floor, act_id=act_id, room_type="merchant"))
                continue
            if floor in {6, 12}:
                rooms.append(PlannedRoom(floor=floor, act_id=act_id, room_type="campfire"))
                continue
            if floor in {7, 13} and elite_ids:
                encounter_id = elite_ids[(elite_offset + elite_cursor) % len(elite_ids)]
                elite_cursor += 1
                rooms.append(PlannedRoom(floor=floor, act_id=act_id, room_type="elite", encounter_id=encounter_id))
                continue
            if not monster_ids:
                raise ValueError(f"Act {act_id} has no monster encounters.")
            encounter_id = monster_ids[(monster_offset + monster_cursor) % len(monster_ids)]
            monster_cursor += 1
            rooms.append(PlannedRoom(floor=floor, act_id=act_id, room_type="monster", encounter_id=encounter_id))
        return rooms

    def _resolve_combat_room(
        self,
        record: RunRecord,
        room: PlannedRoom,
        bundle: SnapshotBundle,
        replay: ReplayService,
        max_turns: int,
    ) -> None:
        ascension_rules = self.ascension_service.rules_for_level(record.ascension_level)
        runtime = CombatRuntime(
            registry=bundle.registry,
            seed=record.seed + room.floor * 997,
            snapshot_tag=record.snapshot_tag,
            enemy_hp_scale=ascension_rules.enemy_hp_scale,
            enemy_damage_scale=ascension_rules.enemy_damage_scale,
        )
        player_state = runtime.build_player_state(
            character_id=record.character_id,
            current_hp=record.player.hp,
            max_hp=record.player.max_hp,
            gold=record.player.gold,
            relic_ids=record.player.relic_ids,
            deck_definition_ids=record.player.deck_definition_ids,
        )
        result = runtime.run_encounter(
            encounter_id=room.encounter_id or "",
            character_id=record.character_id,
            player_state=player_state,
            max_turns=max_turns,
            shuffle_draw_pile=False,
        )
        record.transcript.extend(result.transcript)
        record.player.hp = result.player_hp
        record.player.max_hp = result.max_player_hp
        replay.record(
            room.floor,
            "combat_resolved",
            {
                "encounter_id": room.encounter_id or "",
                "victory": result.victory,
                "hp": result.player_hp,
            },
        )
        if not result.victory:
            record.victory = False
            record.transcript.append(f"Run failed on floor {room.floor}.")
            return
        gold_reward = self.reward_service.gold_reward(room.room_type, ascension_rules)
        if gold_reward > 0:
            record.player.gold += gold_reward
            record.transcript.append(f"Floor {room.floor}: gained {gold_reward} gold.")
        record.transcript.extend(
            self.reward_service.apply_combat_rewards(
                record.player,
                record.character_id,
                bundle.registry,
                room.room_type,
                seed=record.seed,
                floor=room.floor,
                ascension_rules=ascension_rules,
            )
        )

    def _resolve_event_room(
        self,
        record: RunRecord,
        room: PlannedRoom,
        bundle: SnapshotBundle,
        replay: ReplayService,
    ) -> None:
        event = bundle.registry.events[room.event_id or ""]
        record.transcript.append(f"Event: {event.name or event.id}")
        resolution = EventService(bundle.registry).resolve_auto(event.id, record.player)
        record.transcript.extend(resolution.transcript)
        record.transcript.extend(resolution.applied_outcomes)
        replay.record(
            room.floor,
            "event_resolved",
            {
                "event_id": event.id,
                "choices": resolution.chosen_options,
                "hp": record.player.hp,
                "gold": record.player.gold,
            },
        )
        if record.player.hp <= 0:
            record.victory = False
            record.transcript.append(f"Run failed in event {event.id}.")

    def _resolve_merchant_room(self, record: RunRecord, room: PlannedRoom, replay: ReplayService) -> None:
        bundle = self.data_service.load_bundle(snapshot_tag=record.snapshot_tag, lang=record.language)
        ascension_rules = self.ascension_service.rules_for_level(record.ascension_level)
        messages, cards_removed = self.shop_service.resolve_merchant(
            record.player,
            record.character_id,
            bundle.registry,
            seed=record.seed,
            floor=room.floor,
            ascension_rules=ascension_rules,
            cards_removed=record.cards_removed,
        )
        record.cards_removed = cards_removed
        record.transcript.extend(messages)
        replay.record(
            room.floor,
            "merchant_resolved",
            {"gold": record.player.gold, "cards_removed": record.cards_removed},
        )

    def _resolve_campfire_room(self, record: RunRecord, room: PlannedRoom, replay: ReplayService) -> None:
        ascension_rules = self.ascension_service.rules_for_level(record.ascension_level)
        previous_hp = record.player.hp
        heal_amount = max(1, int(record.player.max_hp * 0.3 * ascension_rules.campfire_heal_multiplier))
        record.player.hp = min(record.player.max_hp, record.player.hp + heal_amount)
        actual_heal = record.player.hp - previous_hp
        record.transcript.append(f"Campfire heals {record.player.name} for {actual_heal} HP.")
        replay.record(room.floor, "campfire_resolved", {"healed": actual_heal, "hp": record.player.hp})

    def _resolve_act_id(self, registry: ContentRegistry, act_id: str | None) -> str:
        if act_id is not None:
            if act_id not in registry.acts:
                raise KeyError(f"Unknown act id: {act_id}")
            return act_id
        if "underdocks" in registry.acts:
            return "underdocks"
        return next(iter(sorted(registry.acts)))

    def _sorted_encounter_ids(
        self,
        registry: ContentRegistry,
        act_id: str,
        room_type: str,
    ) -> list[str]:
        act = registry.acts[act_id]
        encounter_ids = [
            ref.entity_id
            for ref in act.encounters
            if ref.entity_id in registry.encounters
            and registry.encounters[ref.entity_id].room_type == room_type
        ]
        return sorted(encounter_ids, key=lambda encounter_id: (self._encounter_difficulty(registry, encounter_id), encounter_id))

    def _sorted_boss_ids(self, registry: ContentRegistry, act_id: str) -> list[str]:
        act = registry.acts[act_id]
        boss_ids = [ref.entity_id for ref in act.bosses if ref.entity_id in registry.encounters]
        return sorted(boss_ids, key=lambda encounter_id: (self._encounter_difficulty(registry, encounter_id), encounter_id))

    def _encounter_difficulty(self, registry: ContentRegistry, encounter_id: str) -> int:
        encounter = registry.encounters[encounter_id]
        total_hp = 0
        for monster_ref in encounter.monsters:
            monster = registry.monsters[monster_ref.entity_id]
            total_hp += monster.hp_min or monster.hp_max or 1
        return total_hp + max(0, len(encounter.monsters) - 1) * 5

    def _gold_reward(self, room_type: str) -> int:
        rewards = {"monster": 20, "elite": 35, "boss": 100}
        return rewards.get(room_type, 0)
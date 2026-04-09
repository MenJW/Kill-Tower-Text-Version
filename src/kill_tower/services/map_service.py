from __future__ import annotations

from typing import Any

from kill_tower.data.registry import ContentRegistry
from kill_tower.services.ascension_service import AscensionRules


class MapService:
    def plan_rooms(
        self,
        registry: ContentRegistry,
        act_id: str,
        floors: int | None,
        seed: int,
        ascension_rules: AscensionRules,
    ) -> list[dict[str, Any]]:
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

        elite_floors = {7, 13}
        if ascension_rules.more_elites:
            elite_floors.add(3)
        campfire_floors = {6, 12}
        if ascension_rules.fewer_rest_sites:
            campfire_floors = {12}
        merchant_floors = {5, 10}
        event_floors = {4, 9, 14}

        monster_cursor = 0
        elite_cursor = 0
        event_cursor = 0
        rooms: list[dict[str, Any]] = []
        for floor in range(1, planned_count + 1):
            if full_route and boss_ids:
                if ascension_rules.double_boss_act3 and act_id == "overgrowth" and floor >= planned_count - 1:
                    encounter_id = boss_ids[(boss_offset + floor - 1) % len(boss_ids)]
                    rooms.append({"floor": floor, "act_id": act_id, "room_type": "boss", "encounter_id": encounter_id})
                    continue
                if floor == planned_count:
                    encounter_id = boss_ids[(boss_offset + floor - 1) % len(boss_ids)]
                    rooms.append({"floor": floor, "act_id": act_id, "room_type": "boss", "encounter_id": encounter_id})
                    continue
            if floor in event_floors and event_ids:
                event_id = event_ids[(event_offset + event_cursor) % len(event_ids)]
                event_cursor += 1
                rooms.append({"floor": floor, "act_id": act_id, "room_type": "event", "event_id": event_id})
                continue
            if floor in merchant_floors:
                rooms.append({"floor": floor, "act_id": act_id, "room_type": "merchant"})
                continue
            if floor in campfire_floors:
                rooms.append({"floor": floor, "act_id": act_id, "room_type": "campfire"})
                continue
            if floor in elite_floors and elite_ids:
                encounter_id = elite_ids[(elite_offset + elite_cursor) % len(elite_ids)]
                elite_cursor += 1
                rooms.append({"floor": floor, "act_id": act_id, "room_type": "elite", "encounter_id": encounter_id})
                continue
            if not monster_ids:
                raise ValueError(f"Act {act_id} has no monster encounters.")
            encounter_id = monster_ids[(monster_offset + monster_cursor) % len(monster_ids)]
            monster_cursor += 1
            rooms.append({"floor": floor, "act_id": act_id, "room_type": "monster", "encounter_id": encounter_id})
        return rooms

    def _sorted_encounter_ids(self, registry: ContentRegistry, act_id: str, room_type: str) -> list[str]:
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
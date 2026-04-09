from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kill_tower.data.registry import ContentRegistry
from kill_tower.data.schemas import CardDefinition, PotionDefinition, RelicDefinition
from kill_tower.data.service import DataService
from kill_tower.engine.cards import resolve_card_script
from kill_tower.engine.combat import CombatRuntime
from kill_tower.engine.cards.scripts import unsupported_card_script
from kill_tower.engine.relics import resolve_relic_hooks
from kill_tower.engine.state_models import CardInstance


UNRESOLVED_MARKERS = (
    "still has unimplemented clauses",
    "used number-only fallback resolution",
    "has no executable script yet",
    "Unsupported event effect",
)


@dataclass(slots=True)
class CoverageEntry:
    entity_id: str
    name: str | None
    status: str
    detail: str | None = None


@dataclass(slots=True)
class CoverageBucket:
    total: int = 0
    resolved: int = 0
    partial: int = 0
    unresolved: int = 0
    error: int = 0
    entries: list[CoverageEntry] = field(default_factory=list)

    def add(self, entry: CoverageEntry) -> None:
        self.total += 1
        if entry.status == "resolved":
            self.resolved += 1
        elif entry.status == "partial":
            self.partial += 1
        elif entry.status == "unresolved":
            self.unresolved += 1
        else:
            self.error += 1
        if entry.status != "resolved":
            self.entries.append(entry)

    def coverage_ratio(self) -> float:
        if self.total == 0:
            return 1.0
        return self.resolved / self.total


@dataclass(slots=True)
class LanguageCoverageReport:
    snapshot_tag: str
    language: str
    generated_at: str
    cards: CoverageBucket
    relics: CoverageBucket
    potions: CoverageBucket
    events: CoverageBucket
    monsters: CoverageBucket

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_tag": self.snapshot_tag,
            "language": self.language,
            "generated_at": self.generated_at,
            "cards": self._bucket_to_dict(self.cards),
            "relics": self._bucket_to_dict(self.relics),
            "potions": self._bucket_to_dict(self.potions),
            "events": self._bucket_to_dict(self.events),
            "monsters": self._bucket_to_dict(self.monsters),
        }

    def _bucket_to_dict(self, bucket: CoverageBucket) -> dict[str, Any]:
        return {
            "total": bucket.total,
            "resolved": bucket.resolved,
            "partial": bucket.partial,
            "unresolved": bucket.unresolved,
            "error": bucket.error,
            "coverage_ratio": bucket.coverage_ratio(),
            "entries": [asdict(entry) for entry in bucket.entries],
        }


class CoverageService:
    def __init__(self, data_service: DataService | None = None) -> None:
        self.data_service = data_service or DataService()

    def generate_language_report(self, snapshot_tag: str, lang: str) -> LanguageCoverageReport:
        registry = self.data_service.load_registry(snapshot_tag=snapshot_tag, lang=lang)
        generated_at = datetime.now(timezone.utc).isoformat()
        return LanguageCoverageReport(
            snapshot_tag=snapshot_tag,
            language=lang,
            generated_at=generated_at,
            cards=self._analyze_cards(registry, snapshot_tag),
            relics=self._analyze_relics(registry),
            potions=self._analyze_potions(registry, snapshot_tag),
            events=self._analyze_events(registry),
            monsters=self._analyze_monsters(registry),
        )

    def render_markdown(self, reports: list[LanguageCoverageReport]) -> str:
        lines = [
            f"# Unresolved Coverage Report: {reports[0].snapshot_tag}" if reports else "# Unresolved Coverage Report",
            "",
            f"Generated at: {datetime.now(timezone.utc).isoformat()}",
            "",
            "Status policy:",
            "- resolved: executed or structurally covered without unresolved markers",
            "- partial: some effect executed but unresolved markers or unsupported outcomes remain",
            "- unresolved: no executable handling or no structured outcomes",
            "- error: analyzer raised an exception",
            "",
        ]
        for report in reports:
            lines.extend(self._render_language_markdown(report))
        return "\n".join(lines) + "\n"

    def _render_language_markdown(self, report: LanguageCoverageReport) -> list[str]:
        lines = [
            f"## {report.language}",
            "",
            "| Entity | Total | Resolved | Partial | Unresolved | Error | Coverage |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for label, bucket in (
            ("cards", report.cards),
            ("relics", report.relics),
            ("potions", report.potions),
            ("events", report.events),
            ("monsters", report.monsters),
        ):
            lines.append(
                f"| {label} | {bucket.total} | {bucket.resolved} | {bucket.partial} | {bucket.unresolved} | {bucket.error} | {bucket.coverage_ratio():.1%} |"
            )
        lines.append("")
        for label, bucket in (
            ("Cards", report.cards),
            ("Relics", report.relics),
            ("Potions", report.potions),
            ("Events", report.events),
            ("Monsters", report.monsters),
        ):
            if not bucket.entries:
                continue
            lines.append(f"### {label} Needing Attention")
            lines.append("")
            for entry in bucket.entries[:40]:
                detail = f": {entry.detail}" if entry.detail else ""
                lines.append(f"- {entry.entity_id} [{entry.status}]{detail}")
            lines.append("")
        return lines

    def _analyze_cards(self, registry: ContentRegistry, snapshot_tag: str) -> CoverageBucket:
        bucket = CoverageBucket()
        for card in sorted(registry.cards.values(), key=lambda item: item.id):
            bucket.add(self._analyze_card(card, registry, snapshot_tag))
        return bucket

    def _analyze_card(
        self,
        card: CardDefinition,
        registry: ContentRegistry,
        snapshot_tag: str,
    ) -> CoverageEntry:
        runtime = CombatRuntime(registry=registry, seed=17, snapshot_tag=snapshot_tag)
        character_id = card.character_id or "ironclad"
        encounter_id = self._default_encounter_id(registry)
        player_state = runtime.build_player_state(character_id=character_id)
        state = runtime.start_encounter(
            character_id=character_id,
            encounter_id=encounter_id,
            shuffle_draw_pile=False,
            player_state=player_state,
        )
        state.transcript.clear()
        state.player.energy = 10
        state.player.max_energy = 10
        state.player.orbs = ["lightning-orb"]
        state.player.resources = {"osty_hp": 6, "osty_attacks_played": 2}
        state.player.draw_pile = [
            self._make_card_instance(registry, "strike-ironclad", "draw-1"),
            self._make_card_instance(registry, "defend-ironclad", "draw-2"),
        ]
        state.player.discard_pile = [self._make_card_instance(registry, "strike-ironclad", "discard-1")]
        state.player.exhaust_pile = [
            self._make_card_instance(registry, "strike-ironclad", "exhaust-1"),
            self._make_card_instance(registry, "strike-ironclad", "exhaust-2"),
            self._make_card_instance(registry, "strike-ironclad", "exhaust-3"),
        ]
        card_instance = self._make_card_instance(registry, card.id, "under-test")
        state.player.hand = [card_instance, self._make_card_instance(registry, "defend-ironclad", "helper")]
        target = runtime.alive_enemies()[0] if runtime.alive_enemies() else None

        try:
            resolve_card_script(card.id)(runtime, card_instance, target)
        except Exception as exc:  # noqa: BLE001
            return CoverageEntry(card.id, card.name, "error", str(exc))

        detail = self._first_unresolved_detail(state.transcript)
        if detail is None:
            return CoverageEntry(card.id, card.name, "resolved")
        if "has no executable script yet" in detail:
            return CoverageEntry(card.id, card.name, "unresolved", detail)
        return CoverageEntry(card.id, card.name, "partial", detail)

    def _analyze_relics(self, registry: ContentRegistry) -> CoverageBucket:
        bucket = CoverageBucket()
        for relic in sorted(registry.relics.values(), key=lambda item: item.id):
            hooks = resolve_relic_hooks(relic.id)
            if hooks.on_combat_start or hooks.on_player_turn_start or hooks.on_combat_end:
                bucket.add(CoverageEntry(relic.id, relic.name, "resolved"))
            else:
                bucket.add(CoverageEntry(relic.id, relic.name, "unresolved", relic.description))
        return bucket

    def _analyze_potions(self, registry: ContentRegistry, snapshot_tag: str) -> CoverageBucket:
        bucket = CoverageBucket()
        for potion in sorted(registry.potions.values(), key=lambda item: item.id):
            bucket.add(self._analyze_potion(potion, registry, snapshot_tag))
        return bucket

    def _analyze_potion(
        self,
        potion: PotionDefinition,
        registry: ContentRegistry,
        snapshot_tag: str,
    ) -> CoverageEntry:
        runtime = CombatRuntime(registry=registry, seed=23, snapshot_tag=snapshot_tag)
        encounter_id = self._default_encounter_id(registry)
        player_state = runtime.build_player_state(character_id="ironclad", potion_ids=[potion.id])
        state = runtime.start_encounter(
            character_id="ironclad",
            encounter_id=encounter_id,
            shuffle_draw_pile=False,
            player_state=player_state,
        )
        state.transcript.clear()
        state.player.energy = 1
        state.player.hp = max(1, state.player.max_hp // 2)
        state.player.draw_pile = [self._make_card_instance(registry, "strike-ironclad", "draw-potion")]
        state.player.discard_pile = [self._make_card_instance(registry, "bash", "discard-potion")]

        try:
            if potion.id == "fairy-in-a-bottle":
                state.player.hp = 0
                runtime._trigger_death_prevention_potion(state.player)
            else:
                runtime._use_potion(potion.id)
        except Exception as exc:  # noqa: BLE001
            return CoverageEntry(potion.id, potion.name, "error", str(exc))

        if potion.id not in state.player.potion_ids:
            return CoverageEntry(potion.id, potion.name, "resolved")
        return CoverageEntry(potion.id, potion.name, "unresolved", potion.description)

    def _analyze_events(self, registry: ContentRegistry) -> CoverageBucket:
        bucket = CoverageBucket()
        for event in sorted(registry.events.values(), key=lambda item: item.id):
            status = "resolved"
            detail: str | None = None
            has_choice = False
            for page in event.pages:
                for choice in page.choices:
                    has_choice = True
                    if not choice.outcomes and choice.description:
                        status = "unresolved"
                        detail = choice.description
                        break
                    unsupported = [outcome for outcome in choice.outcomes if outcome.outcome_type == "unsupported"]
                    if unsupported and status != "unresolved":
                        status = "partial"
                        detail = unsupported[0].value if isinstance(unsupported[0].value, str) else choice.description
                if status == "unresolved":
                    break
            if not has_choice:
                bucket.add(CoverageEntry(event.id, event.name, "unresolved", "event has no choices"))
            else:
                bucket.add(CoverageEntry(event.id, event.name, status, detail))
        return bucket

    def _analyze_monsters(self, registry: ContentRegistry) -> CoverageBucket:
        bucket = CoverageBucket()
        for monster in sorted(registry.monsters.values(), key=lambda item: item.id):
            if not monster.moves:
                bucket.add(CoverageEntry(monster.id, monster.name, "unresolved", "monster has no moves"))
                continue
            unresolved_move = next(
                (
                    move
                    for move in monster.moves
                    if move.damage is None
                    and move.block is None
                    and move.heal is None
                    and not move.powers
                ),
                None,
            )
            if unresolved_move is not None:
                bucket.add(
                    CoverageEntry(
                        monster.id,
                        monster.name,
                        "partial",
                        unresolved_move.description or unresolved_move.intent,
                    )
                )
                continue
            bucket.add(CoverageEntry(monster.id, monster.name, "resolved"))
        return bucket

    def _default_encounter_id(self, registry: ContentRegistry) -> str:
        if "toadpoles-normal" in registry.encounters:
            return "toadpoles-normal"
        return next(iter(sorted(registry.encounters)))

    def _make_card_instance(self, registry: ContentRegistry, card_id: str, suffix: str) -> CardInstance:
        definition = registry.cards[card_id]
        return CardInstance(
            definition_id=definition.id,
            instance_id=f"{definition.id}-{suffix}",
            cost=definition.numbers.cost or 0,
            name=definition.name,
            card_type=definition.card_type,
        )

    def _first_unresolved_detail(self, transcript: list[str]) -> str | None:
        for line in transcript:
            if any(marker in line for marker in UNRESOLVED_MARKERS):
                return line
        return None

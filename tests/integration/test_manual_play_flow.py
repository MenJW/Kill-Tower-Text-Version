from kill_tower.engine.combat import CombatRuntime
from kill_tower.engine.state_models import CombatPhase
from kill_tower.services.event_service import EventService
from kill_tower.services.run_service import RunService


def test_manual_combat_controls_can_finish_encounter_with_explicit_actions() -> None:
    service = RunService()
    bundle = service.data_service.load_bundle(snapshot_tag="2026-04-09_build_unknown", lang="zhs")
    runtime = CombatRuntime(registry=bundle.registry, seed=11, snapshot_tag=bundle.snapshot.tag)
    player_state = runtime.build_player_state(character_id="ironclad", potion_ids=["energy-potion"])
    state = runtime.start_encounter(
        character_id="ironclad",
        encounter_id="toadpoles-normal",
        shuffle_draw_pile=False,
        player_state=player_state,
    )

    runtime.use_potion(0)

    while state.victory is None and state.turn <= 12:
        if state.phase == CombatPhase.PLAYER:
            played_card = False
            for index, card in list(enumerate(state.player.hand)):
                if not runtime.card_is_playable(card):
                    continue
                definition = runtime.get_card_definition(card)
                target_index = 0 if definition.numbers.damage is not None and runtime.alive_enemies() else None
                runtime.play_card(index, target_index)
                played_card = True
                break
            if not played_card:
                runtime.end_player_turn()
        else:
            runtime.run_enemy_turn()

    assert state.victory is True
    assert "energy-potion" not in state.player.potion_ids
    assert any("uses potion" in line for line in state.transcript)


def test_event_service_apply_choice_uses_selected_manual_branch() -> None:
    service = RunService()
    record = service.create_run(
        character_id="ironclad",
        snapshot_tag="2026-04-09_build_unknown",
        lang="zhs",
        act_id="underdocks",
        seed=7,
        floors=7,
    )
    bundle = service.data_service.load_bundle(snapshot_tag=record.snapshot_tag, lang=record.language)
    event = bundle.registry.events["abyssal-baths"]
    page = next(page for page in event.pages if any(choice.id == "immerse" for choice in page.choices))
    event_service = EventService(bundle.registry)

    choice, messages, next_page = event_service.apply_choice(
        event,
        page,
        "immerse",
        record.player,
        visited_pages={page.id},
    )

    assert choice.id == "immerse"
    assert any("Gain 2 Max HP." in message for message in messages)
    assert any("Take 3 damage." in message for message in messages)
    assert next_page is not None


def test_shop_service_supports_manual_preview_and_purchase_flow() -> None:
    service = RunService()
    record = service.create_run(
        character_id="ironclad",
        snapshot_tag="2026-04-09_build_unknown",
        lang="zhs",
        act_id="underdocks",
        seed=7,
        floors=7,
    )
    bundle = service.data_service.load_bundle(snapshot_tag=record.snapshot_tag, lang=record.language)
    record.player.gold = 300

    offer = service.shop_service.preview_merchant(
        record.player,
        record.character_id,
        bundle.registry,
        seed=record.seed,
        floor=5,
        ascension_rules=service.ascension_service.rules_for_level(record.ascension_level),
        cards_removed=record.cards_removed,
    )

    removal_message, cards_removed = service.shop_service.purchase_removal(record.player, record.cards_removed)

    assert removal_message is not None
    assert cards_removed == 1
    assert offer.card_offer_id is not None

    card_message = service.shop_service.purchase_card(record.player, offer)

    assert card_message is not None
    assert "Merchant sells" in card_message
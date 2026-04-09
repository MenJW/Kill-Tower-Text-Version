from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from kill_tower.data.event_outcomes import resolve_execution_description, strip_markup
from kill_tower.data.service import SnapshotBundle
from kill_tower.engine.combat import CombatRuntime
from kill_tower.engine.state_models import CombatPhase
from kill_tower.services.event_service import EventService

if TYPE_CHECKING:
    from kill_tower.services.run_service import PlannedRoom, RunRecord, RunService


def play_interactive_run(
    console: Console,
    run_service: "RunService",
    character_id: str,
    snapshot_tag: str,
    lang: str,
    act_id: str,
    seed: int,
    floors: int | None,
    ascension_level: int,
) -> "RunRecord":
    record = run_service.create_run(
        character_id=character_id,
        snapshot_tag=snapshot_tag,
        lang=lang,
        act_id=act_id,
        seed=seed,
        floors=floors,
        ascension_level=ascension_level,
    )
    bundle = run_service.data_service.load_bundle(snapshot_tag=record.snapshot_tag, lang=record.language)

    _print_route_preview(console, record)
    console.print("手动模式说明: play <手牌序号> [目标序号]、use <药水序号>、end、help、quit", markup=False)

    while record.victory is None and record.floor < len(record.rooms):
        room = record.rooms[record.floor]
        record.transcript.append(f"Floor {room.floor}: entering {room.room_type} room.")
        console.rule(f"第 {room.floor} 层 · {_room_label(room.room_type)}")

        aborted = False
        if room.room_type in {"monster", "elite", "boss"} and room.encounter_id is not None:
            aborted = _play_combat_room(console, run_service, record, room, bundle)
        elif room.room_type == "event" and room.event_id is not None:
            aborted = _play_event_room(console, record, room, bundle)
        elif room.room_type == "merchant":
            aborted = _play_merchant_room(console, run_service, record, room, bundle)
        elif room.room_type == "campfire":
            aborted = _play_campfire_room(console, run_service, record, room)

        if aborted:
            record.victory = False
            record.transcript.append("Run aborted by player.")
            break
        if record.victory is False:
            break
        record.floor += 1

    if record.victory is None:
        record.victory = record.player.hp > 0
        if record.victory:
            record.transcript.append(f"Completed {record.act_id} run slice.")

    return record


def _play_combat_room(
    console: Console,
    run_service: "RunService",
    record: "RunRecord",
    room: "PlannedRoom",
    bundle: SnapshotBundle,
) -> bool:
    ascension_rules = run_service.ascension_service.rules_for_level(record.ascension_level)
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
        potion_ids=record.player.potion_ids,
    )
    state = runtime.start_encounter(
        character_id=record.character_id,
        encounter_id=room.encounter_id or "",
        shuffle_draw_pile=False,
        player_state=player_state,
    )
    log_cursor = _flush_log(console, state.transcript, 0)

    while state.victory is None:
        if state.phase == CombatPhase.PLAYER:
            _print_combat_state(console, runtime)
            command = _read_command(console, "操作")
            if command in {"quit", "q"}:
                return True
            if command in {"help", "h", "?"}:
                console.print("命令: play <手牌序号> [目标序号] | use <药水序号> | end | quit", markup=False)
                continue
            if command in {"end", "e"}:
                runtime.end_player_turn()
                log_cursor = _flush_log(console, state.transcript, log_cursor)
                continue

            try:
                handled = _handle_combat_command(console, runtime, command)
            except (IndexError, ValueError) as exc:
                console.print(f"无效操作: {exc}", markup=False)
                continue
            if not handled:
                console.print("无法识别命令，输入 help 查看帮助。", markup=False)
                continue
            log_cursor = _flush_log(console, state.transcript, log_cursor)
            continue

        console.print("敌人回合...", markup=False)
        runtime.run_enemy_turn()
        log_cursor = _flush_log(console, state.transcript, log_cursor)

    record.transcript.extend(state.transcript)
    record.player.hp = state.player.hp
    record.player.max_hp = state.player.max_hp
    record.player.gold = state.player.gold
    record.player.potion_ids = list(state.player.potion_ids)
    if not state.victory:
        record.victory = False
        record.transcript.append(f"Run failed on floor {room.floor}.")
        return False

    gold_reward = run_service.reward_service.gold_reward(room.room_type, ascension_rules)
    reward_messages: list[str] = []
    if gold_reward > 0:
        record.player.gold += gold_reward
        reward_messages.append(f"Floor {room.floor}: gained {gold_reward} gold.")
    reward_messages.extend(
        run_service.reward_service.apply_combat_rewards(
            record.player,
            record.character_id,
            bundle.registry,
            room.room_type,
            seed=record.seed,
            floor=room.floor,
            ascension_rules=ascension_rules,
        )
    )
    record.transcript.extend(reward_messages)
    if reward_messages:
        console.print("战斗奖励:", markup=False)
        for line in reward_messages:
            console.print(f"- {line}", markup=False)
    return False


def _play_event_room(
    console: Console,
    record: "RunRecord",
    room: "PlannedRoom",
    bundle: SnapshotBundle,
) -> bool:
    event = bundle.registry.events[room.event_id or ""]
    event_service = EventService(bundle.registry)
    record.transcript.append(f"Event: {event.name or event.id}")
    console.print(f"事件: {event.name or event.id}", markup=False)

    if not event.pages:
        message = f"Event {event.name or event.id} has no structured pages."
        record.transcript.append(message)
        console.print(message, markup=False)
        return False

    page = event.pages[0]
    visited_pages: set[str] = set()
    while page is not None:
        visited_pages.add(page.id)
        if page.body:
            console.print(strip_markup(page.body), markup=False)
            record.transcript.append(page.body)
        if not page.choices:
            break

        available_choices = [
            event_service.choice_is_available(event, page, choice, record.player)
            for choice in page.choices
        ]
        for index, choice in enumerate(page.choices, start=1):
            detail = strip_markup(choice.description or choice.requirement or "")
            locked_suffix = " [不可用]" if not available_choices[index - 1] else ""
            console.print(f"{index}. {choice.label}{locked_suffix}", markup=False)
            if detail:
                console.print(f"   {detail}", markup=False)

        raw_choice = _read_command(console, "事件选项")
        if raw_choice in {"quit", "q"}:
            return True
        if not raw_choice.isdigit():
            console.print("请输入选项序号。", markup=False)
            continue
        choice_index = int(raw_choice) - 1
        if choice_index < 0 or choice_index >= len(page.choices):
            console.print("选项序号超出范围。", markup=False)
            continue
        if not available_choices[choice_index]:
            console.print("当前条件无法选择这个选项。", markup=False)
            continue

        choice, messages, next_page = event_service.apply_choice(
            event,
            page,
            page.choices[choice_index].id,
            record.player,
            visited_pages=visited_pages,
        )
        record.transcript.append(f"Chosen option: {choice.label}.")
        record.transcript.extend(messages)
        console.print(f"已选择: {choice.label}", markup=False)
        for message in messages:
            console.print(f"- {message}", markup=False)
        if record.player.hp <= 0:
            record.victory = False
            record.transcript.append(f"Run failed in event {event.id}.")
            return False
        page = next_page

    return False


def _play_merchant_room(
    console: Console,
    run_service: "RunService",
    record: "RunRecord",
    room: "PlannedRoom",
    bundle: SnapshotBundle,
) -> bool:
    ascension_rules = run_service.ascension_service.rules_for_level(record.ascension_level)
    offer = run_service.shop_service.preview_merchant(
        record.player,
        record.character_id,
        bundle.registry,
        seed=record.seed,
        floor=room.floor,
        ascension_rules=ascension_rules,
        cards_removed=record.cards_removed,
    )
    record.transcript.append(f"Merchant visited with {record.player.gold} gold.")

    while True:
        console.print(f"当前金币: {record.player.gold}", markup=False)
        options: list[tuple[str, str]] = []

        if offer.removable_card_id is not None:
            options.append(("remove", f"移除 {offer.removable_card_id} ({offer.remove_cost} 金币)"))
        if offer.card_offer_id is not None and offer.card_price is not None:
            card_name = bundle.registry.cards[offer.card_offer_id].name or offer.card_offer_id
            options.append(("card", f"购买卡牌 {card_name} ({offer.card_price} 金币)"))
        if offer.potion_offer_id is not None and offer.potion_price is not None:
            potion_name = bundle.registry.potions[offer.potion_offer_id].name or offer.potion_offer_id
            options.append(("potion", f"购买药水 {potion_name} ({offer.potion_price} 金币)"))
        options.append(("leave", "离开商店"))

        for index, (_key, label) in enumerate(options, start=1):
            console.print(f"{index}. {label}", markup=False)

        raw_choice = _read_command(console, "商店选项")
        if raw_choice in {"quit", "q"}:
            return True
        if not raw_choice.isdigit():
            console.print("请输入选项序号。", markup=False)
            continue
        choice_index = int(raw_choice) - 1
        if choice_index < 0 or choice_index >= len(options):
            console.print("选项序号超出范围。", markup=False)
            continue

        action, _label = options[choice_index]
        if action == "leave":
            break
        if action == "remove":
            message, cards_removed = run_service.shop_service.purchase_removal(record.player, record.cards_removed)
            if message is None:
                console.print("当前无法移除卡牌。", markup=False)
                continue
            record.cards_removed = cards_removed
            offer.remove_cost = 75 + record.cards_removed * 25
            offer.removable_card_id = run_service.shop_service._preview_basic_card(record.player)
            record.transcript.append(message)
            console.print(message, markup=False)
            continue
        if action == "card":
            message = run_service.shop_service.purchase_card(record.player, offer)
            if message is None:
                console.print("当前无法购买这张卡牌。", markup=False)
                continue
            record.transcript.append(message)
            console.print(message, markup=False)
            continue
        if action == "potion":
            message = run_service.shop_service.purchase_potion(record.player, offer)
            if message is None:
                console.print("当前无法购买这瓶药水。", markup=False)
                continue
            record.transcript.append(message)
            console.print(message, markup=False)

    return False


def _play_campfire_room(
    console: Console,
    run_service: "RunService",
    record: "RunRecord",
    room: "PlannedRoom",
) -> bool:
    ascension_rules = run_service.ascension_service.rules_for_level(record.ascension_level)
    heal_amount = max(1, int(record.player.max_hp * 0.3 * ascension_rules.campfire_heal_multiplier))
    console.print(f"篝火可恢复 {heal_amount} 点生命。", markup=False)
    while True:
        choice = _read_command(console, "篝火选项(rest/leave)")
        if choice in {"quit", "q"}:
            return True
        if choice in {"leave", "l"}:
            record.transcript.append(f"Campfire left untouched on floor {room.floor}.")
            console.print("你离开了篝火。", markup=False)
            return False
        if choice in {"rest", "r", ""}:
            previous_hp = record.player.hp
            record.player.hp = min(record.player.max_hp, record.player.hp + heal_amount)
            actual_heal = record.player.hp - previous_hp
            message = f"Campfire heals {record.player.name} for {actual_heal} HP."
            record.transcript.append(message)
            console.print(message, markup=False)
            return False
        console.print("请输入 rest 或 leave。", markup=False)


def _handle_combat_command(console: Console, runtime: CombatRuntime, command: str) -> bool:
    parts = command.split()
    if not parts:
        return False

    verb = parts[0].lower()
    if verb in {"play", "p"}:
        if len(parts) < 2 or not parts[1].isdigit():
            raise ValueError("play 命令需要手牌序号。")
        card_index = int(parts[1]) - 1
        if card_index < 0 or card_index >= len(runtime.player.hand):
            raise IndexError("手牌序号超出范围。")
        target_index = None
        if len(parts) >= 3:
            if not parts[2].isdigit():
                raise ValueError("目标必须是敌人序号。")
            target_index = int(parts[2]) - 1
        elif _card_needs_target(runtime, card_index):
            if len(runtime.alive_enemies()) == 1:
                target_index = 0
            else:
                target_index = _prompt_enemy_target(console, runtime)
        runtime.play_card(card_index, target_index)
        return True

    if verb in {"use", "u"}:
        if len(parts) < 2 or not parts[1].isdigit():
            raise ValueError("use 命令需要药水序号。")
        runtime.use_potion(int(parts[1]) - 1)
        return True

    return False


def _card_needs_target(runtime: CombatRuntime, card_index: int) -> bool:
    card = runtime.player.hand[card_index]
    definition = runtime.get_card_definition(card)
    if definition.numbers.damage is None or not runtime.alive_enemies():
        return False
    target_name = (definition.target or "").lower()
    if "all" in target_name or "self" in target_name:
        return False
    description = strip_markup(resolve_execution_description(definition) or "").lower()
    return "all enemies" not in description and "所有敌人" not in description


def _prompt_enemy_target(console: Console, runtime: CombatRuntime) -> int:
    enemies = runtime.alive_enemies()
    for index, enemy in enumerate(enemies, start=1):
        console.print(
            f"{index}. {enemy.name} HP {enemy.hp}/{enemy.max_hp} Block {enemy.block} 意图 {enemy.intent or '未知'}",
            markup=False,
        )
    raw_target = _read_command(console, "目标")
    if not raw_target.isdigit():
        raise ValueError("目标必须是敌人序号。")
    target_index = int(raw_target) - 1
    if target_index < 0 or target_index >= len(enemies):
        raise IndexError("目标序号超出范围。")
    return target_index


def _print_combat_state(console: Console, runtime: CombatRuntime) -> None:
    player = runtime.player
    player_table = Table(title=f"第 {runtime.state.turn} 回合")
    player_table.add_column("项目")
    player_table.add_column("数值")
    player_table.add_row("角色", player.name)
    player_table.add_row("生命", f"{player.hp}/{player.max_hp}")
    player_table.add_row("格挡", str(player.block))
    player_table.add_row("能量", f"{player.energy}/{player.max_energy}")
    player_table.add_row("药水", ", ".join(runtime.registry.potions[potion_id].name or potion_id for potion_id in player.potion_ids) or "无")
    player_table.add_row("资源", _format_named_values(player.resources) or "无")
    player_table.add_row("法球", ", ".join(player.orbs) or "无")
    player_table.add_row(
        "牌堆",
        f"抽牌 {len(player.draw_pile)} / 弃牌 {len(player.discard_pile)} / 消耗 {len(player.exhaust_pile)}",
    )
    console.print(player_table)

    enemy_table = Table(title="敌人")
    enemy_table.add_column("序号")
    enemy_table.add_column("名称")
    enemy_table.add_column("HP")
    enemy_table.add_column("格挡")
    enemy_table.add_column("意图")
    for index, enemy in enumerate(runtime.alive_enemies(), start=1):
        enemy_table.add_row(str(index), enemy.name, f"{enemy.hp}/{enemy.max_hp}", str(enemy.block), enemy.intent or "未知")
    console.print(enemy_table)

    hand_table = Table(title="手牌")
    hand_table.add_column("序号")
    hand_table.add_column("名称")
    hand_table.add_column("费用")
    hand_table.add_column("说明")
    for index, card in enumerate(player.hand, start=1):
        definition = runtime.get_card_definition(card)
        hand_table.add_row(
            str(index),
            definition.name or card.definition_id,
            str(runtime.card_energy_cost(card, definition)),
            _truncate(strip_markup(definition.description or ""), 52),
        )
    console.print(hand_table)


def _print_route_preview(console: Console, record: "RunRecord") -> None:
    table = Table(title="路线预览")
    table.add_column("层")
    table.add_column("房间")
    table.add_column("目标")
    for room in record.rooms:
        target = room.encounter_id or room.event_id or "-"
        table.add_row(str(room.floor), _room_label(room.room_type), target)
    console.print(table)


def _flush_log(console: Console, transcript: list[str], cursor: int) -> int:
    for line in transcript[cursor:]:
        console.print(line, markup=False)
    return len(transcript)


def _read_command(console: Console, label: str) -> str:
    try:
        return console.input(f"{label}> ").strip()
    except (EOFError, KeyboardInterrupt):
        return "quit"


def _room_label(room_type: str) -> str:
    labels = {
        "monster": "普通战斗",
        "elite": "精英战斗",
        "boss": "Boss 战",
        "event": "事件",
        "merchant": "商店",
        "campfire": "篝火",
    }
    return labels.get(room_type, room_type)


def _format_named_values(values: dict[str, int]) -> str:
    if not values:
        return ""
    return ", ".join(f"{key}:{value}" for key, value in sorted(values.items()))


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
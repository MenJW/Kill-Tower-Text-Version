from kill_tower.engine.action_queue import Action, ActionQueue


def test_action_queue_push_pop_and_len() -> None:
    queue = ActionQueue()
    queue.push(Action(name="draw", source_id="system"))
    queue.push(Action(name="damage", source_id="card"))

    assert len(queue) == 2
    assert queue.pop().name == "draw"
    assert queue.pop().name == "damage"
    assert len(queue) == 0


def test_action_queue_drain_clears_queue() -> None:
    queue = ActionQueue()
    queue.extend([Action(name="a", source_id="x"), Action(name="b", source_id="y")])

    drained = queue.drain()

    assert [action.name for action in drained] == ["a", "b"]
    assert len(queue) == 0
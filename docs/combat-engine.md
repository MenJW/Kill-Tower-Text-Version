# Combat Engine

## Runtime Objects

- CombatState
- PlayerState
- MonsterState
- CardInstance
- ActionQueue
- TranscriptService

## Turn Flow

1. Start combat hooks
2. Start player turn
3. Draw cards and refresh energy
4. Resolve player actions
5. End player turn hooks
6. Resolve enemy intents
7. End round hooks

## Design Constraints

- Queue-driven resolution only
- RNG must be seedable and replayable
- Logs must be generated from state transitions
- Side effects should be attached to explicit actions or hooks

## First Vertical Slice

- Single player
- One to two enemies
- Damage, block, draw, discard, exhaust
- Transcript output for every action
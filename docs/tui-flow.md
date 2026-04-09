# TUI Flow

## Primary Screens

- Main menu
- New run configuration
- Combat screen
- Map screen
- Event screen
- Merchant screen
- Campfire screen
- Reward screen
- Save/load screen

## Input Principles

- Single-key actions for the common path
- Focus-aware navigation for panels and lists
- No hidden state changes outside the visible log

## Current Launcher

The current UI launcher exposes:

- zhs/eng language toggle
- character cycling across the 5 current single-player characters
- stable 7-floor run mode and full-act mode toggle
- live transcript tail and run summary
- path/status inspection for debugging

## Planned Combat Layout

- top row: room and enemy summary
- middle row: player state and hand
- bottom row: actions and transcript
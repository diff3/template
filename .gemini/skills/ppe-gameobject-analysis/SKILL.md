---
name: ppe-gameobject-analysis
description: Analyze the GameObject subsystem in PPE, including spawns, templates, interactions, and packet flow. Use when debugging GO behavior, adding new GO types, or verifying MoP protocol compliance.
---

# PPE GameObject Analysis

This skill provides a guided workflow for investigating and analyzing GameObjects within the PPE codebase.

## Core Files & Locations

- **Definitions**: `data/def/GAMEOBJECT_CREATE.def`, `SMSG_UPDATE_OBJECT.def`
- **Logic**: `server/modules/handlers/world/bootstrap/gameobjects.py` (Spawn), `server/modules/handlers/world/opcodes/entities.py` (Interaction)
- **DB Models**: `server/modules/database/WorldModel.py`
- **Portals**: `server/modules/handlers/world/teleport/gameobject_teleport.py`

## Workflow: Analyzing a GameObject Issue

1. **Identify the GO**:
   - Find the `entry` (template ID) and `guid` (spawn ID).
   - Query the DB: `SELECT * FROM gameobject_template WHERE entry = <ID>`.
2. **Check the Type**:
   - Identify the `type` in `gameobject_template`.
   - Map it to the logic in `entities.py` or `gameobject_teleport.py`.
3. **Verify Packet Flow**:
   - Use the `proxy` to capture the `CMSG_GAME_OBJ_USE` packet.
   - Verify the GUID is correctly decoded in `entities.py`.
4. **Trace Interaction**:
   - For Portals: Trace `resolve_gameobject_teleport_destination`.
   - For Chairs: Trace `_sit_on_chair`.
5. **Compare with MoP References**:
   - Use \`ppe-pandaria548-comparison\` as the primary reference.
   - Use \`ppe-skyfire548-comparison\` as the secondary reference.
   - Check \`/home/magnus/docker/pandaria_5.4.8_docker/src/pandaria_5.4.8/src/server/game/Entities/GameObject/\` for authoritative C++ logic.

## Key Patterns

- **Rotation**: MoP GOs use 64-bit packed quaternions. Logic is in \`_pack_gameobject_rotation\` in \`gameobjects.py\`.
- **Visibility**: Handled via \`DatabaseConnection.get_gameobjects_near\`.
- **Transports**: Special GO types (11, 15) with path progress in \`data0\` or \`transport_path_progress\`.
- **Authority**: PPE (Python) > Pandaria548 (C++) > SkyFire548 (C++).


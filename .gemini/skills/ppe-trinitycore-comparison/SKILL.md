---
name: ppe-trinitycore-comparison
description: Compare PPE logic or data structures with TrinityCore. Use when you need to verify if PPE is correctly implementing a specific WoW system by cross-referencing with the TrinityCore C++ source code.
---

# PPE vs TrinityCore Comparison (Historical Reference)

This skill guides the comparison of PPE with TrinityCore. 

## Comparison Philosophy

- **Historical Reference Only**: TrinityCore is a general-purpose core. For MoP-specific behavior (5.4.8), prioritize **Pandaria548** or **SkyFire548**.
- **Complex Logic**: Use TC to understand systems that haven't changed much since Cataclysm/MoP (e.g., pathfinding, complex combat formulas).
- **PPE is the Primary**: If PPE differs from TrinityCore, determine if it's a bug in PPE or a deliberate design choice (e.g., PPE's DSL approach vs TC's manual buffer reading).

## Workflow: Cross-Referencing

1. **Find TC Code**: Search the TrinityCore repository (or a local clone) for the opcode or system name (e.g., `SMSG_PONG`, `Unit::CalculateDamage`).
2. **Analyze TC Implementation**:
    - How does TC read the packet? (Look for `packet >> value`).
    - What is the bit-ordering?
3. **Compare with PPE DSL**:
    - Open the corresponding `.def` file in PPE.
    - Check if the field order and types match.
    - Note: TC often uses `ByteBuffer` which maps to PPE's `struct` codes.
4. **Compare Business Logic**:
    - Compare `server/modules/game/` in PPE with the corresponding `src/server/game/` in TC.
    - Look for differences in state management or data persistence.

## Common Mappings

- `WorldPacket` (TC) -> `.def` + `DSL` (PPE)
- `Opcodes.h` (TC) -> `server/modules/opcodes/` (PPE)
- `Database` (TC) -> `server/modules/database/` (PPE)
- `ScriptMgr` (TC) -> `server/modules/handlers/` or `DSL` blocks (PPE)

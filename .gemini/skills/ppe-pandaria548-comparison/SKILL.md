---
name: ppe-pandaria548-comparison
description: Compare PPE logic or data structures with Pandaria548. Use when you need to verify MoP-era (5.4.8) behavior, packet structures, or game systems against an authoritative C++ reference.
---

# PPE vs Pandaria548 Comparison

This skill guides the comparison of PPE with the Pandaria548 C++ core.

## Comparison Philosophy

- **Pandaria548 is the Primary Reference**: It is the most accurate source for MoP-era (5.4.8) behavior.
- **PPE is the Primary Codebase**: Always prioritize PPE's declarative approach. If Pandaria548 differs, determine if it's a protocol mismatch or a design choice.

## Workflow: Cross-Referencing

1. **Locate Pandaria548 Code**:
   - Reference path: `/home/magnus/docker/pandaria_5.4.8_docker/src/pandaria_5.4.8/src/server/game/`
   - Use \`find\` or \`grep\` to locate specific systems (e.g., \`Entities/GameObject/\`, \`Maps/\`).
2. **Analyze Structural Differences**:
   - Pandaria548 uses C++ classes and \`ByteBuffer\` for packets.
   - PPE uses Python dictionaries and DSL (\`.def\`) for packets.
3. **Trace Lifecycle**:
   - Compare \`Map::AddToMap\` (P548) with \`bootstrap/gameobjects.py\` (PPE).
   - Compare \`GameObject::Use\` (P548) with \`entities.py\` (PPE).
4. **Identify Gaps**: Use P548 to find missing fields (like the 32 \`data\` fields in template) or missing logic (like GO AI).

## Authority Order

1. PPE source code
2. PPE packet captures
3. Pandaria548 source code
4. SkyFire548 source code

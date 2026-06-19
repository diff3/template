---
name: ppe-skyfire548-comparison
description: Compare PPE logic or data structures with SkyFire548. Use when you need a secondary MoP-era (5.4.8) reference for complex systems like Transports, Destructible Objects, or Grid management.
---

# PPE vs SkyFire548 Comparison

This skill guides the comparison of PPE with the SkyFire548 C++ core.

## Comparison Philosophy

- **SkyFire548 is a Secondary MoP Reference**: Use it to cross-verify findings from Pandaria548 or when Pandaria548 logic is unclear.
- **Focus on Systems**: SkyFire548 is useful for understanding how MoP systems (like Transports) were integrated into the TrinityCore architecture.

## Workflow: Cross-Referencing

1. **Locate SkyFire548 Code**:
   - Reference path: `/home/magnus/docker/SkyFire_548_docker/src/skyfire_5.4.8/src/server/game/`
   - Use \`find\` or \`grep\` to locate systems (e.g., \`Entities/GameObject/\`, \`Maps/\`).
2. **Compare Implementations**:
   - Compare \`TransportMgr.cpp\` (SF548) with \`gameobjects.py\` (PPE) for transport logic.
   - Compare \`WorldSession::HandleGameObjectUseOpcode\` (SF548) with \`entities.py\` (PPE) for opcode handling.
3. **Verify Protocol**: Both use 18414 build protocol. Check for bit-packing differences if any.

## Authority Order

1. PPE source code
2. PPE packet captures
3. Pandaria548 source code
4. SkyFire548 source code

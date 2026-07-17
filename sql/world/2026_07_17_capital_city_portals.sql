-- Capital-city portal data for the 5.4.8 world database.
-- Pandaria and the temporary Vashj'ir destinations use the normal
-- GAMEOBJECT_TYPE_SPELLCASTER -> spell -> spell_target_position pipeline.

-- Remove duplicate Horde rows at identical coordinates, retaining the
-- original spawn GUID for each normal Earthshrine portal.
DELETE FROM `gameobject`
WHERE `guid` IN (73626, 73630, 73631, 73632)
  AND `id` IN (206595, 207686, 207687, 207689);

-- Restore the four Alliance Eastern Earthshrine portals that are present in
-- the canonical world data but missing from the current database.
DELETE FROM `gameobject`
WHERE `guid` IN (263875, 263876, 263877, 263878)
   OR (`map` = 0 AND `id` IN (207692, 207693, 207694, 207695));

INSERT INTO `gameobject`
    (`guid`, `id`, `map`, `spawnMask`, `phaseId`, `phaseGroup`,
     `position_x`, `position_y`, `position_z`, `orientation`,
     `rotation0`, `rotation1`, `rotation2`, `rotation3`,
     `spawntimesecs`, `animprogress`, `state`, `scale`)
VALUES
    (263875, 207692, 0, 1, 0, 0, -8212.33, 399.021, 117.273, 1.64933, 0, 0, 0.734322, 0.678802, 300, 255, 1, 1),
    (263876, 207693, 0, 1, 0, 0, -8223.32, 451.182, 117.488, 3.14159, 0, 0, -1,       0,        300, 255, 1, 1),
    (263877, 207694, 0, 1, 0, 0, -8186.15, 413.729, 116.750, 2.72271, 0, 0, 0.978148, 0.207912, 300, 255, 1, 1),
    (263878, 207695, 0, 1, 0, 0, -8233.28, 415.595, 117.448, 3.83973, -0.0200067, 0.0145435, -0.939502, 0.341650, 300, 255, 1, 1);

-- The Pandaria portal templates cast a faction-specific wrapper spell.  The
-- wrappers trigger the actual teleport spells in the 5.4.8 SpellEffect DBC:
--   Horde:   130698 -> 130696 (Honeydew Village)
--   Alliance:130703 -> 130702 (Paw'don Village)
UPDATE `gameobject_template`
SET `data0` = CASE `entry`
        WHEN 215424 THEN 130698
        WHEN 215457 THEN 130703
    END,
    -- Historical SFDB rows contain numeric values in these client-facing
    -- string columns. A numeric IconName is rendered as a black cursor tile;
    -- empty strings select the normal spellcaster cog cursor.
    `IconName` = '',
    `castBarCaption` = '',
    `unk1` = ''
WHERE `entry` IN (215424, 215457) AND `type` = 22;

-- 130696/130702 are the faction-specific Jade Forest teleport spells. Keep
-- both destinations in spell_target_position so the two capitals use the
-- same normal portal path.
DELETE FROM `spell_target_position` WHERE `id` IN (130696, 130702);
INSERT INTO `spell_target_position`
    (`id`, `effIndex`, `target_map`, `target_position_x`, `target_position_y`,
     `target_position_z`, `target_orientation`)
VALUES
    (130696, 0, 870, 3001.38, -542.47, 248.18, 5.1),
    (130702, 0, 870, -437.214, -1907.87, 53.5862, 2.89331);

-- TODO: Replace this temporary Smuggler's Scar destination with the complete
-- Cataclysm Vashj'ir introductory ship/quest sequence when it is implemented.
UPDATE `gameobject_template`
SET `data0` = CASE `entry`
    WHEN 207690 THEN 90244
    WHEN 207691 THEN 90245
END
WHERE `entry` IN (207690, 207691) AND `type` = 22;

DELETE FROM `spell_target_position` WHERE `id` IN (90244, 90245);
INSERT INTO `spell_target_position`
    (`id`, `effIndex`, `target_map`, `target_position_x`, `target_position_y`,
     `target_position_z`, `target_orientation`)
VALUES
    (90244, 0, 0, -4556.46, 3470.22, -101.461, 3.21141),
    (90245, 0, 0, -4556.46, 3470.22, -101.461, 3.21141);

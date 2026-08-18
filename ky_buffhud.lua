-- ky_buffhud.lua — Affichage horizontal des buffs + killfeed
-- Kyosh1ro HUD v2.0.0
-- Buffs affichés côte à côte sur une rangée horizontale configurable
-- Icônes compatibles VanillaHUD (skills_new, perks, hud_icons, etc.)

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD
local MY_MOD_PATH = ModPath

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "ky_buff_catalog.lua")
if not catalog_ok then
    log("[Kyosh1ro HUD] Erreur chargement catalogue buffs (HUD): " .. tostring(catalog_err))
end

-- ═══════════════════════════════════════════════════
-- Utilitaires
-- ═══════════════════════════════════════════════════
local function clamp(x, lo, hi)
    if x < lo then return lo end
    if x > hi then return hi end
    return x
end

local function now()
    return TimerManager:game():time()
end

local FALLBACK_TEXTURE = "guis/textures/pd2/hud_timer"

-- ═══════════════════════════════════════════════════
-- État interne
-- ═══════════════════════════════════════════════════
KH._panel       = nil
KH._buffs       = {}           -- { [id] = {id, icon, color, value_text?, stack_text?, start_t, duration, t_end?, is_debuff} }
KH._buff_sources = {}          -- { [buff_id] = { [source_key] = source_data } }
KH._source_targets = {}        -- { [source_key] = { buff_id, ... } }
KH._kills       = {}           -- { {name, start_t, t_end?} }
KH._kill_combo  = { count = 0, last_t = nil, updated_t = nil }
KH._update_acc  = 0

local MAX_KILLFEED_SIZE = 3
local KILL_COMBO_WINDOW = 3
local KILL_SCROLL_TIME  = 0.2
local HUD_ACCENT_COLOR  = Color(0.52, 0.88, 0.92)
local AI_BUFF_LABEL     = "[AI]"

local function killfeed_size(settings)
    local value = tonumber(settings and settings.killfeed_size) or MAX_KILLFEED_SIZE
    return math.floor(clamp(value, 1, MAX_KILLFEED_SIZE))
end
local BANNER_FRAME_STYLE = {
    inset = 2,
    glow_alpha = 0.16,
    brackets = { extension = 4 },
}

-- ═══════════════════════════════════════════════════
-- Résolution d'icônes — système VanillaHUD
-- ═══════════════════════════════════════════════════
local function has_texture(path)
    return path and DB and DB:has(Idstring("texture"), Idstring(path))
end

--- Résout une icône à partir d'une table de description (format VanillaHUD)
--- Supporte : skills_new, skills, perks, hud_tweak, hud_icons, hudtabs, hudpickups, waypoints, texture direct
local function get_icon_data(icon)
    if not icon then return FALLBACK_TEXTURE, nil end

    local texture = icon.texture
    local texture_rect = icon.texture_rect
    local skills = icon.skills
    local skills_new = icon.skills_new

    -- Les coordonnées de l'atlas ont changé au fil des mises à jour. Quand le
    -- catalogue connaît le nom interne du skill, demander sa position au jeu
    -- et conserver les coordonnées statiques uniquement comme repli.
    if icon.skill_id then
        local ok, icon_xy = pcall(function()
            local skills_tweak = tweak_data and tweak_data.skilltree and tweak_data.skilltree.skills
            local skill = skills_tweak and skills_tweak[icon.skill_id]
            return skill and skill.icon_xy
        end)
        if ok and type(icon_xy) == "table" then
            if icon.skill_atlas == "skills" then
                skills = icon_xy
            else
                skills_new = icon_xy
            end
        end
    end

    if skills then
        texture = "guis/textures/pd2/skilltree/icons_atlas"
        local x, y = unpack(skills)
        texture_rect = { x * 64, y * 64, 64, 64 }
    elseif skills_new then
        texture = "guis/textures/pd2/skilltree_2/icons_atlas_2"
        local x, y = unpack(skills_new)
        texture_rect = { x * 80, y * 80, 80, 80 }
    elseif icon.perks then
        texture = string.format("guis/%stextures/pd2/specialization/icons_atlas",
            icon.texture_bundle_folder and string.format("dlcs/%s/", tostring(icon.texture_bundle_folder)) or "")
        local x, y = unpack(icon.perks)
        texture_rect = { x * 64, y * 64, 64, 64 }
    elseif icon.hud_tweak then
        local ok, tx, rect = pcall(function()
            return tweak_data.hud_icons:get_icon_data(icon.hud_tweak, texture_rect)
        end)
        if ok and tx then
            texture = tx
            texture_rect = rect
        end
    elseif icon.hud_icons then
        texture = "guis/textures/hud_icons"
        texture_rect = icon.hud_icons
    elseif icon.hudtabs then
        texture = "guis/textures/pd2/hud_tabs"
        texture_rect = icon.hudtabs
    elseif icon.hudpickups then
        texture = "guis/textures/pd2/hud_pickups"
        texture_rect = icon.hudpickups
    elseif icon.waypoints then
        texture = "guis/textures/pd2/pd2_waypoints"
        texture_rect = icon.waypoints
    end

    if not texture or not has_texture(texture) then
        texture = FALLBACK_TEXTURE
        texture_rect = nil
    end

    return texture, texture_rect
end

-- Le catalogue partagé des buffs est chargé depuis ky_buff_catalog.lua.

-- ═══════════════════════════════════════════════════
-- Résolution d'icône pour un buff_id
-- ═══════════════════════════════════════════════════
local function icon_for_buff(buff_id)
    local vhud_map = HUDList and HUDList.BuffItemBase and HUDList.BuffItemBase.MAP
    local map_entry = (vhud_map and vhud_map[buff_id]) or KH.BUFF_MAP[buff_id]
    if map_entry then
        local tex, rect = get_icon_data(map_entry)
        return { texture = tex, rect = rect }
    end
    return { texture = FALLBACK_TEXTURE }
end

local function current_perk_deck_ids()
    local ok, specialization_id, base_specialization_id = pcall(function()
        local skilltree = managers and managers.skilltree
        local current = skilltree and skilltree:get_specialization_value("current_specialization")
        current = tonumber(current)
        if not current then return nil, nil end

        local skilltree_tweak = tweak_data and tweak_data.skilltree
        local specialization = skilltree_tweak
            and skilltree_tweak.specializations
            and skilltree_tweak.specializations[current]
        return current, tonumber(specialization and specialization.based_on) or current
    end)
    if not ok then return nil, nil end
    return specialization_id, base_specialization_id
end

local function icon_for_equipped_perk_deck()
    local specialization_id = current_perk_deck_ids()
    if not specialization_id then
        return icon_for_buff("equipped_perk_deck")
    end

    if KH._equipped_perk_deck_id == specialization_id and KH._equipped_perk_deck_icon then
        return KH._equipped_perk_deck_icon
    end

    -- Cette API du jeu résout elle-même l'atlas correct, y compris pour les
    -- decks DLC. Conserver l'icône générique du catalogue comme repli.
    local icon_ok, texture, rect = pcall(function()
        local skilltree_tweak = tweak_data and tweak_data.skilltree
        return skilltree_tweak:get_specialization_icon_data(specialization_id)
    end)
    if not (icon_ok and texture and has_texture(texture)) then
        return icon_for_buff("equipped_perk_deck")
    end

    KH._equipped_perk_deck_id = specialization_id
    KH._equipped_perk_deck_icon = { texture = texture, rect = rect }
    return KH._equipped_perk_deck_icon
end

local function color_from_catalog(value)
    if not value then return nil end
    if type(value) ~= "string" then return value end

    local definition = (KH.BUFF_COLORS and KH.BUFF_COLORS[value]) or value
    local ok, color = pcall(function()
        if type(definition) == "table" then
            return Color(unpack(definition))
        end
        return Color(definition)
    end)
    return ok and color or nil
end

local function color_for_buff(buff_id, is_debuff)
    if is_debuff then
        local vhud_options = HUDListManager and HUDListManager.ListOptions
        return (vhud_options and vhud_options.buff_icon_color_debuff_fix)
            or color_from_catalog("debuff")
            or Color.white
    end

    local vhud_map = HUDList and HUDList.BuffItemBase and HUDList.BuffItemBase.MAP
    local vhud_entry = vhud_map and vhud_map[buff_id]
    local catalog_entry = KH.BUFF_MAP and KH.BUFF_MAP[buff_id]
    return color_from_catalog(vhud_entry and vhud_entry.color)
        or color_from_catalog(catalog_entry and catalog_entry.color)
        or Color.white
end

-- ═══════════════════════════════════════════════════
-- Vérifie si un buff doit être affiché (settings)
-- ═══════════════════════════════════════════════════
function KH:is_buff_visible(buff_id)
    if not self.settings or not self.settings.enable_buffs then return false end

    local map_entry = KH.BUFF_MAP[buff_id]
    if not map_entry then return true end -- buff inconnu, on l'affiche

    -- Vérifier le toggle de catégorie
    local cat = map_entry.category
    if cat and self.settings.buff_categories then
        if self.settings.buff_categories[cat] == false then
            return false
        end
    end

    -- Vérifier le toggle individuel
    if self.settings.buff_toggles then
        if self.settings.buff_toggles[buff_id] == false then
            return false
        end
    end

    return true
end

-- Ces indicateurs actifs conservent toujours le même ordre au début de la
-- rangée. Un indicateur absent ne réserve aucun emplacement vide.
local STATIC_BUFF_SLOTS = {
    "equipped_perk_deck",
    "passive_health_regen",
    "standard_armor_regeneration",
    "armor_break_invulnerable_debuff",
    "damage_increase",
    "damage_reduction",
    "melee_damage_increase",
}

local STATIC_BUFF_SLOT_SET = {}
for _, buff_id in ipairs(STATIC_BUFF_SLOTS) do
    STATIC_BUFF_SLOT_SET[buff_id] = true
end

local function equipped_perk_deck_entry(hud)
    if not hud._equipped_perk_deck_buff then
        hud._equipped_perk_deck_buff = {
            id = "equipped_perk_deck",
            color = color_for_buff("equipped_perk_deck", false),
            persistent = true,
        }
    end
    hud._equipped_perk_deck_buff.icon = icon_for_equipped_perk_deck()
    return hud._equipped_perk_deck_buff
end

local function active_equipped_perk_buff(hud)
    local _, base_specialization_id = current_perk_deck_ids()
    local candidates = base_specialization_id
        and KH.PERK_DECK_BUFFS
        and KH.PERK_DECK_BUFFS[base_specialization_id]

    for _, buff_id in ipairs(candidates or {}) do
        local buff = hud._buffs[buff_id]
        local definition = KH.BUFF_MAP and KH.BUFF_MAP[buff_id]
        if buff and buff.icon and definition and definition.category == "perk"
                and hud:is_buff_visible(buff_id) then
            return buff, buff_id
        end
    end

    return nil, nil
end

local function localized_text(id, fallback)
    local value = fallback
    pcall(function()
        if managers.localization then
            local translated = managers.localization:text(id)
            if translated and translated ~= "" and translated:find("ERROR:", 1, true) ~= 1 then
                value = translated
            end
        end
    end)
    return value
end

local function combo_label(count)
    if count == 2 then
        return localized_text("ky_hud_double_kill", "DOUBLE KILL")
    elseif count == 3 then
        return localized_text("ky_hud_triple_kill", "TRIPLE KILL")
    elseif count == 4 then
        return localized_text("ky_hud_quad_kill", "QUAD KILL")
    end
    return localized_text("ky_hud_multi_kill", "MULTI KILL") .. " x" .. tostring(count)
end

local function combo_color(count)
    if count == 2 then return Color(1, 0.85, 0.2) end
    if count == 3 then return Color(1, 0.55, 0.1) end
    if count == 4 then return Color(1, 0.2, 0.1) end
    return Color(0.9, 0.15, 1)
end

-- Cadre tactique inspiré des notifications Battlefield : traits asymétriques,
-- quatre crochets détachés et chevrons qui convergent vers le contenu.
local function draw_corner_brackets(panel, x, y, w, h, color, alpha, layer, style)
    local extension = style and style.extension or 4
    local arm_x = style and style.arm_x or math.min(18, w * 0.08)
    local arm_y = style and style.arm_y or math.min(11, h * 0.3)
    local line_width = style and style.line_width or 1
    local left = x - extension
    local right = x + w + extension
    local top = y - extension
    local bottom = y + h + extension
    local corners = {
        {
            Vector3(left + arm_x, top, 0),
            Vector3(left, top, 0),
            Vector3(left, top + arm_y, 0),
        },
        {
            Vector3(right - arm_x, top, 0),
            Vector3(right, top, 0),
            Vector3(right, top + arm_y, 0),
        },
        {
            Vector3(left, bottom - arm_y, 0),
            Vector3(left, bottom, 0),
            Vector3(left + arm_x, bottom, 0),
        },
        {
            Vector3(right, bottom - arm_y, 0),
            Vector3(right, bottom, 0),
            Vector3(right - arm_x, bottom, 0),
        },
    }

    for _, points in ipairs(corners) do
        panel:polyline({
            points = points,
            line_width = line_width,
            color = color,
            alpha = alpha,
            layer = layer,
        })
    end
end

local function draw_chevrons(panel, x, y, direction, color, alpha, layer, style)
    local count = 3
    local arrow_w = style and style.arrow_w or 7
    local arrow_h = style and style.arrow_h or 12
    local gap = style and style.gap or 3

    for i = 0, count - 1 do
        local arrow_x = x + i * (arrow_w + gap)
        local triangles
        if direction > 0 then
            triangles = {
                Vector3(0, 0, 0),
                Vector3(0, arrow_h, 0),
                Vector3(arrow_w, arrow_h * 0.5, 0),
            }
        else
            triangles = {
                Vector3(arrow_w, 0, 0),
                Vector3(arrow_w, arrow_h, 0),
                Vector3(0, arrow_h * 0.5, 0),
            }
        end

        local prominence
        if direction > 0 then
            prominence = i / (count - 1)
        else
            prominence = (count - 1 - i) / (count - 1)
        end

        panel:polygon({
            x = arrow_x,
            y = y - arrow_h * 0.5,
            w = arrow_w,
            h = arrow_h,
            triangles = triangles,
            color = color,
            alpha = alpha * (0.55 + 0.45 * prominence),
            layer = layer,
        })
    end
end

local TACTICAL_FRAME_SEGMENTS = {
    { 0.09, 0, 0.2  },
    { 0.37, 0, 0.11 },
    { 0.6,  0, 0.27 },
    { 0.06, 1, 0.13 },
    { 0.27, 1, 0.3  },
    { 0.7,  1, 0.18 },
}

local function draw_tactical_frame(panel, x, y, w, h, color, alpha, layer, style)
    local glow_alpha = style and style.glow_alpha or 0.16
    local inset = style and style.inset or 2

    panel:gradient({
        x = x + inset,
        y = y + inset,
        w = w - inset * 2,
        h = h - inset * 2,
        orientation = "horizontal",
        gradient_points = {
            0, Color.black:with_alpha(alpha * 0.16),
            0.2, Color.black:with_alpha(alpha * 0.62),
            0.5, Color.black:with_alpha(alpha * 0.78),
            0.82, Color.black:with_alpha(alpha * 0.58),
            1, Color.black:with_alpha(alpha * 0.1),
        },
        layer = layer,
    })

    -- Trois segments sur chaque bord, volontairement décalés et inégaux.
    for _, segment in ipairs(TACTICAL_FRAME_SEGMENTS) do
        local segment_x = x + w * segment[1]
        local segment_y = y + (segment[2] == 1 and h - 1 or 0)
        local segment_w = w * segment[3]
        panel:rect({
            x = segment_x, y = segment_y - 1, w = segment_w, h = 3,
            color = color, alpha = alpha * glow_alpha, layer = layer + 1,
        })
        panel:rect({
            x = segment_x, y = segment_y, w = segment_w, h = 1,
            color = color, alpha = alpha, layer = layer + 2,
        })
    end

    draw_corner_brackets(
        panel, x, y, w, h, color, alpha, layer + 2,
        style and style.brackets
    )
end

local TEXT_GLOW_OFFSETS = {
    { -1, 0 }, { 1, 0 }, { 0, -1 }, { 0, 1 },
}

local function draw_glowing_text(panel, label, font, font_size, color, x, y, w, h, alpha, layer)
    panel:text({
        text = label,
        font = font,
        font_size = font_size,
        color = Color.black,
        align = "center",
        vertical = "center",
        x = x + 1,
        y = y + 1,
        w = w,
        h = h,
        layer = layer,
        alpha = alpha * 0.9,
    })
    for _, offset in ipairs(TEXT_GLOW_OFFSETS) do
        panel:text({
            text = label,
            font = font,
            font_size = font_size,
            color = color,
            align = "center",
            vertical = "center",
            x = x + offset[1],
            y = y + offset[2],
            w = w,
            h = h,
            layer = layer,
            alpha = alpha * 0.16,
        })
    end
    panel:text({
        text = label,
        font = font,
        font_size = font_size,
        color = color,
        align = "center",
        vertical = "center",
        x = x,
        y = y,
        w = w,
        h = h,
        layer = layer + 1,
        alpha = alpha,
    })
end

-- ═══════════════════════════════════════════════════
-- API publique : ajouter/retirer des buffs
-- ═══════════════════════════════════════════════════
function KH:add_buff(buff_id, icon_data, duration, raw_upgrade_id, persistent, is_debuff, value_text, stack_text)
    if not self.settings or not self.settings.enable_buffs then return end

    -- Résoudre le vrai buff_id depuis l'upgrade
    local resolved_id = buff_id
    if raw_upgrade_id and KH.UPGRADE_TO_BUFF[raw_upgrade_id] then
        resolved_id = KH.UPGRADE_TO_BUFF[raw_upgrade_id]
    end

    -- Vérifier si ce buff est visible dans les settings
    if not self:is_buff_visible(resolved_id) then return end

    local dur = tonumber(duration)
    if not persistent then
        dur = dur or (self.settings.buff_duration or 5)
    end
    local t = now()
    local definition = KH.BUFF_MAP and KH.BUFF_MAP[resolved_id]

    -- Un buff rafraîchi garde sa position dans la rangée (order_t d'origine),
    -- seuls son timer et son fondu (start_t) repartent de zéro
    local existing = self._buffs[resolved_id]

    self._buffs[resolved_id] = {
        id       = resolved_id,
        icon     = icon_data or icon_for_buff(resolved_id),
        color    = color_for_buff(resolved_id, is_debuff),
        category = definition and definition.category,
        value_text = value_text,
        stack_text = stack_text,
        is_debuff = is_debuff == true,
        order_t  = existing and existing.order_t or t,
        start_t  = t,
        duration = dur,
        t_end    = not persistent and dur and (t + dur) or nil,
        persistent = persistent == true,
    }
end

function KH:remove_buff(buff_id)
    -- Essayer aussi le buff résolu
    self._buffs[buff_id] = nil
    if KH.UPGRADE_TO_BUFF[buff_id] then
        self._buffs[KH.UPGRADE_TO_BUFF[buff_id]] = nil
    end
end

-- ═══════════════════════════════════════════════════
-- Sources de buffs et pont optionnel VanillaHUD+
-- ═══════════════════════════════════════════════════
local function application_time()
    local ok, t = pcall(function()
        return Application:time()
    end)
    return ok and tonumber(t) or now()
end

local function source_remaining(data)
    if type(data) ~= "table" then
        return nil, false
    end

    local app_t = application_time()
    local expire_t = tonumber(data.expire_t)
    if expire_t then
        return math.max(0, expire_t - app_t), true
    end

    local duration = tonumber(data.duration)
    if duration then
        local start_t = tonumber(data.t)
        if start_t then
            return math.max(0, start_t + duration - app_t), true
        end
        return math.max(0, duration), true
    end

    if type(data.stacks) == "table" then
        local latest_expire_t
        for _, stack in ipairs(data.stacks) do
            local stack_expire_t = type(stack) == "table" and tonumber(stack.expire_t)
            if stack_expire_t and (not latest_expire_t or stack_expire_t > latest_expire_t) then
                latest_expire_t = stack_expire_t
            end
        end
        if latest_expire_t then
            return math.max(0, latest_expire_t - app_t), true
        end
    end

    return nil, false
end

local function player_upgrade_value(category, upgrade, fallback)
    local ok, value = pcall(function()
        return managers.player and managers.player:upgrade_value(category, upgrade, fallback)
    end)
    return ok and value ~= nil and value or fallback
end

local function largest_source_value(sources)
    local result
    for _, source in pairs(sources) do
        if not source.is_calculated then
            local value = tonumber(source.value)
            if value and (not result or value > result) then
                result = value
            end
        end
    end
    return result
end

local function source_stack_count(source)
    local count = tonumber(source and source.stack_count)
    if count then return math.floor(count) end
    if source and type(source.stacks) == "table" then return #source.stacks end
    return nil
end

local function largest_stack_count(sources)
    local result
    for _, source in pairs(sources) do
        local count = source_stack_count(source)
        if count and (not result or count > result) then
            result = count
        end
    end
    return result
end

local function compact_number(value)
    local text = string.format("%.2f", value)
    text = string.gsub(text, "(%..-)0+$", "%1")
    return string.gsub(text, "%.$", "")
end

local function current_player_damage()
    local ok, player_damage = pcall(function()
        local player = managers.player and managers.player:player_unit()
        return alive(player) and player:character_damage()
    end)
    return ok and player_damage or nil
end

local function passive_health_regen_source_value(source)
    local value = source and tonumber(source.value)
    if not value then return nil end

    -- VanillaHUD+ exprime la régénération de l'équipier en points de santé
    -- internes, contrairement aux autres sources qui utilisent déjà un ratio.
    if source.source_id == "crew_health_regen" then
        local player_damage = current_player_damage()
        local ok, max_health = pcall(function()
            return player_damage and player_damage:_max_health()
        end)
        max_health = ok and tonumber(max_health) or nil
        if not max_health or max_health <= 0 then return nil end
        return value / (max_health * 10)
    end

    return value
end

local function equipped_weapon_context()
    local ok, ignore_upgrades, categories = pcall(function()
        local player = managers.player and managers.player:player_unit()
        local inventory = alive(player) and player:inventory()
        local weapon = inventory and inventory:equipped_unit()
        local base = alive(weapon) and weapon:base()
        local tweak = base and base:weapon_tweak_data()
        return tweak and tweak.ignore_damage_upgrades == true, tweak and tweak.categories
    end)
    if not ok or type(categories) ~= "table" then return nil, nil end

    local category_set = {}
    for _, category in ipairs(categories) do
        category_set[category] = true
    end
    return ignore_upgrades, category_set
end

local function source_applies_to_weapon(source_id, categories)
    if source_id == "overkill" then
        return categories.shotgun or categories.saw
    elseif source_id == "overkill_aced" then
        return not categories.shotgun and not categories.saw
    elseif source_id == "berserker" then
        return categories.saw == true
    elseif source_id == "berserker_aced" then
        return categories.saw ~= true
    end
    return true
end

local function health_ratio_damage_multiplier(source_id, value)
    if source_id == "berserker" then
        return 1 + value * (tonumber(player_upgrade_value(
            "player", "melee_damage_health_ratio_multiplier", 0
        )) or 0)
    elseif source_id == "berserker_aced" then
        return 1 + value * (tonumber(player_upgrade_value(
            "player", "damage_health_ratio_multiplier", 0
        )) or 0)
    end
    return value
end

local function damage_increase_text(sources)
    local ignore_upgrades, categories = equipped_weapon_context()
    if not categories then return nil end
    if ignore_upgrades then return "(0%)" end

    local multiplier = 1
    local has_value = false
    for _, source in pairs(sources) do
        local value = tonumber(source.value)
        if value and source_applies_to_weapon(source.source_id, categories) then
            multiplier = multiplier * health_ratio_damage_multiplier(source.source_id, value)
            has_value = true
        end
    end
    return has_value and string.format("%+.0f%%", (multiplier - 1) * 100) or nil
end

local function melee_damage_increase_text(sources)
    local multiplier = 1
    local has_value = false
    for _, source in pairs(sources) do
        local value = tonumber(source.value)
        if value then
            multiplier = multiplier * health_ratio_damage_multiplier(source.source_id, value)
            has_value = true
        end
    end
    return has_value and ("x" .. compact_number(multiplier)) or nil
end

local function maniac_damage_multiplier(value)
    local player_damage = current_player_damage()
    if not player_damage then return nil end

    local ok, current_armor, max_armor, max_health = pcall(function()
        return player_damage:get_real_armor(), player_damage:_max_armor(), player_damage:_max_health()
    end)
    if not ok then return nil end
    current_armor = tonumber(current_armor)
    if not current_armor then return nil end
    local maximum = current_armor > 0 and tonumber(max_armor) or tonumber(max_health)
    if not maximum or maximum <= 0 then return nil end
    return 1 - value / (maximum * 10)
end

local function damage_reduction_source_multiplier(source)
    local value = tonumber(source.value)
    if not value then return nil end

    if source.source_id == "chico_injector" then
        local player_damage = current_player_damage()
        local ok, health_ratio = pcall(function()
            return player_damage and player_damage:health_ratio()
        end)
        local low_health = player_upgrade_value("player", "chico_injector_low_health_multiplier", nil)
        local threshold = type(low_health) == "table" and tonumber(low_health[1])
        local bonus = type(low_health) == "table" and tonumber(low_health[2])
        if ok and tonumber(health_ratio) and threshold and bonus and health_ratio < threshold then
            value = value + bonus
        end
        return 1 - value
    elseif source.source_id == "frenzy" then
        return 1 - value
    elseif source.source_id == "maniac" then
        return maniac_damage_multiplier(value)
    end

    return value
end

local function damage_reduction_text(sources)
    local multiplier = 1
    local has_value = false
    for _, source in pairs(sources) do
        local value = damage_reduction_source_multiplier(source)
        if value then
            multiplier = multiplier * value
            has_value = true
        end
    end
    local reduction = clamp(1 - multiplier, 0, 1)
    return has_value and string.format("-%.0f%%", reduction * 100) or nil
end

local function calculated_base_dodge(include_sicario)
    local value = tonumber(tweak_data and tweak_data.player
        and tweak_data.player.damage and tweak_data.player.damage.DODGE_INIT) or 0

    local ok, calculated = pcall(function()
        local pm = managers.player
        local armor_id = managers.blackmarket and managers.blackmarket:equipped_armor(true, true)
        local armor_upgrade = armor_id and tostring(armor_id) .. "_dodge_addend"
        local risk_upgrade = pm:upgrade_value("player", "detection_risk_add_dodge_chance", 0)
        return (pm:body_armor_value("dodge") or 0)
            + (pm:upgrade_value("player", "passive_dodge_chance", 0) or 0)
            + (armor_upgrade and pm:upgrade_value("player", armor_upgrade, 0) or 0)
            + (pm:upgrade_value("player", "tier_dodge_chance", 0) or 0)
            + (pm:get_value_from_risk_upgrade(risk_upgrade) or 0)
            + (pm:upgrade_value("team", "crew_add_dodge", 0) or 0)
            + (include_sicario and pm:upgrade_value("player", "sicario_multiplier", 0) or 0)
    end)
    return math.max(0, value + (ok and tonumber(calculated) or 0))
end

local function total_dodge_chance_text(sources)
    local has_sicario_source = false
    local has_smoke_source = false
    for _, source in pairs(sources) do
        has_sicario_source = has_sicario_source or source.source_id == "sicario_dodge"
        has_smoke_source = has_smoke_source or source.source_id == "smoke_screen_grenade"
    end

    local value = calculated_base_dodge(not has_sicario_source)
    for _, source in pairs(sources) do
        if not source.is_calculated then
            value = value + (tonumber(source.value) or 0)
        end
    end

    if has_smoke_source then
        local smoke_dodge = tonumber(tweak_data and tweak_data.projectiles
            and tweak_data.projectiles.smoke_screen_grenade
            and tweak_data.projectiles.smoke_screen_grenade.dodge_chance) or 0
        value = 1 - (1 - value) * (1 - smoke_dodge)
    end

    return string.format("%.0f%%", math.max(value * 100, 0))
end

local BUFF_VALUE_FORMATTERS = {
    percent = function(sources)
        local value = largest_source_value(sources)
        return value and string.format("%.0f%%", value * 100) or nil
    end,
    multiplier_percent = function(sources)
        local value = largest_source_value(sources)
        return value and string.format("%+.0f%%", (value - 1) * 100) or nil
    end,
    multiplier = function(sources)
        local value = largest_source_value(sources)
        return value and ("x" .. compact_number(value)) or nil
    end,
    negative_number = function(sources)
        local value = largest_source_value(sources)
        return value and string.format("-%.0f", math.abs(value)) or nil
    end,
    negative_number_1 = function(sources)
        local value = largest_source_value(sources)
        return value and string.format("-%.1f", math.abs(value)) or nil
    end,
    damage_increase = damage_increase_text,
    damage_reduction = damage_reduction_text,
    melee_damage_increase = melee_damage_increase_text,
    passive_health_regen = function(sources)
        local total = 0
        local has_value = false

        for _, source in pairs(sources) do
            local value = passive_health_regen_source_value(source)
            if value then
                total = total + value
                has_value = true
            end
        end

        return has_value and string.format("%.1f%%", total * 100) or nil
    end,
    total_dodge_chance = total_dodge_chance_text,
}

local function format_buff_value(buff_id, sources)
    local definition = KH.BUFF_MAP and KH.BUFF_MAP[buff_id]
    local formatter = definition and BUFF_VALUE_FORMATTERS[definition.value_format]
    local value_text = formatter and formatter(sources) or nil
    local stack_count = largest_stack_count(sources)
    local stack_text
    if definition and definition.stack_format == "biker_charges" and stack_count then
        local maximum = tonumber(tweak_data and tweak_data.upgrades
            and tweak_data.upgrades.wild_max_triggers_per_time) or 0
        stack_text = "x" .. tostring(math.max(0, maximum - stack_count))
    elseif definition and definition.show_stack_count and stack_count and stack_count > 0 then
        stack_text = "x" .. tostring(stack_count)
    end
    return value_text, stack_text
end

function KH:_refresh_source_target(buff_id)
    local sources = self._buff_sources and self._buff_sources[buff_id]
    if not sources or not next(sources) then
        self:remove_buff(buff_id)
        return
    end

    local has_persistent_source = false
    local persistent_sources_are_debuffs = true
    local max_remaining
    local max_remaining_is_debuff = false
    local value_text, stack_text = format_buff_value(buff_id, sources)
    for _, source in pairs(sources) do
        local remaining, timed = source_remaining(source)
        if timed then
            local source_is_debuff = source.is_debuff == true
            if remaining > 0 and (not max_remaining
                or remaining > max_remaining
                or (remaining == max_remaining and max_remaining_is_debuff and not source_is_debuff)) then
                max_remaining = remaining
                max_remaining_is_debuff = source_is_debuff
            end
        else
            has_persistent_source = true
            if not source.is_debuff then
                persistent_sources_are_debuffs = false
            end
        end
    end

    if has_persistent_source then
        self:add_buff(buff_id, nil, nil, nil, true, persistent_sources_are_debuffs, value_text, stack_text)
    elseif max_remaining and max_remaining > 0 then
        self:add_buff(buff_id, nil, max_remaining, nil, false, max_remaining_is_debuff, value_text, stack_text)
    else
        self:remove_buff(buff_id)
    end
end

local DYNAMIC_VALUE_BUFFS = {
    "damage_increase",
    "damage_reduction",
    "melee_damage_increase",
    "passive_health_regen",
    "total_dodge_chance",
}

function KH:RefreshCalculatedBuffValues()
    if self._debug_preview_active then return end

    local buff_id = "total_dodge_chance"
    local source_key = "calculated:base_dodge"
    local sources = self._buff_sources[buff_id]
    local base_dodge = calculated_base_dodge(true)
    local has_calculated_source = sources and sources[source_key] ~= nil
    local source_changed = false

    if base_dodge > 0 and not has_calculated_source then
        self._buff_sources[buff_id] = sources or {}
        self._buff_sources[buff_id][source_key] = {
            source_id = "base_dodge",
            is_calculated = true,
            is_debuff = false,
        }
        source_changed = true
    elseif base_dodge <= 0 and has_calculated_source then
        sources[source_key] = nil
        if not next(sources) then self._buff_sources[buff_id] = nil end
        source_changed = true
    end

    if source_changed then
        self:_refresh_source_target(buff_id)
    end

    -- Ces valeurs dépendent aussi de l'arme équipée, de la santé ou de
    -- l'armure. Les recalculer à faible fréquence sans recréer les entrées
    -- conserve leur ordre et leur timer.
    for _, dynamic_buff_id in ipairs(DYNAMIC_VALUE_BUFFS) do
        local dynamic_sources = self._buff_sources[dynamic_buff_id]
        local buff = self._buffs[dynamic_buff_id]
        if dynamic_sources and buff then
            buff.value_text, buff.stack_text = format_buff_value(dynamic_buff_id, dynamic_sources)
        end
    end
end

function KH:handle_buff_event(event, source_id, data, source_type)
    if not source_id or not KH.GetBuffTargets then return end

    local targets = KH.GetBuffTargets(source_id)
    if #targets == 0 then return end

    source_type = source_type or "buff"
    local source_key = tostring(source_type) .. ":" .. tostring(source_id)

    if event == "deactivate" then
        local old_targets = self._source_targets[source_key] or targets
        for _, buff_id in ipairs(old_targets) do
            local sources = self._buff_sources[buff_id]
            if sources then
                sources[source_key] = nil
                if not next(sources) then
                    self._buff_sources[buff_id] = nil
                end
            end
            self:_refresh_source_target(buff_id)
        end
        self._source_targets[source_key] = nil
        return
    end

    local activates = event == "activate"
        or event == "set_duration"
        or event == "add_timed_stack"
        or event == "set_data"

    if not activates and not self._source_targets[source_key] then
        return
    end

    self._source_targets[source_key] = targets
    for _, buff_id in ipairs(targets) do
        self._buff_sources[buff_id] = self._buff_sources[buff_id] or {}
        local source = self._buff_sources[buff_id][source_key] or {}
        if type(data) == "table" then
            for key, value in pairs(data) do
                source[key] = value
            end
            if data.duration and not data.t
                and (event == "activate" or event == "set_duration") then
                source.t = application_time()
            end
        end
        if event == "set_value" and (not data or data.value == nil) then
            source.value = nil
        elseif event == "set_stack_count" and (not data or data.stack_count == nil) then
            source.stack_count = nil
        end
        source.updated_t = application_time()
        source.source_id = source_id
        source.is_debuff = string.match(tostring(source_id), "_debuff$") ~= nil
        self._buff_sources[buff_id][source_key] = source
        self:_refresh_source_target(buff_id)
    end
end

function KH:SyncGameInfoBuffs()
    if not (managers and managers.gameinfo) then return end

    local ok_buffs, buffs = pcall(function()
        return managers.gameinfo:get_buffs()
    end)
    if ok_buffs and type(buffs) == "table" then
        for id, data in pairs(buffs) do
            self:handle_buff_event("activate", id, data, "gameinfo_buff")
        end
    end

    local ok_actions, actions = pcall(function()
        return managers.gameinfo:get_player_actions()
    end)
    if ok_actions and type(actions) == "table" then
        for id, data in pairs(actions) do
            self:handle_buff_event("activate", id, data, "gameinfo_action")
        end
    end
    self:RefreshCalculatedBuffValues()
end

function KH:TryRegisterGameInfoBridge()
    if self._gameinfo_bridge_active then return true end
    if not (managers and managers.gameinfo
        and managers.gameinfo.register_listener
        and managers.gameinfo.get_buffs
        and managers.gameinfo.get_player_actions) then
        return false
    end

    local buff_events = {
        "activate", "deactivate", "set_duration", "set_progress",
        "set_stack_count", "add_timed_stack", "remove_timed_stack", "set_value",
    }
    local action_events = { "activate", "deactivate", "set_duration", "set_value", "set_data" }
    local buff_callback = function(event, id, data)
        KH:handle_buff_event(event, id, data, "gameinfo_buff")
    end
    local action_callback = function(event, id, data)
        KH:handle_buff_event(event, id, data, "gameinfo_action")
    end

    local ok, err = pcall(function()
        for _, event in ipairs(buff_events) do
            managers.gameinfo:register_listener("Kyosh1roHUD_buff_bridge", "buff", event, buff_callback)
        end
        for _, event in ipairs(action_events) do
            managers.gameinfo:register_listener("Kyosh1roHUD_action_bridge", "player_action", event, action_callback)
        end
    end)
    if not ok then
        if not self._gameinfo_bridge_error_logged then
            self._gameinfo_bridge_error_logged = true
            log("[Kyosh1ro HUD] Pont VanillaHUD+ indisponible: " .. tostring(err))
        end
        return false
    end

    -- Remplacer les sources locales déjà observées par l'état de référence du
    -- gestionnaire afin qu'une désactivation future ne laisse rien bloqué.
    self._buff_sources = {}
    self._source_targets = {}
    self._buffs = {}
    self._gameinfo_bridge_active = true
    self._gameinfo_bridge_callbacks = { buff_callback, action_callback }
    self:SyncGameInfoBuffs()
    log("[Kyosh1ro HUD] Détection complète reliée au gestionnaire de buffs VanillaHUD+.")
    return true
end

function KH:RefreshDetectedBuffs()
    if self._gameinfo_bridge_active then
        self:SyncGameInfoBuffs()
    end
    for buff_id, _ in pairs(self._buff_sources or {}) do
        self:_refresh_source_target(buff_id)
    end
    self:RefreshCalculatedBuffValues()
end

-- ═══════════════════════════════════════════════════
-- API publique : ajouter un kill au killfeed
-- ═══════════════════════════════════════════════════
function KH:add_kill(enemy_name)
    if not self.settings or not self.settings.enable_killfeed then return end

    local dur = self.settings.buff_duration or 5
    local t = now()
    local combo = self._kill_combo or { count = 0 }
    if combo.preview then
        combo = { count = 0 }
    end
    if combo.last_t and (t - combo.last_t) <= KILL_COMBO_WINDOW then
        combo.count = (combo.count or 0) + 1
    else
        combo.count = 1
    end
    combo.last_t = t
    combo.updated_t = t
    self._kill_combo = combo

    local entry = {
        name   = enemy_name or "Enemy",
        start_t = t,
        t_end  = t + dur,
    }
    table.insert(self._kills, entry)

    while #self._kills > killfeed_size(self.settings) do
        table.remove(self._kills, 1)
    end
end

-- ═══════════════════════════════════════════════════
-- Panneau HUD
-- ═══════════════════════════════════════════════════
local function get_hud_panel()
    if not managers.hud then return nil end

    local ok, script = pcall(function()
        return managers.hud:script(PlayerBase.PLAYER_INFO_HUD_PD2)
    end)
    if ok and script and script.panel then
        return script.panel
    end

    local ok2, script2 = pcall(function()
        return managers.hud:script(PlayerBase.PLAYER_INFO_HUD_FULLSCREEN_PD2)
    end)
    if ok2 and script2 and script2.panel then
        return script2.panel
    end

    return nil
end

function KH:ensure_panel(force)
    local parent = get_hud_panel()
    if not parent then return false end

    if force or not (self._panel and alive(self._panel)) then
        local old = parent:child("kyosh1ro_buff_panel")
        if old then
            parent:remove(old)
        end

        self._panel = parent:panel({
            name  = "kyosh1ro_buff_panel",
            layer = 100,
        })
    end
    return true
end

-- ═══════════════════════════════════════════════════
-- Layout : rangée horizontale centrée sur une position en pourcentage d'écran
-- L'espacement se resserre si nécessaire pour ne masquer aucun buff.
-- ═══════════════════════════════════════════════════
local function compute_horizontal_positions(
        count, x_percent, y_percent, panel_w, panel_h, icon_size, frame_pad_x, frame_pad_y,
        top_label_height)
    local positions = {}
    if count == 0 then return positions end

    local edge_margin = 4
    local frame_w = icon_size + frame_pad_x * 2
    local desired_pitch = frame_w + clamp(icon_size * 0.25, 4, 12)
    local available_w = math.max(frame_w, panel_w - edge_margin * 2)
    local pitch = desired_pitch

    if count > 1 and frame_w + pitch * (count - 1) > available_w then
        pitch = math.max(0, (available_w - frame_w) / (count - 1))
    end

    local row_w = frame_w + pitch * (count - 1)
    local anchor_x = panel_w * clamp(x_percent, 0, 100) / 100
    local row_left = clamp(
        anchor_x - row_w * 0.5,
        edge_margin,
        math.max(edge_margin, panel_w - edge_margin - row_w)
    )

    -- Garder la valeur au-dessus, le cadre et le timer sous l'icône dans le panneau.
    local min_y = icon_size * 0.5 + frame_pad_y + (top_label_height or 18) + edge_margin
    local max_y = panel_h - icon_size * 0.5 - 22
    local y = clamp(panel_h * clamp(y_percent, 0, 100) / 100, min_y, max_y)
    local first_x = row_left + frame_w * 0.5

    for i = 0, count - 1 do
        positions[#positions + 1] = { x = first_x + pitch * i, y = y }
    end

    return positions
end

-- ═══════════════════════════════════════════════════
-- Dessin du HUD
-- ═══════════════════════════════════════════════════
function KH:draw()
    if not (self._panel and alive(self._panel)) then return end

    local s = self.settings
    if not s then return end

    local t = now()

    -- Purger les buffs expirés
    for id, b in pairs(self._buffs) do
        if b.t_end and b.t_end <= t then
            self._buffs[id] = nil
        end
    end

    -- Purger les kills expirés
    local i = 1
    while i <= #self._kills do
        if self._kills[i].t_end and self._kills[i].t_end <= t then
            table.remove(self._kills, i)
        else
            i = i + 1
        end
    end

    -- Une série se termine après quelques secondes sans nouveau kill.
    local combo = self._kill_combo
    if combo and not combo.preview and combo.last_t
            and (t - combo.last_t) > KILL_COMBO_WINDOW then
        combo.count = 0
        combo.last_t = nil
        combo.updated_t = nil
    end

    -- Nettoyer le panneau pour redessiner
    self._panel:clear()

    local w = self._panel:w()
    local h = self._panel:h()
    local cx = w * 0.5
    local cy = h * 0.5
    local radius    = clamp(s.circle_radius or 250, 100, 500)
    local size      = clamp(s.icon_size or 32, 16, 64)
    local alpha     = clamp(s.opacity or 0.9, 0.1, 1.0)

    -- ── Dessiner les buffs ──
    if s.enable_buffs then
        local buff_list = {}
        local promoted_perk_buff_id

        -- Les indicateurs prioritaires ouvrent la rangée dans l'ordre choisi,
        -- mais seuls le deck équipé et les buffs réellement actifs apparaissent.
        -- Un buff actif associé au deck remplace son placeholder en position 1.
        for _, buff_id in ipairs(STATIC_BUFF_SLOTS) do
            if self:is_buff_visible(buff_id) then
                local buff
                if buff_id == "equipped_perk_deck" then
                    buff, promoted_perk_buff_id = active_equipped_perk_buff(self)
                    buff = buff or equipped_perk_deck_entry(self)
                else
                    buff = self._buffs[buff_id]
                end
                if buff and buff.icon then
                    table.insert(buff_list, buff)
                end
            end
        end

        local extra_buffs = {}
        for _, b in pairs(self._buffs) do
            if b.icon and b.id ~= promoted_perk_buff_id
                    and not STATIC_BUFF_SLOT_SET[b.id] and self:is_buff_visible(b.id) then
                table.insert(extra_buffs, b)
            end
        end
        -- Tri par ordre d'arrivée : les nouveaux buffs s'ajoutent à la suite
        -- des emplacements fixes, sans réordonner les icônes existantes.
        table.sort(extra_buffs, function(a, b)
            local oa = a.order_t or a.start_t or 0
            local ob = b.order_t or b.start_t or 0
            if oa ~= ob then return oa < ob end
            return a.id < b.id
        end)
        for _, buff in ipairs(extra_buffs) do
            table.insert(buff_list, buff)
        end

        local frame_pad_x = clamp(size * 0.26, 6, 14)
        local frame_pad_y = clamp(size * 0.1, 2, 5)
        local top_label_height = 18
        for _, buff in ipairs(buff_list) do
            if buff.category == "ai" and buff.value_text then
                top_label_height = 35
                break
            end
        end
        local positions = compute_horizontal_positions(
            #buff_list,
            tonumber(s.buff_position_x) or 50,
            tonumber(s.buff_position_y) or 85,
            w,
            h,
            size,
            frame_pad_x,
            frame_pad_y,
            top_label_height
        )
        local arrow_w = clamp(size * 0.07, 1.5, 4)
        local arrow_h = clamp(size * 0.16, 4, 9)
        local arrow_gap = clamp(size * 0.035, 0.75, 2)
        local arrow_group_w = arrow_w * 3 + arrow_gap * 2
        local compact_chevrons = {
            arrow_w = arrow_w,
            arrow_h = arrow_h,
            gap = arrow_gap,
        }
        local compact_frame = {
            inset = 2,
            glow_alpha = 0.12,
            brackets = {
                extension = clamp(size * 0.055, 1, 3),
                arm_x = clamp(size * 0.16, 3, 9),
                arm_y = clamp(size * 0.12, 3, 7),
            },
        }

        for idx, buff in ipairs(buff_list) do
            local pos = positions[idx]
            if pos then
                -- Alpha dynamique : diminue quand le buff expire.
                local life = 1
                if buff.duration and buff.duration > 0 and buff.start_t then
                    life = clamp(1 - ((t - buff.start_t) / buff.duration), 0, 1)
                end
                local buff_alpha = alpha * (0.4 + 0.6 * life)

                -- Version compacte du cadre tactique : les chevrons restent dans
                -- les marges et convergent vers l'icône sans la recouvrir.
                local frame_x = pos.x - size * 0.5 - frame_pad_x
                local frame_y = pos.y - size * 0.5 - frame_pad_y
                local frame_w = size + frame_pad_x * 2
                local frame_h = size + frame_pad_y * 2

                draw_tactical_frame(
                    self._panel,
                    frame_x,
                    frame_y,
                    frame_w,
                    frame_h,
                    HUD_ACCENT_COLOR,
                    buff_alpha * 0.72,
                    98,
                    compact_frame
                )
                draw_chevrons(
                    self._panel,
                    frame_x + 1,
                    pos.y,
                    1,
                    HUD_ACCENT_COLOR,
                    buff_alpha * 0.72,
                    100,
                    compact_chevrons
                )
                draw_chevrons(
                    self._panel,
                    frame_x + frame_w - arrow_group_w - 1,
                    pos.y,
                    -1,
                    HUD_ACCENT_COLOR,
                    buff_alpha * 0.72,
                    100,
                    compact_chevrons
                )

                local params = {
                    layer = 101,
                    w     = size,
                    h     = size,
                    x     = pos.x - size / 2,
                    y     = pos.y - size / 2,
                }

                if buff.icon.rect then
                    params.texture      = buff.icon.texture
                    params.texture_rect = buff.icon.rect
                else
                    params.texture = buff.icon.texture
                end

                local bmp = self._panel:bitmap(params)
                bmp:set_color(buff.color or Color.white)
                bmp:set_alpha(buff_alpha)

                local is_ai_buff = buff.category == "ai"
                if buff.value_text then
                    self._panel:text({
                        text      = buff.value_text,
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = clamp(size * 0.38, 11, 15),
                        color     = buff.color or Color.white,
                        align     = "center",
                        vertical  = "center",
                        x         = frame_x,
                        y         = frame_y - (is_ai_buff and 34 or 17),
                        w         = frame_w,
                        h         = 16,
                        layer     = 102,
                        alpha     = buff_alpha,
                    })
                end

                if is_ai_buff then
                    self._panel:text({
                        text      = AI_BUFF_LABEL,
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = clamp(size * 0.3, 9, 12),
                        color     = HUD_ACCENT_COLOR,
                        align     = "center",
                        vertical  = "center",
                        x         = frame_x,
                        y         = frame_y - 17,
                        w         = frame_w,
                        h         = 16,
                        layer     = 102,
                        alpha     = buff_alpha,
                    })
                end

                if buff.stack_text then
                    local badge_w = clamp(size * 0.55, 15, 26)
                    local badge_h = clamp(size * 0.36, 10, 16)
                    local badge_x = pos.x + size * 0.5 - badge_w
                    local badge_y = pos.y + size * 0.5 - badge_h
                    self._panel:rect({
                        x = badge_x,
                        y = badge_y,
                        w = badge_w,
                        h = badge_h,
                        color = Color.black,
                        alpha = buff_alpha * 0.78,
                        layer = 102,
                    })
                    self._panel:text({
                        text = buff.stack_text,
                        font = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = clamp(size * 0.3, 9, 12),
                        color = Color.white,
                        align = "center",
                        vertical = "center",
                        x = badge_x,
                        y = badge_y,
                        w = badge_w,
                        h = badge_h,
                        layer = 103,
                        alpha = buff_alpha,
                    })
                end

                -- Timer texte sous l'icône
                local remaining = buff.t_end and math.max(0, buff.t_end - t)
                if remaining and remaining > 0 then
                    self._panel:text({
                        text      = string.format("%.1f", remaining),
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = 14,
                        color     = Color.white,
                        align     = "center",
                        x         = pos.x - size / 2,
                        y         = pos.y + size / 2 + 2,
                        w         = size,
                        h         = 16,
                        layer     = 102,
                        alpha     = alpha * 0.8,
                    })
                end
            end
        end
    end

    -- ── Dessiner le bandeau de série et le killfeed horizontal ──
    local combo_active = combo and combo.count and combo.count >= 2 and combo.last_t
    if s.enable_killfeed and (#self._kills > 0 or combo_active) then
        local killfeed_limit = killfeed_size(s)
        local visible_count = math.min(#self._kills, killfeed_limit)
        local item_h = clamp(size * 0.72 + 6, 28, 42)
        local item_gap = clamp(size * 0.3, 8, 14)
        local desired_item_w = clamp(size * 5.2, 150, 220)
        local available_w = math.max(1, w - 16)

        if visible_count > 1 then
            item_gap = math.min(
                item_gap,
                math.max(0, (available_w - visible_count) / (visible_count - 1))
            )
        end

        local item_w = desired_item_w
        if visible_count > 0 then
            item_w = math.min(
                desired_item_w,
                math.max(1, (available_w - item_gap * (visible_count - 1)) / visible_count)
            )
        end

        local feed_row_w = visible_count > 0
            and item_w * visible_count + item_gap * (visible_count - 1)
            or 0
        local banner_w = clamp(size * 7.5, 220, 320)
        local banner_h = math.max(38, size + 8)
        local block_h = banner_h + 8 + (visible_count > 0 and item_h or 0)
        local preferred_top = cy + clamp(radius * 0.55, 70, 160)
        local block_top = math.max(8, math.min(preferred_top, h - block_h - 16))
        local feed_y = block_top + banner_h + 8
        local feed_color = HUD_ACCENT_COLOR

        if combo_active then
            local remaining = combo.preview
                and KILL_COMBO_WINDOW
                or combo.last_t + KILL_COMBO_WINDOW - t
            if remaining > 0 then
                local intro = clamp((t - (combo.updated_t or t)) / 0.15, 0, 1)
                local fade_out = clamp(remaining / 0.35, 0, 1)
                local banner_alpha = alpha * fade_out
                local scale = 1 + (1 - intro) * 0.06
                local bw = banner_w * scale
                local bh = banner_h * scale
                local bx = cx - bw * 0.5
                local by = block_top - (bh - banner_h) * 0.5
                local color = combo_color(combo.count)

                draw_tactical_frame(
                    self._panel,
                    bx,
                    by,
                    bw,
                    bh,
                    color,
                    banner_alpha,
                    103,
                    BANNER_FRAME_STYLE
                )

                local arrow_group_w = 27
                local arrow_margin = 16
                draw_chevrons(
                    self._panel,
                    bx + arrow_margin,
                    by + bh * 0.5,
                    1,
                    color,
                    banner_alpha,
                    106
                )
                draw_chevrons(
                    self._panel,
                    bx + bw - arrow_margin - arrow_group_w,
                    by + bh * 0.5,
                    -1,
                    color,
                    banner_alpha,
                    106
                )

                local text_x = bx + 48
                local text_w = bw - 96
                local font_size = clamp(size * 0.65, 17, 27)
                local label = combo_label(combo.count)
                draw_glowing_text(
                    self._panel,
                    label,
                    tweak_data.menu.pd2_large_font or "fonts/font_large_mf",
                    font_size,
                    color,
                    text_x,
                    by,
                    text_w,
                    bh,
                    banner_alpha,
                    106
                )
            end
        end

        local newest = self._kills[#self._kills]
        local scroll = 1
        if newest and newest.start_t then
            scroll = clamp((t - newest.start_t) / KILL_SCROLL_TIME, 0, 1)
        end

        local feed_x = clamp(cx - feed_row_w * 0.5, 8, math.max(8, w - 8 - feed_row_w))
        local first_kill = #self._kills - visible_count + 1
        for slot = 1, visible_count do
            -- Ordre chronologique : le kill le plus ancien est à gauche,
            -- le plus récent s'ajoute à droite.
            local kill = self._kills[first_kill + slot - 1]
            local item_x = feed_x + (slot - 1) * (item_w + item_gap)

            local life = 1
            if kill.start_t and kill.t_end then
                local dur = kill.t_end - kill.start_t
                if dur > 0 then
                    life = clamp(1 - ((t - kill.start_t) / dur), 0, 1)
                end
            end

            local item_alpha = alpha * (0.25 + 0.75 * life)
            if slot == visible_count then
                item_alpha = item_alpha * scroll
                item_x = item_x + 18 * (1 - scroll)
            end

            self._panel:gradient({
                x = item_x,
                y = feed_y + 1,
                w = item_w,
                h = item_h - 2,
                orientation = "horizontal",
                gradient_points = {
                    0, Color.black:with_alpha(item_alpha * 0.68),
                    0.72, Color.black:with_alpha(item_alpha * 0.42),
                    1, Color.black:with_alpha(item_alpha * 0.05),
                },
                layer = 101,
            })
            self._panel:rect({
                x = item_x, y = feed_y + 2, w = 2, h = item_h - 4,
                color = feed_color, alpha = item_alpha * 0.9, layer = 102,
            })
            self._panel:rect({
                x = item_x + 2, y = feed_y + 1, w = item_w - 4, h = 1,
                color = feed_color, alpha = item_alpha * 0.5, layer = 102,
            })
            self._panel:rect({
                x = item_x + 2, y = feed_y + item_h - 2, w = item_w - 4, h = 1,
                color = feed_color, alpha = item_alpha * 0.5, layer = 102,
            })
            self._panel:rect({
                x = item_x + item_w - 2, y = feed_y + 2, w = 2, h = item_h - 4,
                color = feed_color, alpha = item_alpha * 0.9, layer = 102,
            })

            self._panel:text({
                text = kill.name,
                font = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                font_size = clamp(size * 0.42, 13, 18),
                color = Color(0.86, 0.96, 1),
                align = "center",
                vertical = "center",
                x = item_x + 9,
                y = feed_y,
                w = item_w - 18,
                h = item_h,
                layer = 102,
                alpha = item_alpha,
            })
        end
    end
end

-- ═══════════════════════════════════════════════════
-- Rafraîchissement
-- ═══════════════════════════════════════════════════
function KH:RefreshHUD()
    self:RefreshDetectedBuffs()
    if self:ensure_panel(false) then
        self:draw()
    end
end

-- ═══════════════════════════════════════════════════
-- Debug : simulation
-- ═══════════════════════════════════════════════════
function KH:DebugSimulate(n)
    self:DebugClear()
    self._debug_preview_active = true
    n = n or 8

    local demo_static_buffs = {
        { id = "passive_health_regen", value_text = "4.5%" },
        { id = "standard_armor_regeneration" },
        { id = "armor_break_invulnerable_debuff", is_debuff = true },
        { id = "damage_increase", value_text = "+35%" },
        { id = "damage_reduction", value_text = "-20%" },
        { id = "melee_damage_increase", value_text = "x1.75" },
    }
    local t_now = now()
    for i, demo in ipairs(demo_static_buffs) do
        self._buffs[demo.id] = {
            id = demo.id,
            icon = icon_for_buff(demo.id),
            color = color_for_buff(demo.id, demo.is_debuff),
            value_text = demo.value_text,
            is_debuff = demo.is_debuff == true,
            order_t = t_now + i * 0.001,
            start_t = t_now,
            persistent = true,
        }
    end

    -- Si le deck équipé possède un buff de deck activé dans les options, la
    -- simulation l'active afin de vérifier le remplacement de la position 1.
    local _, base_specialization_id = current_perk_deck_ids()
    local perk_candidates = base_specialization_id
        and KH.PERK_DECK_BUFFS
        and KH.PERK_DECK_BUFFS[base_specialization_id]
    for _, buff_id in ipairs(perk_candidates or {}) do
        if self:is_buff_visible(buff_id) then
            self._buffs[buff_id] = {
                id = buff_id,
                icon = icon_for_buff(buff_id),
                color = color_for_buff(buff_id, false),
                order_t = t_now + 0.0005,
                start_t = t_now,
                persistent = true,
            }
            break
        end
    end

    local demo_buffs = {
        { id = "crew_throwable_regen", stack_text = "x2" },
        { id = "total_dodge_chance", value_text = "45%" },
        { id = "lock_n_load", value_text = "+35%" },
        { id = "delayed_damage", value_text = "-125" },
        { id = "grinder", stack_text = "x3" },
        { id = "overkill" },
        { id = "unseen_strike" },
        { id = "bullet_storm" },
        { id = "second_wind", value_text = "+30%" },
    }

    for i = 1, n do
        local demo = demo_buffs[((i - 1) % #demo_buffs) + 1]
        local base = demo.id
        local icon = icon_for_buff(base)
        self._buffs["demo_" .. base .. "_" .. tostring(i)] = {
            id       = "demo_" .. base .. "_" .. tostring(i),
            icon     = icon,
            color    = color_for_buff(base, demo.is_debuff),
            category = KH.BUFF_MAP[base] and KH.BUFF_MAP[base].category,
            value_text = demo.value_text,
            stack_text = demo.stack_text,
            is_debuff = demo.is_debuff == true,
            order_t  = t_now + i * 0.001, -- ordre d'affichage 1..n dans la rangée
            start_t  = t_now,
            -- Pas de t_end : les buffs de debug restent visibles jusqu'à DebugClear.
        }
    end

    -- Simuler quelques kills
    local demo_names = { "SWAT", "Shield", "Bulldozer" }
    local t_now = now()
    for i = 1, killfeed_size(self.settings) do
        table.insert(self._kills, {
            name    = demo_names[i],
            start_t = t_now,
            -- Pas de t_end : les kills de debug restent visibles jusqu'à DebugClear.
        })
    end
    self._kill_combo = {
        count = 2,
        last_t = t_now,
        updated_t = t_now,
        preview = true,
    }
end

function KH:DebugClear()
    self._debug_preview_active = false
    self._buffs = {}
    self._kills = {}
    self._kill_combo = { count = 0, last_t = nil, updated_t = nil }
    if self._panel and alive(self._panel) then
        self._panel:clear()
    end
end

-- ═══════════════════════════════════════════════════
-- Hooks HUD : initialisation et mise à jour
-- ═══════════════════════════════════════════════════
Hooks:PostHook(HUDManager, "init_finalize", "KH_InitHUD", function()
    KH:ensure_panel(true)
    KH:TryRegisterGameInfoBridge()
    log("[Kyosh1ro HUD] Panneau HUD initialisé.")
end)

Hooks:PostHook(HUDManager, "update", "KH_UpdateHUD", function(self, t, dt)
    if not KH._gameinfo_bridge_active then
        KH._bridge_retry_acc = (KH._bridge_retry_acc or 0) + dt
        if KH._bridge_retry_acc >= 1 then
            KH._bridge_retry_acc = 0
            KH:TryRegisterGameInfoBridge()
        end
    elseif not KH._bridge_delayed_sync_done then
        KH._bridge_delayed_sync_acc = (KH._bridge_delayed_sync_acc or 0) + dt
        if KH._bridge_delayed_sync_acc >= 2 then
            KH._bridge_delayed_sync_done = true
            KH:SyncGameInfoBuffs()
        end
    end

    KH._value_refresh_acc = (KH._value_refresh_acc or 0) + dt
    if KH._value_refresh_acc >= 0.5 then
        KH._value_refresh_acc = 0
        KH:RefreshCalculatedBuffValues()
    end

    KH._update_acc = (KH._update_acc or 0) + dt
    if KH._update_acc < 0.05 then return end
    KH._update_acc = 0

    if KH:ensure_panel(false) then
        KH:draw()
    end
end)

log("[Kyosh1ro HUD] ky_buffhud.lua v2.0 chargé.")

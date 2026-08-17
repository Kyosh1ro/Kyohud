-- ky_buffhud.lua — Affichage des buffs en arc + killfeed
-- Kyosh1ro HUD v2.0.0
-- Buffs affichés côte à côte le long d'un arc de cercle
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
KH._buffs       = {}           -- { [id] = {id, icon, start_t, duration, t_end?, category} }
KH._kills       = {}           -- { {name, icon, start_t, t_end?} }
KH._kill_combo  = { count = 0, last_t = nil, updated_t = nil }
KH._update_acc  = 0

local MAX_KILL_HISTORY = 20
local MAX_VISIBLE_KILLS = 5
local KILL_COMBO_WINDOW = 3
local KILL_SCROLL_TIME  = 0.2

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

    if icon.skills then
        texture = "guis/textures/pd2/skilltree/icons_atlas"
        local x, y = unpack(icon.skills)
        texture_rect = { x * 64, y * 64, 64, 64 }
    elseif icon.skills_new then
        texture = "guis/textures/pd2/skilltree_2/icons_atlas_2"
        local x, y = unpack(icon.skills_new)
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
    local map_entry = KH.BUFF_MAP[buff_id]
    if map_entry then
        local tex, rect = get_icon_data(map_entry)
        return { texture = tex, rect = rect }
    end
    return { texture = FALLBACK_TEXTURE }
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

-- ═══════════════════════════════════════════════════
-- Icônes pour le killfeed
-- ═══════════════════════════════════════════════════
local ENEMY_ICON_MAP = {
    swat         = "hud_icons:mugshot_normal",
    heavy_swat   = "hud_icons:mugshot_normal",
    shield       = "hud_icons:mugshot_normal",
    sniper       = "hud_icons:mugshot_normal",
    taser        = "hud_icons:mugshot_normal",
    cloaker      = "hud_icons:mugshot_normal",
    medic        = "hud_icons:mugshot_normal",
    bulldozer    = "hud_icons:mugshot_normal",
    gangster     = "hud_icons:mugshot_normal",
    cop          = "hud_icons:mugshot_normal",
    default      = "hud_icons:mugshot_normal",
}

local function resolve_simple_icon(icon_ref)
    if not icon_ref or icon_ref == "" then
        return { texture = FALLBACK_TEXTURE }
    end
    local atlas, name = tostring(icon_ref):match("^([^:]+):(.+)$")
    if atlas == "hud_icons" and name then
        local ok, tx, rect = pcall(function()
            return tweak_data.hud_icons:get_icon_data(name)
        end)
        if ok and tx and has_texture(tx) and rect then
            return { texture = tx, rect = rect }
        end
    end
    if has_texture(tostring(icon_ref)) then
        return { texture = tostring(icon_ref) }
    end
    return { texture = FALLBACK_TEXTURE }
end

local function icon_for_enemy(enemy_type)
    local ref = ENEMY_ICON_MAP[enemy_type] or ENEMY_ICON_MAP.default
    return resolve_simple_icon(ref)
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

-- Cadre tactique inspiré des notifications Battlefield : quatre crochets
-- interrompus et des chevrons qui convergent vers le libellé central.
local function draw_corner_brackets(panel, x, y, w, h, color, alpha, layer)
    local extension = 4
    local arm_x = math.min(18, w * 0.08)
    local arm_y = math.min(11, h * 0.3)
    local left = x - extension
    local right = x + w + extension
    local top = y
    local bottom = y + h
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
            line_width = 1,
            color = color,
            alpha = alpha,
            layer = layer,
        })
    end
end

local function draw_chevrons(panel, x, y, direction, color, alpha, layer)
    local count = 3
    local arrow_w = 7
    local arrow_h = 12
    local gap = 3

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

-- ═══════════════════════════════════════════════════
-- API publique : ajouter/retirer des buffs
-- ═══════════════════════════════════════════════════
function KH:add_buff(buff_id, icon_data, duration, raw_upgrade_id)
    if not self.settings or not self.settings.enable_buffs then return end

    -- Résoudre le vrai buff_id depuis l'upgrade
    local resolved_id = buff_id
    if raw_upgrade_id and KH.UPGRADE_TO_BUFF[raw_upgrade_id] then
        resolved_id = KH.UPGRADE_TO_BUFF[raw_upgrade_id]
    end

    -- Vérifier si ce buff est visible dans les settings
    if not self:is_buff_visible(resolved_id) then return end

    local dur = tonumber(duration) or (self.settings.buff_duration or 5)
    local t = now()

    -- Un buff rafraîchi garde sa position dans l'arc (order_t d'origine),
    -- seuls son timer et son fondu (start_t) repartent de zéro
    local existing = self._buffs[resolved_id]

    self._buffs[resolved_id] = {
        id       = resolved_id,
        icon     = icon_data or icon_for_buff(resolved_id),
        order_t  = existing and existing.order_t or t,
        start_t  = t,
        duration = dur,
        t_end    = t + dur,
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
-- API publique : ajouter un kill au killfeed
-- ═══════════════════════════════════════════════════
function KH:add_kill(enemy_name, enemy_type)
    if not self.settings or not self.settings.enable_killfeed then return end

    local dur = self.settings.buff_duration or 5
    local t = now()
    local combo = self._kill_combo or { count = 0 }
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
        icon   = icon_for_enemy(enemy_type or "default"),
        start_t = t,
        t_end  = t + dur,
    }
    table.insert(self._kills, entry)

    while #self._kills > MAX_KILL_HISTORY do
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
-- Layout : positions séquentielles le long d'un arc
-- Les buffs se placent côte à côte depuis la position de départ
-- Arc de [1,1] (315°) vers [0,-1] (90°) = sens anti-horaire
-- ═══════════════════════════════════════════════════
local function compute_sequential_arc_positions(count, start_deg, end_deg, radius, cx, cy, icon_size)
    local positions = {}
    if count == 0 then return positions end

    -- Espacement le long de l'arc : icône + marge proportionnelle, pour que
    -- les icônes ET leur timer (16px sous l'icône) ne se chevauchent pas
    -- sur les portions diagonales de l'arc
    local margin = math.max(12, icon_size * 0.6)
    local spacing_px = icon_size + margin
    -- angle_step en degrés = (spacing_px / circumference) * 360
    local angle_step = (spacing_px / (2 * math.pi * radius)) * 360

    -- Direction : de start_deg vers end_deg (sens anti-horaire = angles croissants)
    -- start_deg = 315° (bas-droite), end_deg = 90° (haut)
    -- En traversant 0°/360°, le chemin est 315 → 360 → 0 → 90 = 135° de span
    local span = end_deg - start_deg
    if span < 0 then span = span + 360 end

    -- Trop d'icônes pour l'arc : compresser l'espacement plutôt que de
    -- masquer silencieusement le surplus
    if count > 1 and angle_step * (count - 1) > span then
        angle_step = span / (count - 1)
    end

    for i = 0, count - 1 do
        local angle_deg = start_deg + angle_step * i
        -- Normaliser à [0, 360)
        if angle_deg >= 360 then angle_deg = angle_deg - 360 end

        -- Diesel expose les fonctions trigonométriques en degrés.
        local x = cx + math.cos(angle_deg) * radius
        local y = cy - math.sin(angle_deg) * radius
        positions[#positions + 1] = { x = x, y = y }
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
    if combo and combo.last_t and (t - combo.last_t) > KILL_COMBO_WINDOW then
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
    local start_deg = s.angle_start or 315  -- [1,1] = bas-droite = 315°
    local end_deg   = s.angle_end or 90     -- [0,-1] = haut = 90°
    local size      = clamp(s.icon_size or 32, 16, 64)
    local alpha     = clamp(s.opacity or 0.9, 0.1, 1.0)

    -- ── Dessiner les buffs ──
    if s.enable_buffs then
        local buff_list = {}
        for _, b in pairs(self._buffs) do
            if b.icon then
                table.insert(buff_list, b)
            end
        end
        -- Tri par ordre d'arrivée : les nouveaux buffs s'ajoutent à la suite
        -- en bout d'arc au lieu de réordonner les icônes existantes
        table.sort(buff_list, function(a, b)
            local oa = a.order_t or a.start_t or 0
            local ob = b.order_t or b.start_t or 0
            if oa ~= ob then return oa < ob end
            return a.id < b.id
        end)

        -- Positions séquentielles le long de l'arc
        local positions = compute_sequential_arc_positions(
            #buff_list, start_deg, end_deg, radius, cx, cy, size
        )

        -- DEBUG TEMPORAIRE : trace les positions quand le nombre de buffs change
        local dbg = (#buff_list ~= KH._dbg_last_count)
        if dbg then
            KH._dbg_last_count = #buff_list
            log(string.format(
                "[Kyosh1ro HUD][DBG] panel=%.0fx%.0f centre=(%.0f;%.0f) rayon=%.0f taille=%.0f angles=%d->%d buffs=%d",
                w, h, cx, cy, radius, size, start_deg, end_deg, #buff_list))
        end

        for idx, buff in ipairs(buff_list) do
            local pos = positions[idx]
            if pos then
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

                -- DEBUG TEMPORAIRE : position calculée vs position réelle du bitmap
                if dbg then
                    log(string.format(
                        "[Kyosh1ro HUD][DBG]  #%d %s calc=(%.0f;%.0f) reel=(%.0f;%.0f)",
                        idx, tostring(buff.id), pos.x, pos.y, bmp:x(), bmp:y()))
                end

                -- Alpha dynamique : diminue quand le buff expire
                local life = 1
                if buff.duration and buff.duration > 0 and buff.start_t then
                    life = clamp(1 - ((t - buff.start_t) / buff.duration), 0, 1)
                end
                bmp:set_alpha(alpha * (0.4 + 0.6 * life))

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

    -- ── Dessiner le bandeau de série et le killfeed vertical ──
    local combo_active = combo and combo.count and combo.count >= 2 and combo.last_t
    if s.enable_killfeed and (#self._kills > 0 or combo_active) then
        local kill_icon_size = clamp(size * 0.72, 18, 36)
        local row_h = math.max(28, kill_icon_size + 6)
        local feed_w = clamp(size * 7.5, 220, 320)
        local banner_h = math.max(38, size + 8)
        local block_h = banner_h + 8 + MAX_VISIBLE_KILLS * row_h
        local preferred_top = cy + clamp(radius * 0.55, 70, 160)
        local block_top = math.max(8, math.min(preferred_top, h - block_h - 16))
        local rows_top = block_top + banner_h + 8
        local feed_color = Color(0.52, 0.88, 0.92)

        if combo_active then
            local remaining = combo.last_t + KILL_COMBO_WINDOW - t
            if remaining > 0 then
                local intro = clamp((t - (combo.updated_t or t)) / 0.15, 0, 1)
                local fade_out = clamp(remaining / 0.35, 0, 1)
                local banner_alpha = alpha * fade_out
                local scale = 1 + (1 - intro) * 0.06
                local bw = feed_w * scale
                local bh = banner_h * scale
                local bx = cx - bw * 0.5
                local by = block_top - (bh - banner_h) * 0.5
                local color = combo_color(combo.count)

                -- Fond sombre avec un centre plus dense pour préserver la lisibilité.
                self._panel:gradient({
                    x = bx + 2,
                    y = by + 2,
                    w = bw - 4,
                    h = bh - 4,
                    orientation = "horizontal",
                    gradient_points = {
                        0, Color.black:with_alpha(banner_alpha * 0.18),
                        0.18, Color.black:with_alpha(banner_alpha * 0.68),
                        0.5, Color.black:with_alpha(banner_alpha * 0.82),
                        0.82, Color.black:with_alpha(banner_alpha * 0.68),
                        1, Color.black:with_alpha(banner_alpha * 0.18),
                    },
                    layer = 103,
                })

                -- Halo puis traits fins, interrompus par les crochets extérieurs.
                self._panel:rect({
                    x = bx + 14, y = by - 1, w = bw - 28, h = 3,
                    color = color, alpha = banner_alpha * 0.18, layer = 104,
                })
                self._panel:rect({
                    x = bx + 14, y = by, w = bw - 28, h = 1,
                    color = color, alpha = banner_alpha, layer = 105,
                })
                self._panel:rect({
                    x = bx + 14, y = by + bh - 2, w = bw - 28, h = 3,
                    color = color, alpha = banner_alpha * 0.18, layer = 104,
                })
                self._panel:rect({
                    x = bx + 14, y = by + bh - 1, w = bw - 28, h = 1,
                    color = color, alpha = banner_alpha, layer = 105,
                })

                draw_corner_brackets(
                    self._panel, bx, by, bw, bh, color, banner_alpha, 105
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
                self._panel:text({
                    text = label,
                    font = tweak_data.menu.pd2_large_font or "fonts/font_large_mf",
                    font_size = font_size,
                    color = Color.black,
                    align = "center",
                    vertical = "center",
                    x = text_x + 1,
                    y = by + 1,
                    w = text_w,
                    h = bh,
                    layer = 106,
                    alpha = banner_alpha * 0.9,
                })
                self._panel:text({
                    text = label,
                    font = tweak_data.menu.pd2_large_font or "fonts/font_large_mf",
                    font_size = font_size,
                    color = color,
                    align = "center",
                    vertical = "center",
                    x = text_x,
                    y = by,
                    w = text_w,
                    h = bh,
                    layer = 107,
                    alpha = banner_alpha,
                })
            end
        end

        local newest = self._kills[#self._kills]
        local scroll = 1
        if newest and newest.start_t then
            scroll = clamp((t - newest.start_t) / KILL_SCROLL_TIME, 0, 1)
        end

        local visible_count = math.min(#self._kills, MAX_VISIBLE_KILLS)
        local feed_x = cx - feed_w / 2
        for row = 1, visible_count do
            -- Le kill le plus récent reste en haut ; les précédents descendent.
            local kill = self._kills[#self._kills - row + 1]
            local row_y = rows_top + (row - 1) * row_h
            if row > 1 then
                row_y = row_y - row_h * (1 - scroll)
            end

            local life = 1
            if kill.start_t and kill.t_end then
                local dur = kill.t_end - kill.start_t
                if dur > 0 then
                    life = clamp(1 - ((t - kill.start_t) / dur), 0, 1)
                end
            end

            local row_alpha = alpha * (0.25 + 0.75 * life)
            local row_x = feed_x
            if row == 1 then
                row_alpha = row_alpha * scroll
                row_x = row_x + 18 * (1 - scroll)
            end

            self._panel:gradient({
                x = row_x,
                y = row_y + 1,
                w = feed_w,
                h = row_h - 2,
                orientation = "horizontal",
                gradient_points = {
                    0, Color.black:with_alpha(row_alpha * 0.68),
                    0.72, Color.black:with_alpha(row_alpha * 0.42),
                    1, Color.black:with_alpha(row_alpha * 0.05),
                },
                layer = 101,
            })
            self._panel:rect({
                x = row_x, y = row_y + 2, w = 2, h = row_h - 4,
                color = feed_color, alpha = row_alpha * 0.9, layer = 102,
            })
            self._panel:rect({
                x = row_x + 2, y = row_y + 1, w = feed_w * 0.72, h = 1,
                color = feed_color, alpha = row_alpha * 0.5, layer = 102,
            })
            self._panel:rect({
                x = row_x + 2, y = row_y + row_h - 2, w = feed_w * 0.48, h = 1,
                color = feed_color, alpha = row_alpha * 0.3, layer = 102,
            })

            local icon_y = row_y + (row_h - kill_icon_size) / 2
            local icon_params = {
                layer = 102,
                w = kill_icon_size,
                h = kill_icon_size,
                x = row_x + 5,
                y = icon_y,
            }
            if kill.icon.rect then
                icon_params.texture = kill.icon.texture
                icon_params.texture_rect = kill.icon.rect
            else
                icon_params.texture = kill.icon.texture
            end

            local kill_bmp = self._panel:bitmap(icon_params)
            kill_bmp:set_color(Color(0.88, 0.96, 1))
            kill_bmp:set_alpha(row_alpha)

            self._panel:text({
                text = kill.name,
                font = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                font_size = clamp(size * 0.42, 13, 18),
                color = Color(0.86, 0.96, 1),
                align = "left",
                vertical = "center",
                x = row_x + kill_icon_size + 12,
                y = row_y,
                w = feed_w - kill_icon_size - 18,
                h = row_h,
                layer = 102,
                alpha = row_alpha,
            })
        end
    end
end

-- ═══════════════════════════════════════════════════
-- Rafraîchissement
-- ═══════════════════════════════════════════════════
function KH:RefreshHUD()
    if self:ensure_panel(false) then
        self:draw()
    end
end

-- ═══════════════════════════════════════════════════
-- Debug : simulation
-- ═══════════════════════════════════════════════════
function KH:DebugSimulate(n)
    self:DebugClear()
    n = n or 8

    local demo_buffs = {
        "unseen_strike", "overkill", "berserker", "swan_song",
        "inspire", "hostage_taker", "bullet_storm", "iron_man",
        "armor_break_invulnerable", "grinder", "sicario_dodge", "second_wind",
    }

    for i = 1, n do
        local base = demo_buffs[((i - 1) % #demo_buffs) + 1]
        local icon = icon_for_buff(base)
        local t_now = now()
        self._buffs["demo_" .. base .. "_" .. tostring(i)] = {
            id       = "demo_" .. base .. "_" .. tostring(i),
            icon     = icon,
            order_t  = t_now + i * 0.001, -- ordre d'affichage 1..n le long de l'arc
            start_t  = t_now,
            -- Pas de t_end : les buffs de debug restent visibles jusqu'à DebugClear.
        }
    end

    -- Simuler quelques kills
    local demo_names = { "SWAT", "Shield", "Bulldozer", "Cloaker", "Sniper" }
    local t_now = now()
    for i = 1, 5 do
        table.insert(self._kills, {
            name    = demo_names[i],
            icon    = icon_for_enemy("default"),
            start_t = t_now,
            -- Pas de t_end : les kills de debug restent visibles jusqu'à DebugClear.
        })
    end
    self._kill_combo = {
        count = #demo_names,
        last_t = t_now,
        updated_t = t_now,
    }
end

function KH:DebugClear()
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
    log("[Kyosh1ro HUD] Panneau HUD initialisé.")
end)

Hooks:PostHook(HUDManager, "update", "KH_UpdateHUD", function(self, t, dt)
    KH._update_acc = (KH._update_acc or 0) + dt
    if KH._update_acc < 0.05 then return end
    KH._update_acc = 0

    if KH:ensure_panel(false) then
        KH:draw()
    end
end)

log("[Kyosh1ro HUD] ky_buffhud.lua v2.0 chargé.")

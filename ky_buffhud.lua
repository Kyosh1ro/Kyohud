-- ky_buffhud.lua — Affichage circulaire des buffs + killfeed autour du viseur
-- Kyosh1ro HUD v1.0.0

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD

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
KH._panel       = nil          -- panneau HUD principal
KH._buffs       = {}           -- { [id] = {id, icon, start_t, duration, t_end} }
KH._kills       = {}           -- { {name, icon, t_end} }  (liste ordonnée)
KH._update_acc  = 0            -- throttle pour limiter les redraws

-- ═══════════════════════════════════════════════════
-- Résolution d'icônes (atlas PD2 / hud_icons / fallback)
-- ═══════════════════════════════════════════════════
local function has_texture(path)
    return path and DB and DB:has(Idstring("texture"), Idstring(path))
end

local function resolve_icon(icon_ref)
    if not icon_ref or icon_ref == "" then
        return { texture = FALLBACK_TEXTURE }
    end

    -- Format "atlas:name" (ex: "hud_icons:skill_overkill")
    local atlas, name = tostring(icon_ref):match("^([^:]+):(.+)$")
    if atlas == "hud_icons" and name then
        local ok, tx, rect = pcall(function()
            return tweak_data.hud_icons:get_icon_data(name)
        end)
        if ok and tx and has_texture(tx) and rect then
            return { texture = tx, rect = rect }
        end
    end

    -- Chemin texture direct
    if has_texture(tostring(icon_ref)) then
        return { texture = tostring(icon_ref) }
    end

    return { texture = FALLBACK_TEXTURE }
end

-- ═══════════════════════════════════════════════════
-- Catalogue des buffs connus → icônes du skilltree
-- ═══════════════════════════════════════════════════
local BUFF_ICON_MAP = {
    -- Ghost
    unseen_strike               = "hud_icons:skill_unseen_strike",
    second_wind                 = "hud_icons:skill_second_wind",
    damage_speed_multiplier     = "hud_icons:skill_speed",
    movement_speed_multiplier   = "hud_icons:skill_speed",
    dodge_chance                = "hud_icons:skill_dodge",
    -- Enforcer
    overkill_damage_multiplier  = "hud_icons:skill_overkill",
    dmg_multiplier_outnumbered  = "hud_icons:skill_underdog",
    bullet_storm                = "hud_icons:skill_bullet_storm",
    iron_man                    = "hud_icons:skill_iron_man",
    -- Mastermind
    inspire                     = "hud_icons:skill_inspire",
    inspire_cooldown            = "hud_icons:skill_inspire",
    ammo_efficiency             = "hud_icons:skill_ammo_efficiency",
    hostage_taker               = "hud_icons:skill_hostage_taker",
    -- Fugitive
    berserker_damage_multiplier = "hud_icons:skill_berserker",
    swan_song                   = "hud_icons:skill_swan_song",
    bloodthirst                 = "hud_icons:skill_bloodthirst",
    -- Perk Decks
    armor_break_invulnerable    = "hud_icons:perk_armorer",
    sicario_dodge               = "hud_icons:perk_sicario",
    stoic_damage_reduction      = "hud_icons:perk_stoic",
    rogue_dodge                 = "hud_icons:perk_rogue",
    hacker_pocket_ecm           = "hud_icons:perk_hacker",
    -- Divers
    mrwi_health_invulnerable    = "hud_icons:perk_armorer",
    crew_inspire_debuff         = "hud_icons:skill_inspire",
    invulnerable_buff           = "hud_icons:perk_armorer",
}

local function icon_for_buff(buff_id)
    local ref = BUFF_ICON_MAP[buff_id]
    if ref then return resolve_icon(ref) end
    return resolve_icon(nil)
end

-- ═══════════════════════════════════════════════════
-- Icônes pour le killfeed (types d'ennemis)
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

local function icon_for_enemy(enemy_type)
    local ref = ENEMY_ICON_MAP[enemy_type] or ENEMY_ICON_MAP.default
    return resolve_icon(ref)
end

-- ═══════════════════════════════════════════════════
-- API publique : ajouter/retirer des buffs
-- ═══════════════════════════════════════════════════
function KH:add_buff(buff_id, icon_data, duration, raw_upgrade_id)
    if not self.settings or not self.settings.enable_buffs then return end

    local dur = tonumber(duration) or (self.settings.buff_duration or 5)
    local t = now()

    self._buffs[buff_id] = {
        id       = buff_id,
        icon     = icon_data or icon_for_buff(raw_upgrade_id or buff_id),
        start_t  = t,
        duration = dur,
        t_end    = t + dur,
    }
end

function KH:remove_buff(buff_id)
    self._buffs[buff_id] = nil
end

-- ═══════════════════════════════════════════════════
-- API publique : ajouter un kill au killfeed
-- ═══════════════════════════════════════════════════
function KH:add_kill(enemy_name, enemy_type)
    if not self.settings or not self.settings.enable_killfeed then return end

    local dur = self.settings.buff_duration or 5
    local t = now()
    local entry = {
        name   = enemy_name or "Enemy",
        icon   = icon_for_enemy(enemy_type or "default"),
        start_t = t,
        t_end  = t + dur,
    }
    table.insert(self._kills, entry)

    -- Limiter à 20 kills affichés max
    while #self._kills > 20 do
        table.remove(self._kills, 1)
    end
end

-- ═══════════════════════════════════════════════════
-- Panneau HUD
-- ═══════════════════════════════════════════════════
local function get_hud_panel()
    if not managers.hud then return nil end

    -- Essayer le HUD PD2 standard
    local ok, script = pcall(function()
        return managers.hud:script(PlayerBase.PLAYER_INFO_HUD_PD2)
    end)
    if ok and script and script.panel then
        return script.panel
    end

    -- Fallback fullscreen
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
        -- Supprimer l'ancien panneau s'il existe
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
-- Layout : calcul des positions en arc de cercle
-- ═══════════════════════════════════════════════════
local function compute_arc_positions(count, start_deg, end_deg, radius, cx, cy)
    local positions = {}
    if count == 0 then return positions end

    -- Normaliser l'arc (on va de start vers end dans le sens horaire)
    local span = start_deg - end_deg
    if span <= 0 then span = span + 360 end

    for i = 0, count - 1 do
        local angle_deg
        if count == 1 then
            angle_deg = start_deg
        else
            angle_deg = start_deg - (span * i / (count - 1))
        end

        local rad = math.rad(angle_deg)
        local x = cx + math.cos(rad) * radius
        local y = cy - math.sin(rad) * radius
        positions[i + 1] = { x = x, y = y }
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
        if self._kills[i].t_end <= t then
            table.remove(self._kills, i)
        else
            i = i + 1
        end
    end

    -- Nettoyer le panneau pour redessiner
    self._panel:clear()

    local w = self._panel:w()
    local h = self._panel:h()
    local cx = w * 0.5
    local cy = h * 0.5
    local radius    = clamp(s.circle_radius or 250, 100, 500)
    local start_deg = s.angle_start or 360
    local end_deg   = s.angle_end or 270
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
        -- Tri stable par ID
        table.sort(buff_list, function(a, b) return a.id < b.id end)

        local positions = compute_arc_positions(
            #buff_list, start_deg, end_deg, radius, cx, cy
        )

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

                -- Alpha dynamique : diminue quand le buff expire
                local life = 1
                if buff.duration and buff.duration > 0 and buff.start_t then
                    life = clamp(1 - ((t - buff.start_t) / buff.duration), 0, 1)
                end
                bmp:set_alpha(alpha * (0.4 + 0.6 * life))

                -- Timer texte sous l'icône
                local remaining = math.max(0, buff.t_end - t)
                if remaining > 0 then
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

    -- ── Dessiner le killfeed (arc en dessous du crosshair) ──
    if s.enable_killfeed and #self._kills > 0 then
        -- Le killfeed utilise un arc en dessous (180° à 0°, sous le viseur)
        local kill_radius = radius + size + 20
        local kill_positions = compute_arc_positions(
            #self._kills, 250, 290, kill_radius, cx, cy
        )

        for idx, kill in ipairs(self._kills) do
            local pos = kill_positions[idx]
            if pos then
                -- Icône du kill
                local life = 1
                if kill.start_t and kill.t_end then
                    local dur = kill.t_end - kill.start_t
                    if dur > 0 then
                        life = clamp(1 - ((t - kill.start_t) / dur), 0, 1)
                    end
                end

                local icon_params = {
                    layer = 101,
                    w     = size * 0.8,
                    h     = size * 0.8,
                    x     = pos.x - (size * 0.8) / 2,
                    y     = pos.y - (size * 0.8) / 2,
                }
                if kill.icon.rect then
                    icon_params.texture      = kill.icon.texture
                    icon_params.texture_rect = kill.icon.rect
                else
                    icon_params.texture = kill.icon.texture
                end

                local kill_bmp = self._panel:bitmap(icon_params)
                kill_bmp:set_alpha(alpha * (0.3 + 0.7 * life))

                -- Nom de l'ennemi à côté
                self._panel:text({
                    text      = kill.name,
                    font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                    font_size = 12,
                    color     = Color(1, 0.9, 0.3),
                    align     = "center",
                    x         = pos.x - 50,
                    y         = pos.y + (size * 0.8) / 2 + 1,
                    w         = 100,
                    h         = 14,
                    layer     = 102,
                    alpha     = alpha * (0.3 + 0.7 * life),
                })
            end
        end
    end
end

-- ═══════════════════════════════════════════════════
-- Rafraîchissement (appelé par ky_options.lua)
-- ═══════════════════════════════════════════════════
function KH:RefreshHUD()
    if self:ensure_panel(false) then
        self:draw()
    end
end

-- ═══════════════════════════════════════════════════
-- Debug : simulation
-- ═══════════════════════════════════════════════════
function KH:DebugSimulate(n, dur)
    self:DebugClear()
    n = n or 8
    dur = dur or 8
    local demo_buffs = {
        "unseen_strike", "overkill_damage_multiplier",
        "berserker_damage_multiplier", "swan_song",
        "inspire", "hostage_taker", "bullet_storm", "iron_man",
    }

    for i = 1, n do
        local base = demo_buffs[((i - 1) % #demo_buffs) + 1]
        local id = "demo_" .. tostring(i)
        local icon = icon_for_buff(base)
        local t = now()
        self._buffs[id] = {
            id       = id,
            icon     = icon,
            start_t  = t,
            duration = dur,
            t_end    = t + dur,
        }
    end

    -- Simuler quelques kills aussi
    local demo_names = { "SWAT", "Shield", "Bulldozer", "Cloaker", "Sniper" }
    for i = 1, 5 do
        self:add_kill(demo_names[i], "default")
    end
end

function KH:DebugClear()
    self._buffs = {}
    self._kills = {}
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
    -- Throttle à ~20 FPS pour ne pas impacter les performances
    if KH._update_acc < 0.05 then return end
    KH._update_acc = 0

    if KH:ensure_panel(false) then
        KH:draw()
    end
end)

log("[Kyosh1ro HUD] ky_buffhud.lua chargé.")

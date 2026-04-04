-- ky_buffhud.lua — Affichage des buffs en arc + killfeed
-- Kyosh1ro HUD v2.0.0
-- Buffs affichés côte à côte le long d'un arc de cercle
-- Icônes compatibles VanillaHUD (skills_new, perks, hud_icons, etc.)

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
KH._panel       = nil
KH._buffs       = {}           -- { [id] = {id, icon, start_t, duration, t_end, category} }
KH._kills       = {}           -- { {name, icon, t_end} }
KH._update_acc  = 0

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

-- ═══════════════════════════════════════════════════
-- Catalogue complet des buffs — format VanillaHUD
-- Chaque entrée contient : icône data + catégorie + ignore par défaut
-- ═══════════════════════════════════════════════════
KH.BUFF_CATEGORIES = {
    mastermind = "Mastermind",
    enforcer   = "Enforcer",
    technician = "Technician",
    ghost      = "Ghost",
    fugitive   = "Fugitive",
    perk       = "Perk Decks",
    debuff     = "Debuffs",
    team       = "Team Buffs",
    player_action = "Player Actions",
    gage       = "Gage Boosts",
    ai         = "AI Skills",
}

KH.BUFF_MAP = {
    -- ══ Mastermind ══
    single_shot_fast_reload = {
        skills_new = {1, 0},
        category = "mastermind",
        default_show = true,
    },
    aggressive_reload_aced = {
        skills_new = {1, 1},
        category = "mastermind",
        default_show = true,
    },
    inspire = {
        skills_new = {0, 9},
        category = "mastermind",
        default_show = true,
    },
    inspire_cooldown = {
        skills_new = {0, 9},
        category = "mastermind",
        default_show = true,
    },
    inspire_debuff = {
        skills_new = {0, 9},
        category = "debuff",
        default_show = true,
    },
    inspire_revive_debuff = {
        skills_new = {0, 9},
        category = "debuff",
        default_show = true,
    },
    combat_medic = {
        skills_new = {0, 0},
        category = "mastermind",
        default_show = true,
    },
    combat_medic_passive = {
        skills_new = {0, 0},
        category = "mastermind",
        default_show = false,
    },
    quick_fix = {
        skills_new = {1, 3},
        category = "mastermind",
        default_show = false,
    },
    uppers = {
        skills_new = {1, 2},
        category = "mastermind",
        default_show = true,
    },
    painkiller = {
        skills_new = {0, 4},
        category = "mastermind",
        default_show = false,
    },
    hostage_taker = {
        skills_new = {1, 5},
        category = "mastermind",
        default_show = false,
    },
    partner_in_crime = {
        skills_new = {0, 6},
        category = "mastermind",
        default_show = false,
    },
    forced_friendship = {
        skills_new = {0, 7},
        category = "team",
        default_show = true,
    },
    ammo_efficiency = {
        skills_new = {0, 8},
        category = "mastermind",
        default_show = true,
    },

    -- ══ Enforcer ══
    overkill = {
        skills_new = {2, 0},
        category = "enforcer",
        default_show = false,
    },
    bullet_storm = {
        skills_new = {2, 3},
        category = "enforcer",
        default_show = true,
    },
    die_hard = {
        skills_new = {2, 4},
        category = "enforcer",
        default_show = false,
    },
    iron_man = {
        skills_new = {2, 6},
        category = "enforcer",
        default_show = true,
    },
    underdog = {
        skills_new = {2, 1},
        category = "enforcer",
        default_show = false,
    },
    bullseye_debuff = {
        skills_new = {2, 8},
        category = "debuff",
        default_show = true,
    },
    bulletproof = {
        perks = {6, 2},
        category = "team",
        default_show = true,
    },

    -- ══ Technician ══
    lock_n_load = {
        skills_new = {3, 0},
        category = "technician",
        default_show = true,
    },

    -- ══ Ghost ══
    second_wind = {
        skills_new = {4, 1},
        category = "ghost",
        default_show = true,
    },
    unseen_strike = {
        skills_new = {4, 5},
        category = "ghost",
        default_show = true,
    },
    sixth_sense = {
        skills_new = {4, 7},
        category = "ghost",
        default_show = true,
    },
    dire_need = {
        skills_new = {4, 8},
        category = "ghost",
        default_show = true,
    },

    -- ══ Fugitive ══
    berserker = {
        skills_new = {5, 0},
        category = "fugitive",
        default_show = true,
    },
    swan_song = {
        skills_new = {5, 3},
        category = "fugitive",
        default_show = false,
    },
    trigger_happy = {
        skills_new = {5, 4},
        category = "fugitive",
        default_show = false,
    },
    desperado = {
        skills_new = {5, 5},
        category = "fugitive",
        default_show = true,
    },
    bloodthirst_basic = {
        skills_new = {5, 6},
        category = "fugitive",
        default_show = false,
    },
    bloodthirst_aced = {
        skills_new = {5, 6},
        category = "fugitive",
        default_show = true,
    },
    up_you_go = {
        skills_new = {5, 7},
        category = "fugitive",
        default_show = false,
    },
    running_from_death = {
        skills_new = {5, 8},
        category = "fugitive",
        default_show = true,
    },
    messiah = {
        skills_new = {5, 9},
        category = "fugitive",
        default_show = true,
    },
    frenzy = {
        skills_new = {5, 10},
        category = "fugitive",
        default_show = false,
    },

    -- ══ Perk Decks ══
    armor_break_invulnerable = {
        perks = {6, 1},
        category = "perk",
        default_show = true,
    },
    armorer = {
        perks = {6, 0},
        category = "team",
        default_show = true,
    },
    crew_chief = {
        perks = {2, 0},
        category = "team",
        default_show = true,
    },
    muscle_regen = {
        perks = {4, 1},
        category = "perk",
        default_show = false,
    },
    grinder = {
        perks = {4, 6},
        category = "perk",
        default_show = true,
    },
    sicario_dodge = {
        perks = {1, 0},
        texture_bundle_folder = "max",
        category = "perk",
        default_show = true,
    },
    smoke_screen_grenade = {
        perks = {0, 0},
        texture_bundle_folder = "max",
        category = "perk",
        default_show = true,
    },
    biker = {
        perks = {0, 0},
        texture_bundle_folder = "wild",
        category = "perk",
        default_show = true,
    },
    maniac = {
        perks = {0, 0},
        texture_bundle_folder = "coco",
        category = "perk",
        default_show = false,
    },
    tag_team = {
        perks = {0, 0},
        texture_bundle_folder = "ecp",
        category = "perk",
        default_show = true,
    },
    chico_injector = {
        perks = {0, 0},
        texture_bundle_folder = "chico",
        category = "perk",
        default_show = false,
    },
    pocket_ecm_jammer = {
        perks = {0, 0},
        texture_bundle_folder = "joy",
        category = "perk",
        default_show = true,
    },
    pocket_ecm_kill_dodge = {
        perks = {3, 0},
        texture_bundle_folder = "joy",
        category = "perk",
        default_show = false,
    },
    copr_ability = {
        perks = {0, 0},
        texture_bundle_folder = "copr",
        category = "perk",
        default_show = true,
    },
    copycat_health_invul = {
        perks = {3, 0},
        texture_bundle_folder = "mrwi",
        category = "perk",
        default_show = true,
    },
    copycat_health_shot = {
        perks = {1, 0},
        texture_bundle_folder = "mrwi",
        category = "perk",
        default_show = true,
    },
    delayed_damage = {
        perks = {3, 0},
        texture_bundle_folder = "myh",
        category = "perk",
        default_show = true,
    },
    close_contact = {
        perks = {5, 4},
        category = "perk",
        default_show = true,
    },
    overdog = {
        perks = {6, 4},
        category = "perk",
        default_show = false,
    },
    melee_stack_damage = {
        perks = {5, 4},
        category = "perk",
        default_show = false,
    },
    tooth_and_claw = {
        perks = {0, 3},
        category = "perk",
        default_show = true,
    },
    hostage_situation = {
        perks = {0, 1},
        category = "perk",
        default_show = false,
    },
    yakuza = {
        perks = {2, 7},
        category = "perk",
        default_show = false,
    },

    -- ══ Debuffs ══
    anarchist_armor_recovery_debuff = {
        perks = {0, 1},
        texture_bundle_folder = "opera",
        category = "debuff",
        default_show = true,
    },
    ammo_give_out_debuff = {
        perks = {5, 5},
        category = "debuff",
        default_show = true,
    },
    armor_break_invulnerable_debuff = {
        perks = {6, 1},
        category = "debuff",
        default_show = true,
    },
    sociopath_debuff = {
        perks = {3, 5},
        category = "debuff",
        default_show = true,
    },
    life_drain_debuff = {
        perks = {7, 4},
        category = "debuff",
        default_show = true,
    },
    medical_supplies_debuff = {
        perks = {4, 5},
        category = "debuff",
        default_show = true,
    },
    damage_control_debuff = {
        perks = {2, 0},
        texture_bundle_folder = "myh",
        category = "debuff",
        default_show = false,
    },

    -- ══ Player Actions ══
    anarchist_armor_regeneration = {
        perks = {0, 0},
        texture_bundle_folder = "opera",
        category = "player_action",
        default_show = true,
    },
    standard_armor_regeneration = {
        perks = {6, 0},
        category = "player_action",
        default_show = true,
    },
    weapon_charge = {
        texture = "guis/textures/weapon_charge",
        texture_rect = {1984, 0, 64, 64},
        category = "player_action",
        default_show = true,
    },
    melee_charge = {
        skills = {4, 5},  -- hidden_blade icon_xy
        category = "player_action",
        default_show = true,
    },
    reload = {
        skills = {0, 9},
        category = "player_action",
        default_show = true,
    },
    interact = {
        texture = "guis/textures/pd2/skilltree/drillgui_icon_faster",
        category = "player_action",
        default_show = true,
    },

    -- ══ Gage Boosts ══
    invulnerable_buff = {
        hud_tweak = "csb_melee",
        category = "gage",
        default_show = true,
    },
    life_steal_debuff = {
        hud_tweak = "csb_lifesteal",
        category = "gage",
        default_show = true,
    },

    -- ══ AI Skills ══
    crew_inspire_debuff = {
        hud_tweak = "ability_1",
        category = "ai",
        default_show = true,
    },
    crew_throwable_regen = {
        hud_tweak = "skill_7",
        category = "ai",
        default_show = true,
    },
    crew_health_regen = {
        hud_tweak = "skill_5",
        category = "ai",
        default_show = true,
    },

    -- ══ Buffs composites (résumés) ══
    damage_increase = {
        skills_new = {2, 8},
        category = "fugitive",
        default_show = true,
    },
    damage_reduction = {
        skills_new = {5, 2},
        category = "fugitive",
        default_show = true,
    },
    melee_damage_increase = {
        skills_new = {4, 3},
        category = "fugitive",
        default_show = true,
    },
    passive_health_regen = {
        skills_new = {1, 11},
        category = "mastermind",
        default_show = true,
    },
    total_dodge_chance = {
        skills_new = {1, 12},
        category = "ghost",
        default_show = true,
    },
}

-- Mapping upgrade_id → buff_id pour les hooks
-- Certains upgrades correspondent à des buff_id différents
KH.UPGRADE_TO_BUFF = {
    -- Temporary upgrades
    unseen_strike               = "unseen_strike",
    second_wind                 = "second_wind",
    overkill_damage_multiplier  = "overkill",
    dmg_multiplier_outnumbered  = "underdog",
    bullet_storm                = "bullet_storm",
    inspire                     = "inspire",
    inspire_cooldown            = "inspire_debuff",
    ammo_efficiency             = "ammo_efficiency",
    hostage_taker               = "hostage_taker",
    berserker_damage_multiplier = "berserker",
    swan_song                   = "swan_song",
    bloodthirst                 = "bloodthirst_aced",
    armor_break_invulnerable    = "armor_break_invulnerable",
    sicario_dodge               = "sicario_dodge",
    combat_medic                = "combat_medic",
    quick_fix                   = "quick_fix",
    up_you_go                   = "up_you_go",
    running_from_death          = "running_from_death",
    trigger_happy               = "trigger_happy",
    desperado                   = "desperado",
    dire_need                   = "dire_need",
    sixth_sense                 = "sixth_sense",
    aggressive_reload_aced      = "aggressive_reload_aced",
    lock_n_load                 = "lock_n_load",
    close_contact               = "close_contact",
    overdog                     = "overdog",
    tooth_and_claw              = "tooth_and_claw",
    painkiller                  = "painkiller",
    iron_man                    = "iron_man",
    die_hard                    = "die_hard",
    frenzy                      = "frenzy",
    messiah                     = "messiah",
    crew_inspire_debuff         = "crew_inspire_debuff",
    invulnerable_buff           = "invulnerable_buff",

    -- Noms d'upgrade qui diffèrent du buff_id
    single_shot_fast_reload     = "single_shot_fast_reload",
    dmg_dampener_close_contact  = "close_contact",
}

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

    self._buffs[resolved_id] = {
        id       = resolved_id,
        icon     = icon_data or icon_for_buff(resolved_id),
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
    local entry = {
        name   = enemy_name or "Enemy",
        icon   = icon_for_enemy(enemy_type or "default"),
        start_t = t,
        t_end  = t + dur,
    }
    table.insert(self._kills, entry)

    while #self._kills > 20 do
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

    -- Espacement angulaire entre chaque icône (basé sur la taille de l'icône)
    -- L'arc-length entre deux icônes = icon_size + marge
    local margin = 4
    local spacing_px = icon_size + margin
    -- angle_step en degrés = (spacing_px / circumference) * 360
    local angle_step = (spacing_px / (2 * math.pi * radius)) * 360

    -- Direction : de start_deg vers end_deg (sens anti-horaire = angles croissants)
    -- start_deg = 315° (bas-droite), end_deg = 90° (haut)
    -- En traversant 0°/360°, le chemin est 315 → 360 → 0 → 90 = 135° de span
    local span = end_deg - start_deg
    if span < 0 then span = span + 360 end

    for i = 0, count - 1 do
        local angle_offset = angle_step * i
        -- Ne pas dépasser le span total
        if angle_offset > span then break end

        local angle_deg = start_deg + angle_offset
        -- Normaliser à [0, 360)
        if angle_deg >= 360 then angle_deg = angle_deg - 360 end

        local rad = math.rad(angle_deg)
        local x = cx + math.cos(rad) * radius
        local y = cy - math.sin(rad) * radius
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
        -- Tri stable par ID pour un ordre constant
        table.sort(buff_list, function(a, b) return a.id < b.id end)

        -- Positions séquentielles le long de l'arc
        local positions = compute_sequential_arc_positions(
            #buff_list, start_deg, end_deg, radius, cx, cy, size
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

    -- ── Dessiner le killfeed ──
    if s.enable_killfeed and #self._kills > 0 then
        local kill_radius = radius + size + 20
        local kill_positions = compute_sequential_arc_positions(
            #self._kills, 250, 290, kill_radius, cx, cy, size * 0.8
        )

        for idx, kill in ipairs(self._kills) do
            local pos = kill_positions[idx]
            if pos then
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
function KH:DebugSimulate(n, dur)
    self:DebugClear()
    n = n or 8
    dur = dur or 8

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
            start_t  = t_now,
            duration = dur,
            t_end    = t_now + dur,
        }
    end

    -- Simuler quelques kills
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
    if KH._update_acc < 0.05 then return end
    KH._update_acc = 0

    if KH:ensure_panel(false) then
        KH:draw()
    end
end)

log("[Kyosh1ro HUD] ky_buffhud.lua v2.0 chargé.")

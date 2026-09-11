-- ky_localization.lua — Translation loading + fallbacks
local MOD_NAME = "KyoHUD"

-- IMPORTANT: capture ModPath immediately upon file execution, as the global ModPath will be overwritten by BLT when other mods load.
local MY_MOD_PATH = ModPath

local function logi(msg)
    pcall(function() log("[" .. MOD_NAME .. "][Loc] " .. tostring(msg)) end)
end

-- Built-in fallbacks to ensure no "ERROR:" appears in menus
local function add_fallbacks(loc)
    loc:add_localized_strings({
        -- Main menu
        ky_menu_title = "KyoHUD - Killfeed & Combat Score",
        ky_menu_desc  = "Customizable buffs, killfeed, kill streaks and combat score",

        -- Options de base
        ky_opt_language           = "Language",
        ky_opt_language_desc      = "Choose the mod language. Reload the level to apply the change.",
        ky_opt_language_auto      = "Detection AUTO",
        ky_opt_language_english   = "English",
        ky_opt_language_french    = "Français",
        ky_opt_enable_killfeed      = "Enable KillFeed",
        ky_opt_enable_killfeed_desc = "Show eliminated enemies beneath the crosshair; scores and counters continue while the killfeed is hidden",
        ky_opt_killfeed_size        = "Killfeed Size",
        ky_opt_killfeed_size_desc   = "Number of kills shown in the killfeed (1-5). Default: 3",
        ky_opt_enable_buffs         = "Enable Buffs",
        ky_opt_enable_buffs_desc    = "Show VanillaHUD+ buffs in KyoHUD's horizontal row; individual visibility follows VanillaHUD+ settings",
        ky_opt_radius               = "Killfeed Vertical Offset",
        ky_opt_radius_desc          = "Vertical distance of the killfeed from the crosshair (128-291). Default: 250",
        ky_opt_buff_position_x      = "Buff Position X (%)",
        ky_opt_buff_position_x_desc = "Horizontal center of the buff row (0-100%). Default: 50%",
        ky_opt_buff_position_y      = "Buff Position Y (%)",
        ky_opt_buff_position_y_desc = "Vertical center of the buff row (0-100%). The default adapts to the active HUD.",
        ky_opt_show_total_score      = "Show Total Score",
        ky_opt_show_total_score_desc = "Show the heist total score widget. Disabling it also disables the Best Streak option.",
        ky_opt_show_best_streak      = "Show Best Streak",
        ky_opt_show_best_streak_desc = "Show the best continuous scoring streak below the total score.",
        ky_opt_score_position_x      = "Score Position X (%)",
        ky_opt_score_position_x_desc = "Horizontal center of the total score widget (0-100%). Default: 100%",
        ky_opt_score_position_y      = "Score Position Y (%)",
        ky_opt_score_position_y_desc = "Vertical center of the total score widget (0-100%). Default: 75%",
        ky_opt_opacity              = "Opacity",
        ky_opt_opacity_desc         = "HUD element opacity (10-100%). Default: 90%",
        ky_opt_icon_size            = "Icon Size",
        ky_opt_icon_size_desc       = "Size of buff/kill icons in pixels (32-40). Default: 32",
        ky_opt_reset                = "Reset to Defaults",
        ky_opt_reset_desc           = "Reset all settings to their default values",
        ky_opt_debug_sim            = "Preview Buffs & Kills",
        ky_opt_debug_sim_desc       = "Main menu only: preview buffs, special-enemy kill cards and priority-target banners; unavailable during a heist",
        ky_opt_debug_clear          = "Clear Preview",
        ky_opt_debug_clear_desc     = "Remove preview buffs and kills; the equipped perk deck remains visible",

        ky_hud_score_total       = "TOTAL SCORE",
        ky_hud_score_best_streak = "BEST STREAK",
        ky_hud_score_best_short  = "BEST",

        -- Labels drawn above a buff icon
        ky_hud_buff_label_inspire_cooldown = "Boost+",
        ky_hud_buff_label_inspire_revive   = "Revive",
        ky_hud_buff_label_damage_increase  = "Dmg+",
        ky_hud_buff_label_damage_reduction = "Dmg-",
        ky_hud_buff_label_melee_damage     = "M.Dmg+",
        ky_hud_buff_label_health_regen     = "HP+",
        ky_hud_buff_label_dodge_chance     = "Dodge",

        -- Kill streak banner
        ky_hud_combo_2     = "CLEAN PAIR",
        ky_hud_combo_2_2   = "DOUBLE TAP",
        ky_hud_combo_2_3   = "TWO FOR ONE",
        ky_hud_combo_3     = "EXCELLENT",
        ky_hud_combo_3_2   = "TRIPLE THREAT",
        ky_hud_combo_3_3   = "THREE OF A KIND",
        ky_hud_combo_4     = "OVERKILL",
        ky_hud_combo_4_2   = "FOUR DOWN",
        ky_hud_combo_4_3   = "QUAD STRIKE",
        ky_hud_combo_5     = "FRENZY",
        ky_hud_combo_5_2   = "HIGH FIVE",
        ky_hud_combo_5_3   = "FIVEFOLD FURY",
        ky_hud_combo_6     = "CARNAGE",
        ky_hud_combo_6_2   = "SIX FEET UNDER",
        ky_hud_combo_6_3   = "SIXFOLD SLAUGHTER",
        ky_hud_combo_7     = "MASSACRE",
        ky_hud_combo_7_2   = "LUCKY SEVEN",
        ky_hud_combo_7_3   = "SEVENTH HEAVEN",
        ky_hud_combo_8     = "EXTERMINATION",
        ky_hud_combo_8_2   = "EIGHT COUNT",
        ky_hud_combo_8_3   = "OCTUPLE ONSLAUGHT",
        ky_hud_combo_9     = "APOCALYPSE",
        ky_hud_combo_9_2   = "CLOUD NINE",
        ky_hud_combo_9_3   = "NINE LIVES DENIED",
        ky_hud_combo_10    = "PERFECT HEIST",
        ky_hud_combo_10_2  = "TEN OUT OF TEN",
        ky_hud_combo_10_3  = "DECADE OF DOOM",
        ky_hud_combo_chain = "KILL CHAIN",
        ky_hud_killdozer   = "KILLDOZER",
        ky_hud_dozer_down  = "DOZER DOWN",
        ky_hud_bulldozed   = "BULLDOZED",
        ky_hud_boss_eliminated = "BOSS ELIMINATED",
        ky_hud_dozer_tank_buster          = "TANK BUSTER",
        ky_hud_dozer_armor_breaker        = "ARMOR BREAKER",
        ky_hud_dozer_heavy_down           = "HEAVY DOWN",
        ky_hud_dozer_ive_got_the_big_guy = "I'VE GOT THE BIG GUY",
        ky_hud_medic_code_blue       = "CODE BLUE",
        ky_hud_medic_bad_medicine    = "BAD MEDICINE",
        ky_hud_medic_doctor_down     = "DOCTOR DOWN",
        ky_hud_cloaker_shadow_hunter = "SHADOW HUNTER",
        ky_hud_cloaker_counter_kick  = "COUNTER-KICK",
        ky_hud_cloaker_ambush_broken = "AMBUSH BROKEN",
        ky_hud_taser_power_outage    = "POWER OUTAGE",
        ky_hud_taser_circuit_breaker = "CIRCUIT BREAKER",
        ky_hud_taser_blackout        = "BLACKOUT",
        ky_hud_shield_breaker        = "SHIELD BREAKER",
        ky_hud_shield_phalanx_fall   = "PHALANX FALL",
        ky_hud_shield_barrier_down   = "BARRIER DOWN",
        ky_hud_shield_defense_denied = "DEFENSE DENIED",
        ky_hud_sniper_counter_sniper = "COUNTER-SNIPER",
        ky_hud_sniper_scope_breaker  = "SCOPE BREAKER",
        ky_hud_sniper_longshot_denied = "LONGSHOT DENIED",

        -- Streak tiers by weapon family. Like other banner labels, these medals remain in English for both languages.
        ky_hud_streak_shotgun_5      = "SHOTGUN SPREE",
        ky_hud_streak_shotgun_10     = "OPEN SEASON",
        ky_hud_streak_shotgun_15     = "BUCK WILD",
        ky_hud_streak_sniper_5       = "SNIPER SPREE",
        ky_hud_streak_sniper_10      = "SHARPSHOOTER",
        ky_hud_streak_sniper_15      = "BE THE BULLET",
        ky_hud_streak_akimbo_5       = "DOUBLE TROUBLE",
        ky_hud_streak_akimbo_10      = "GUNS BLAZING",
        ky_hud_streak_akimbo_15      = "TWICE THE FIREPOWER",
        ky_hud_streak_incendiary_3   = "BURN NOTICE",
        ky_hud_streak_incendiary_6   = "INCINERATION",
        ky_hud_streak_incendiary_10  = "HELLFIRE",
        ky_hud_streak_poison_3       = "TOXIC",
        ky_hud_streak_poison_6       = "VENOMOUS",
        ky_hud_streak_poison_10      = "BIOHAZARD",
        ky_hud_streak_melee_2        = "ONE-TWO",
        ky_hud_streak_melee_3        = "BONE CRACKER",
        ky_hud_streak_melee_4        = "PUMMEL",
        ky_hud_streak_melee_5        = "WRECKING CREW",
        ky_hud_streak_explosive_3    = "BOOM",
        ky_hud_streak_explosive_5    = "DEMOLITION",
        ky_hud_streak_explosive_8    = "BLAST ZONE",

        -- Heist cumulative kill medal. A single key: the damage buff icon serves as the name, and the tier reached precedes it.
        ky_hud_kill_medal_kills      = "KILLS",

        -- Event medals, awarded based on the kill conditions themselves.
        ky_hud_event_medal_first_strike = "First Strike",
        ky_hud_event_medal_grave     = "Grave",
        ky_hud_event_medal_low_hp    = "Last Breath",
        ky_hud_event_medal_reload    = "Reload This",
        ky_hud_event_medal_through_shield = "Through the Shield",
        ky_hud_event_medal_one_shot_two_kills = "Collateral",
        ky_hud_event_medal_revenge   = "Revenge",
        ky_hud_event_medal_bulltrue  = "Bulltrue",
        ky_hud_event_medal_showstopper = "Showstopper",
        ky_hud_event_medal_rope      = "Pull!",
        ky_hud_event_medal_rope_3    = "Free Fall",
        ky_hud_event_medal_rope_5    = "Air Sweep",
        ky_hud_event_medal_blindfire = "BlindFire",
        ky_hud_event_medal_first_blood = "First Blood",
        ky_hud_event_medal_hotswap   = "Hot Swap",
        ky_hud_event_medal_overwatch = "Overwatch",
        ky_hud_event_medal_long_shot = "Long Shot",
        ky_hud_event_medal_spray_down = "Spray Down",
        ky_hud_event_medal_no_flashbang = "No Flashbang",
        ky_hud_event_medal_air_kill  = "Air Kill",
        ky_hud_event_medal_wall_bang = "Wallbang",
        ky_hud_event_medal_loot_carrier = "Hands Off",
    })
end

Hooks:Add("LocalizationManagerPostInit", "KH_Localization", function(loc)
    -- Use MY_MOD_PATH (captured at load) and NOT the global ModPath
    local base = MY_MOD_PATH .. "loc/"
    local loaded = false

    logi("Searching for files in: " .. tostring(base))

    -- Fallbacks FIRST: add_localized_strings OVERWRITES existing keys, so files loaded subsequently (english then french) take priority.
    add_fallbacks(loc)

    -- Read this setting here because the localization hook precedes ky_options.lua.
    local language = 1
    local settings_paths = {
        SavePath .. "kyohud_settings.json",
        SavePath .. "kyosh1ro_hud_settings.json",
    }
    for _, settings_path in ipairs(settings_paths) do
        local settings_file = io.open(settings_path, "r")
        if settings_file then
            local raw = settings_file:read("*all")
            settings_file:close()
            local ok, data = pcall(json.decode, raw)
            if ok and type(data) == "table" then
                local saved_language = math.floor(tonumber(data.language) or 1)
                if saved_language >= 1 and saved_language <= 3 then
                    language = saved_language
                end
            end
            break
        end
    end

    -- Detect BLT language for automatic mode.
    local blt_lang = ""
    if BLT and BLT.Localization and BLT.Localization._current then
        blt_lang = tostring(BLT.Localization._current):lower()
    end

    -- Detect game language
    local game_french = false
    pcall(function()
        game_french = (SystemInfo:language():key() == Idstring("french"):key())
    end)

    -- Load the appropriate language file
    local try_files = {}
    local auto_french = blt_lang:match("^fr") or blt_lang:match("french") or game_french
    local wants_french = language == 3 or (language == 1 and auto_french)

    table.insert(try_files, base .. "english.json")
    if wants_french then
        table.insert(try_files, base .. "french.json")
    end

    for _, path in ipairs(try_files) do
        local readable = false
        if io.file_is_readable then
            readable = io.file_is_readable(path)
        elseif file and file.FileExists then
            readable = file.FileExists(path)
        else
            -- Attempt to open to verify
            local test = io.open(path, "r")
            if test then
                test:close()
                readable = true
            end
        end

        if readable then
            loc:load_localization_file(path)
            logi("Loaded: " .. path)
            loaded = true
        else
            logi("Not found: " .. path)
        end
    end

    if not loaded then
        logi("No localization file found, using internal fallbacks.")
    end
end)

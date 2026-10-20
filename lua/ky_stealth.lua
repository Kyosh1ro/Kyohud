-- lua/ky_stealth.lua — Stealth detection, medals and tied-civilian tracking
-- KyoHUD stealth first batch.
--
-- Capture strategy:
--   Native CopDamage:damage_* methods are PreHook'd to capture
--   whisper/cool/backstab BEFORE the original call. These methods are inherited
--   by HuskCopDamage (which only overrides die, not damage_*). So the capture
--   is present for both host (CopDamage:die -> event_info -> ConsumeStealthContext)
--   and client (HuskCopDamage:die -> chk_killshot -> on_killshot -> event_info
--   -> ConsumeStealthContext). PostHook on the same methods cleans residual
--   capture AFTER on_killshot has had a chance to consume it.
--
--   CopDamage:die PreHook remains as a fallback for direct death calls:
--   it captures only if no transaction capture
--   already exists for the unit, and never sets cool since the damage method
--   did not observe it.
--
-- Loaded in multiple SuperBLT contexts declared in mod.txt:
--   copdamage               -> PreHook/PostHook native damage transaction capture
--                              + PreHook die fallback
--   hudmanagerpd2           -> Reset integration
--   civilianlogicsurrender  -> Host tied-civilian confirmation
--   huskcopbrain            -> Client tied-civilian net event confirmation (PostHook)
--   interactionext          -> Local interaction intent capture for civilian tie
-- Each context uses its own idempotence guard.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

local TIE_INTENT_EXPIRY = 4.0

local TIE_INTERACTION_WHITELIST = {
    intimidate = true,
    intimidate_and_search = true,
    intimidate_with_contour = true,
    intimidate_and_search_with_contour = true,
}

local function local_player_unit()
    local ok, unit = pcall(function()
        return managers and managers.player and managers.player:player_unit()
    end)
    if not ok or not unit then return nil end
    local alive_ok, is_alive = pcall(alive, unit)
    return alive_ok and is_alive and unit or nil
end

local BACKSTAB_DOT_THRESHOLD = -0.3

KH._stealth_pre_die_states = KH._stealth_pre_die_states
    or setmetatable({}, { __mode = "k" })

KH._stealth_tied_units = KH._stealth_tied_units or {}
KH._stealth_tie_intents = KH._stealth_tie_intents
    or setmetatable({}, { __mode = "k" })

function KH:IsWhisperMode()
    local ok, wm = pcall(function()
        return managers and managers.groupai and managers.groupai:state()
            and managers.groupai:state():whisper_mode()
    end)
    return ok and wm == true
end

function KH:IsEnemyCool(unit)
    if not unit then return false end
    local alive_ok, is_alive = pcall(alive, unit)
    if not alive_ok or not is_alive then return false end
    local ok, cool = pcall(function()
        local movement = unit:movement()
        if not movement or not movement.cool then return nil end
        return movement:cool()
    end)
    return ok and cool == true
end

function KH:IsBackstabKill(enemy_unit)
    local player = local_player_unit()
    if not player or not enemy_unit then return false end

    local ok, result = pcall(function()
        local e_pos = enemy_unit:position()
        local p_pos = player:position()
        local dx = p_pos.x - e_pos.x
        local dy = p_pos.y - e_pos.y
        local len = math.sqrt(dx * dx + dy * dy)
        if len < 1 then return false end
        dx = dx / len
        dy = dy / len

        local fwd = enemy_unit:rotation():y()
        if not fwd then return false end
        local fx = fwd.x
        local fy = fwd.y
        local flen = math.sqrt(fx * fx + fy * fy)
        if flen < 0.001 then return false end
        fx = fx / flen
        fy = fy / flen

        local dot = dx * fx + dy * fy
        return dot < BACKSTAB_DOT_THRESHOLD
    end)
    return ok and result == true
end

local function is_civilian_unit(unit)
    if not unit then return false end
    local ok, unit_id = pcall(function()
        local base = unit:base()
        return base and base._tweak_table
    end)
    if not ok or not unit_id then return false end
    local civ_ok, is_civ = pcall(function()
        return CopDamage.is_civilian(unit_id)
    end)
    return civ_ok and is_civ == true
end

local function capture_stealth_state(unit, from_damage_method)
    if not unit then return end
    local whisper = KH:IsWhisperMode()
    if not whisper then return end

    local state = {
        cool = from_damage_method and KH:IsEnemyCool(unit) or false,
        whisper = true,
    }
    state.backstab = KH:IsBackstabKill(unit)
    return state
end

function KH:ConsumeStealthContext(unit)
    local state = unit and self._stealth_pre_die_states[unit]
    if state then
        self._stealth_pre_die_states[unit] = nil
        return state
    end
    return nil
end

local function stealth_capture_for_damage(self, attack_data)
    if not attack_data then return end
    local unit = self._unit
    if not unit then return end
    if KH._stealth_pre_die_states[unit] then return end
    if is_civilian_unit(unit) then return end

    local attacker = attack_data.attacker_unit
    local kill_source
    if KH.GetLocalKillSource then
        kill_source = KH:GetLocalKillSource(attacker)
    end
    if kill_source ~= "player" then return end

    local state = capture_stealth_state(unit, true)
    if state then
        KH._stealth_pre_die_states[unit] = state
    end
end

local function stealth_cleanup_for_damage(self, attack_data)
    if not attack_data then return end
    local unit = self._unit
    if unit then
        KH._stealth_pre_die_states[unit] = nil
    end
end

if RequiredScript == "lib/units/enemies/cop/copdamage"
        and not KH._stealth_copdamage_hooks_installed then

    -- These native methods are inherited by HuskCopDamage. Their complete
    -- transaction encloses both die and the later client on_killshot callback.
    for _, method in ipairs({
        "damage_bullet", "damage_melee", "damage_fire", "damage_explosion",
        "damage_dot", "damage_simple", "damage_tase", "damage_mission",
    }) do
        if type(CopDamage[method]) == "function" then
            Hooks:PreHook(CopDamage, method, "KH_StealthPre_" .. method, stealth_capture_for_damage)
            Hooks:PostHook(CopDamage, method, "KH_StealthPost_" .. method, stealth_cleanup_for_damage)
        end
    end

    Hooks:PreHook(CopDamage, "die", "KH_StealthPreDieFallback", function(self, attack_data)
        if not attack_data then return end
        local unit = self._unit
        if not unit then return end
        if KH._stealth_pre_die_states[unit] then return end
        if is_civilian_unit(unit) then return end

        local attacker = attack_data.attacker_unit
        local kill_source
        if KH.GetLocalKillSource then
            kill_source = KH:GetLocalKillSource(attacker)
        end
        if kill_source ~= "player" then return end

        local state = capture_stealth_state(unit, false)
        if state then
            KH._stealth_pre_die_states[unit] = state
        end
    end)

    KH._stealth_copdamage_hooks_installed = true
end

if RequiredScript == "lib/units/civilians/logics/civilianlogicsurrender"
        and not KH._stealth_civ_surrender_hooks_installed then

    if CivilianLogicSurrender and CivilianLogicSurrender.on_tied then
        Hooks:PostHook(CivilianLogicSurrender, "on_tied", "KH_StealthCivTiedHost", function(data, aggressor_unit, not_tied, can_flee)
            if not data or not data.unit then return end

            local unit = data.unit

            local intent = KH._stealth_tie_intents[unit]
            KH._stealth_tie_intents[unit] = nil
            if not intent then return end

            if not is_civilian_unit(unit) then return end

            local player = local_player_unit()
            if not player or aggressor_unit ~= player then return end

            if not_tied then return end
            if data.is_tied ~= true then return end

            local intent_t = tonumber(intent.t)
            local now_t = KH.now and KH.now()
            if intent_t and now_t and (now_t - intent_t) > TIE_INTENT_EXPIRY then return end

            local was_tied_before = data._kh_was_tied_before
            if was_tied_before then return end

            local unit_key = nil
            pcall(function() unit_key = unit:key() end)
            if not unit_key then return end

            if KH._stealth_tied_units[unit_key] then return end
            KH._stealth_tied_units[unit_key] = true

            if KH.ShowTiedCivilianMedal then
                KH._tied_civilian_variant_index = ((KH._tied_civilian_variant_index or 0)
                    % (KH.TIED_CIVILIAN_VARIANT_COUNT or 3)) + 1
                KH:ShowTiedCivilianMedal(KH._tied_civilian_variant_index, intent.whisper)
            elseif KH.ShowEventMedal then
                KH:ShowEventMedal("tied_civilian")
            end
        end)

        Hooks:PreHook(CivilianLogicSurrender, "on_tied", "KH_StealthCivTiedHostPreCapture", function(data, aggressor_unit, not_tied, can_flee)
            if data then
                data._kh_was_tied_before = data.is_tied == true
            end
        end)
    end

    KH._stealth_civ_surrender_hooks_installed = true
end

if RequiredScript == "lib/units/enemies/cop/huskcopbrain"
        and not KH._stealth_huskcopbrain_hooks_installed then

    if HuskCopBrain and HuskCopBrain.sync_net_event then
        Hooks:PostHook(HuskCopBrain, "sync_net_event", "KH_StealthHuskCopBrainNetEvent", function(self, event_id)
            if not Network:is_client() then return end
            if not event_id then return end
            local net_events = HuskCopBrain._NET_EVENTS
            if not net_events or event_id ~= net_events.surrender_civilian_tied then return end

            local unit = self._unit
            if not unit or not is_civilian_unit(unit) then return end

            local intent = KH._stealth_tie_intents[unit]
            KH._stealth_tie_intents[unit] = nil
            if not intent then return end

            local intent_t = tonumber(intent.t)
            local now_t = KH.now and KH.now()
            if intent_t and now_t and (now_t - intent_t) > TIE_INTENT_EXPIRY then return end

            if self._kh_prev_surrendered ~= false or self._surrendered ~= true then return end

            local unit_key = nil
            pcall(function() unit_key = unit:key() end)
            if not unit_key then return end

            if KH._stealth_tied_units[unit_key] then return end
            KH._stealth_tied_units[unit_key] = true

            if KH.ShowTiedCivilianMedal then
                KH._tied_civilian_variant_index = ((KH._tied_civilian_variant_index or 0)
                    % (KH.TIED_CIVILIAN_VARIANT_COUNT or 3)) + 1
                KH:ShowTiedCivilianMedal(KH._tied_civilian_variant_index, intent.whisper)
            elseif KH.ShowEventMedal then
                KH:ShowEventMedal("tied_civilian")
            end
        end)

        Hooks:PreHook(HuskCopBrain, "sync_net_event", "KH_StealthHuskCopBrainPreCapture", function(self, event_id)
            if not event_id then return end
            local net_events = HuskCopBrain._NET_EVENTS
            if not net_events or event_id ~= net_events.surrender_civilian_tied then return end
            self._kh_prev_surrendered = self._surrendered
        end)
    end

    KH._stealth_huskcopbrain_hooks_installed = true
end

if RequiredScript == "lib/units/interactions/interactionext"
        and not KH._stealth_interaction_hooks_installed then

    if IntimitateInteractionExt and IntimitateInteractionExt.interact then
        Hooks:PreHook(IntimitateInteractionExt, "interact", "KH_StealthInteractionCapture", function(self, player)
            if not self or not self._unit then return end
            local unit = self._unit
            KH._stealth_tie_intents[unit] = nil

            local lp = local_player_unit()
            if not lp or player ~= lp then return end

            if not is_civilian_unit(unit) then return end

            local interaction_id
            pcall(function() interaction_id = self.tweak_data end)
            if not interaction_id or not TIE_INTERACTION_WHITELIST[interaction_id] then return end

            local can_ok, can = pcall(function() return self:can_interact(player) end)
            if not can_ok or not can then return end

            local already_tied = false
            pcall(function()
                local td = self.tweak_data
                if td == "hostage_stay" or td == "hostage_move" or td == "hostage_convert"
                        or td == "hostage_trade" then
                    already_tied = true
                end
            end)
            if already_tied then return end

            local is_tie_attempt = false
            local eq_ok, eq_result = pcall(function()
                local td = self._tweak_data
                if not td then return false end
                if td.special_equipment ~= "cable_tie" then return false end
                local player_mgr = managers and managers.player
                -- The native query returns an equipment record, not a boolean.
                return player_mgr and player_mgr:has_special_equipment(td.special_equipment)
                    and true or false
            end)
            is_tie_attempt = eq_ok and eq_result == true
            if not is_tie_attempt then
                KH._stealth_tie_intents[unit] = nil
                return
            end

            KH._stealth_tie_intents[unit] = nil
            KH._stealth_tie_intents[unit] = {
                whisper = KH:IsWhisperMode(),
                t = KH.now and KH.now() or 0,
            }
        end)
    end

    KH._stealth_interaction_hooks_installed = true
end

if RequiredScript == "lib/managers/hudmanagerpd2"
        and not KH._stealth_hud_hooks_installed then

    local _orig_reset = KH.ResetHeistCombatState
    function KH:ResetHeistCombatState(rearm_bridge_sync)
        _orig_reset(self, rearm_bridge_sync)

        local states = self._stealth_pre_die_states
        if type(states) == "table" then
            for k in pairs(states) do states[k] = nil end
        end

        local tied = self._stealth_tied_units
        if type(tied) == "table" then
            for k in pairs(tied) do tied[k] = nil end
        end

        local intents = self._stealth_tie_intents
        if type(intents) == "table" then
            for k in pairs(intents) do intents[k] = nil end
        end

        self._tied_civilian_variant_index = nil
    end

    KH._stealth_hud_hooks_installed = true
end
-- Pager rewards: authoritative host decision or native success radio on clients.
-- A completed client interaction is only a request; its optimistic bluff counter
-- must never be used as proof of success. No custom network messages are needed.
if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
KH._pager_state = KH._pager_state or {
    pending = setmetatable({}, { __mode = "k" }),
    awarded = setmetatable({}, { __mode = "k" }),
    samples = setmetatable({}, { __mode = "k" }),
    hooks = {},
    variant = 0,
}
local P = KH._pager_state
local RESPONSE_EXPIRY = 10
local LABELS = {
    { "ky_hud_pager_banner_1", "PAGER ANSWERED" },
    { "ky_hud_pager_banner_2", "ALL CLEAR" },
    { "ky_hud_pager_banner_3", "NOTHING TO REPORT" },
}

local function local_player()
    local ok, player = pcall(function() return managers.player:player_unit() end)
    return ok and player or nil
end

local function whisper_mode()
    local ok, whisper = pcall(function() return managers.groupai:state():whisper_mode() end)
    return ok and whisper == true
end

local function game_time()
    local ok, t = pcall(function() return TimerManager:game():time() end)
    return ok and tonumber(t) or nil
end

local function success_count()
    local ok, n = pcall(function()
        return managers.groupai:state():get_nr_successful_alarm_pager_bluffs()
    end)
    return ok and tonumber(n) or nil
end

function KH:ResetPagerState()
    for _, state in ipairs({P.pending, P.awarded, P.samples}) do
        for key in pairs(state) do state[key] = nil end
    end
    P.variant = 0
end

function KH:MakePagerBanner(variant)
    local label = LABELS[variant or 1] or LABELS[1]
    return {
        kind = "pager",
        multikill_style = true,
        label = self.localized_text(label[1], label[2]),
        color = self.STEALTH_KILLFEED_COLOR,
    }
end

function KH:GetPagerIconDescriptor()
    local texture, rect = self.get_icon_data({preplanning = 32})
    return {texture = texture, rect = rect}
end

function KH:RewardAnsweredPager(unit)
    if not unit or P.awarded[unit] or not self.settings
            or not self.AddActionEntry or not self.GetActionScore then return end
    local score = self:GetActionScore("pager_answered")
    if not score then return end
    P.awarded[unit] = true
    P.pending[unit] = nil
    P.variant = P.variant % #LABELS + 1
    local text = self.localized_text("ky_hud_pager_answered", "Pager answered")
    self:AddActionEntry("pager_answered", text, score, self:GetPagerIconDescriptor())
    self:_show_special_banner(self.now(), self:MakePagerBanner(P.variant), false)
end

local context = RequiredScript
if P.hooks[context] then return end

if context == "lib/units/enemies/cop/copbrain" then
    Hooks:PreHook(CopBrain, "on_alarm_pager_interaction", "KH_PagerBeforeDecision", function(self, status, player)
        P.samples[self] = nil
        if Network:is_client() or status ~= "complete" or player ~= local_player() or not whisper_mode()
                or not self._alarm_pager_data then return end
        local count = success_count()
        if count then P.samples[self] = {count = count, unit = self._unit} end
    end)
    Hooks:PostHook(CopBrain, "on_alarm_pager_interaction", "KH_PagerAfterDecision", function(self)
        local sample = P.samples[self]
        P.samples[self] = nil
        if not sample then return end
        local count = success_count()
        if count and count > sample.count then KH:RewardAnsweredPager(sample.unit) end
    end)
    P.hooks[context] = true
elseif context == "lib/units/interactions/interactionext" then
    Hooks:PreHook(IntimitateInteractionExt, "interact", "KH_PagerClientRequest", function(self, player)
        if not Network:is_client() or not self._unit or self.tweak_data ~= "corpse_alarm_pager"
                or player ~= local_player() then return end
        local unit = self._unit
        P.pending[unit] = nil
        if P.awarded[unit] or not whisper_mode() then return end
        local ok, request = pcall(function()
            if not self:can_interact(player) then return nil end
            -- Match CopBrain:_get_radio_id without calling its diagnostic print.
            local id = unit:base()._tweak_table
            local character = tweak_data.character[id]
            local prefix = character and character.radio_prefix or ""
            local first = prefix .. "dsp_radio_fooled_1"
            local last = prefix .. "dsp_radio_fooled_4"
            local failed = prefix .. "dsp_radio_alarm_1"
            return {
                t = game_time(),
                first = SoundDevice:string_to_id(first),
                last = SoundDevice:string_to_id(last),
                failed = SoundDevice:string_to_id(failed),
            }
        end)
        if ok and request and request.t and request.first and request.last then
            P.pending[unit] = request
        end
    end)
    Hooks:PostHook(IntimitateInteractionExt, "_at_interact_interupt", "KH_PagerClientCancelled", function(self, player, complete)
        if not complete and player == local_player() then P.pending[self._unit] = nil end
    end)
    Hooks:PreHook(IntimitateInteractionExt, "sync_interacted", "KH_PagerOtherResponder", function(self, peer, player, status)
        -- Native completion is relayed to everyone EXCEPT the completing peer.
        -- Receiving it therefore disqualifies our local request in a race.
        if Network:is_client() and self.tweak_data == "corpse_alarm_pager"
                and (status == 3 or status == "complete") then
            P.pending[self._unit] = nil
        end
    end)
    P.hooks[context] = true
elseif context == "lib/units/enemies/cop/copsound" then
    -- UnitNetworkHandler:corpse_sound_play resolves the corpse then calls play
    -- with the host's numeric event ID. Living dominated guards use play too.
    -- This still runs when the player has muted audio: no sound playback result
    -- or timer is interpreted as success.
    Hooks:PostHook(CopSound, "play", "KH_PagerClientRadioResult", function(self, event_id, source, sync)
        if not Network:is_client() or sync == true then return end
        local unit = self._unit
        local request = unit and P.pending[unit]
        if not request then return end
        local t = game_time()
        if not t or t < request.t or t - request.t > RESPONSE_EXPIRY then
            P.pending[unit] = nil
            return
        end
        if event_id == request.failed then
            P.pending[unit] = nil
        elseif event_id == request.first or event_id == request.last then
            KH:RewardAnsweredPager(unit)
        end
    end)
    P.hooks[context] = true
end

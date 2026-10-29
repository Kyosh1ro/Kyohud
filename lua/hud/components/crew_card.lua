kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then
    Kyosh1roHUD = kyohud
end

kyohud.hud = kyohud.hud or {}

local FONT = "fonts/font_medium_mf"

local WHITE = Color(1, 1, 1)
local DIM = Color(0.7, 0.7, 0.7)
local HP_HI = Color(0.2, 0.8, 0.2)
local HP_MID = Color(1, 0.85, 0.2)
local HP_LO = Color(0.9, 0.2, 0.2)
local ARMOR_CLR = Color(0.4, 0.6, 0.9)
local WARN = Color(1, 0.85, 0.2)
local BAR_BG = Color(0.15, 0.15, 0.15)

local RH = {0.20, 0.17, 0.16, 0.17, 0.15, 0.15}

local function finite(v)
    return type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge
end

local function live(p)
    if p == nil or type(alive) ~= "function" then return false end
    local ok, result = pcall(alive, p)
    return ok and result == true
end

local function shape(p, x, y, w, h)
    if p:x() ~= x or p:y() ~= y or p:w() ~= w or p:h() ~= h then
        p:set_shape(x, y, w, h)
    end
end

local function remove_owned(parent, root)
    if not live(parent) or not live(root) then return end
    pcall(function()
        if parent:child(root:name()) == root then
            parent:remove(root)
        end
    end)
end

local function near(a, b)
    return finite(a) and finite(b) and math.abs(a - b) <= 0.5
end

local function color_near(a, b)
    return finite(a) and finite(b) and math.abs(a - b) <= 0.02
end

local function trim_utf8(text)
    local n = #text
    while n > 0 and text:byte(n) >= 128 and text:byte(n) < 192 do
        n = n - 1
    end
    return text:sub(1, n - 1)
end

local function measure(p)
    if type(p.text_rect) ~= "function" then return nil end
    local _, _, w, h = p:text_rect()
    if not (finite(w) and finite(h)) then return nil end
    return w, h
end

local function fmt_pct(ratio)
    if ratio == nil then return "--" end
    if not finite(ratio) then return "--" end
    if ratio < 0 or ratio > 1 then return "--" end
    return math.floor(ratio * 100 + 0.5) .. "%"
end

local function hp_color(ratio)
    if ratio == nil then return DIM end
    if not finite(ratio) then return DIM end
    if ratio > 0.6 then return HP_HI end
    if ratio > 0.3 then return HP_MID end
    return HP_LO
end

local function loc_name(character_name)
    if type(character_name) ~= "string" or character_name == "" then return nil end
    local ok, result = pcall(function()
        return managers.localization:text("menu_" .. character_name)
    end)
    if ok and type(result) == "string" and result ~= "" then
        return result
    end
    return nil
end

local function localized(key, fallback)
    local ok, text = pcall(function() return managers.localization:text(key) end)
    if ok and type(text) == "string" and text ~= "" and text ~= key then return text end
    return fallback or key
end

local function fmt_name(actor)
    if actor.ai then
        local display = loc_name(actor.character_name) or actor.name
        return (display or "AI") .. " " .. localized("ky_hud_crew_ai", "IA")
    end
    local n = actor.name
    if n == nil then return "--" end
    local s = n
    if finite(actor.level) then
        s = s .. " L" .. math.floor(actor.level)
    end
    if finite(actor.rank) and actor.rank > 0 then
        s = s .. " R" .. math.floor(actor.rank)
    end
    return s
end

local function fmt_weapon(actor)
    local w = actor.weapon
    if not w then return "--" end
    local nid = w.name_id and localized(w.name_id) or w.weapon_id or "--"
    local ammo = w.ammo
    if not ammo then return nid .. " --/--", " --/--" end
    local clip = ammo.current_clip
    local res = ammo.reserve
    local suffix = " " .. (finite(clip) and math.floor(clip) or "--") .. "/" .. (finite(res) and math.floor(res) or "--")
    return nid .. suffix, suffix
end

local function fmt_equipment(actor)
    local eq = actor.equipment
    if not eq then return "--", "", "--" end
    local dep = eq.deployable
    local eq_str = "--"
    local dep_suffix
    if dep then
        dep_suffix = " x" .. (finite(dep.amount) and dep.amount >= 0 and math.floor(dep.amount) or "--")
        eq_str = (dep.name_id and localized(dep.name_id) or dep.id or "?") .. dep_suffix
    end
    local cb = eq.cable_ties
    local cb_str = ""
    if cb and finite(cb.amount) and cb.amount >= 0 then
        cb_str = "x" .. math.floor(cb.amount)
    elseif cb and cb.amount == -1 then
        cb_str = "\226\136\158"
    end
    local pj = eq.projectile
    local pj_str = "--"
    if pj and finite(pj.amount) and pj.amount >= 0 then
        pj_str = (pj.kind or "?") .. " charge" .. math.floor(pj.amount)
    end
    return eq_str, cb_str, pj_str, dep_suffix
end

local function fmt_interaction(actor, t)
    local inter = actor.interaction
    if not inter then return "" end
    if not inter.enabled then return "" end
    if inter.success then return "" end
    local td = inter.tweak_data_id or "?"
    local dur = inter.duration
    local start = inter.started_t
    if not finite(dur) or dur <= 0 then return td end
    if not finite(start) then return td end
    if not finite(t) then t = 0 end
    local elapsed = t - start
    local frac = math.min(1, math.max(0, elapsed / dur))
    local pct = math.floor(frac * 100)
    return td .. " " .. pct .. "%"
end

local function fmt_status(actor)
    local d = actor.downs
    local ct = actor.condition_text
    local cp = actor.phase
    local has_downs = finite(d)
    local cond = (type(ct) == "string" and ct ~= "") and ct or (type(cp) == "string" and cp ~= "") and cp or nil

    if has_downs and cond then
        return math.floor(d) .. " " .. cond
    elseif has_downs then
        return tostring(math.floor(d))
    elseif cond then
        return cond
    end
    return "--"
end

local function get_name_color(actor)
    local c = actor.color
    if type(c) == "table" and finite(c.r) and finite(c.g) and finite(c.b) then
        return Color(c.r, c.g, c.b)
    end
    return WHITE
end

local function store_color(c)
    return {r = c and c.r or 0, g = c and c.g or 0, b = c and c.b or 0}
end

local CC = {}
local Card = {}
Card.__index = Card

function CC.new(parent, name)
    if not live(parent) then return nil end
    local ok_e, existing = pcall(function()
        return parent:child(name)
    end)
    if not ok_e or existing then return nil end

    local self = setmetatable({_parent = parent, _key = name, _cache = {}, _geo = nil, _exp = nil}, Card)
    local ok = pcall(function()
        self.root = parent:panel({name = name, layer = 1})
        self.root:set_visible(false)

        self._name_text = self.root:text({name = name .. "_nm", font = FONT, layer = 2, text = ""})

        self._hp_bg = self.root:rect({name = name .. "_hpbg", layer = 1, color = BAR_BG})
        self._health_fill = self.root:rect({name = name .. "_hpfl", layer = 2, color = HP_HI})
        self._health_text = self.root:text({name = name .. "_hptx", font = FONT, layer = 3, text = ""})

        self._ar_bg = self.root:rect({name = name .. "_arbg", layer = 1, color = BAR_BG})
        self._armor_fill = self.root:rect({name = name .. "_arfl", layer = 2, color = ARMOR_CLR})
        self._armor_text = self.root:text({name = name .. "_artx", font = FONT, layer = 3, text = ""})

        self._weapon_text = self.root:text({name = name .. "_wp", font = FONT, layer = 2, text = ""})

        self._equipment_text = self.root:text({name = name .. "_dp", font = FONT, layer = 2, text = ""})
        self._cables_text = self.root:text({name = name .. "_cb", font = FONT, layer = 2, text = ""})
        self._projectile_text = self.root:text({name = name .. "_pj", font = FONT, layer = 2, text = ""})

        self._interaction_text = self.root:text({name = name .. "_itx", font = FONT, layer = 2, text = ""})
        self._status_text = self.root:text({name = name .. "_st", font = FONT, layer = 2, text = ""})
    end)

    if not ok or not self.root then
        remove_owned(parent, self.root)
        return nil
    end

    return self
end

function Card:set_geometry(x, y, w, h)
    if not (finite(x) and finite(y) and finite(w) and finite(h) and w > 0 and h > 0) then
        self._geo = nil
        return
    end
    self._geo = {x = x, y = y, w = w, h = h}
    if live(self.root) then
        pcall(shape, self.root, x, y, w, h)
    end
end

function Card:_all_live()
    return live(self.root)
        and live(self._name_text)
        and live(self._hp_bg) and live(self._health_fill) and live(self._health_text)
        and live(self._ar_bg) and live(self._armor_fill) and live(self._armor_text)
        and live(self._weapon_text)
        and live(self._equipment_text) and live(self._cables_text) and live(self._projectile_text)
        and live(self._interaction_text) and live(self._status_text)
end

function Card:_rows()
    local h = self._geo.h
    local out = {}
    local y = 0
    for i = 1, 6 do
        local rh = h * RH[i]
        out[i] = {y = y, h = rh}
        y = y + rh
    end
    return out
end

function Card:_fit(p, key, text, size, allow_trim, suffix)
    self._cache = self._cache or {}
    local c = self._cache[key]
    local pw, ph = p:w(), p:h()
    if not c or c.src ~= text or c.sz ~= size or c.pw ~= pw or c.ph ~= ph then
        local fitted, fsize = text, size
        if p:font_size() ~= fsize then p:set_font_size(fsize) end
        if p:text() ~= fitted then p:set_text(fitted) end
        local tw, th = measure(p)
        if tw and (tw > pw or th > ph) then
            fsize = math.max(10 * self._geo.w / 280, math.min(size, size * math.min(pw / math.max(tw, 1), ph / math.max(th, 1))))
            if p:font_size() ~= fsize then p:set_font_size(fsize) end
            tw, th = measure(p)
            if allow_trim or suffix then
                local remaining = suffix and text:sub(1, #text - #suffix) or text
                while tw and tw > pw and #remaining > 0 do
                    remaining = trim_utf8(remaining)
                    fitted = remaining .. "..." .. (suffix or "")
                    p:set_text(fitted)
                    tw, th = measure(p)
                end
            end
        end
        c = {src = text, sz = size, pw = pw, ph = ph, text = fitted, fsize = fsize}
        self._cache[key] = c
    end
    if p:text() ~= c.text then p:set_text(c.text) end
    if p:font_size() ~= c.fsize then p:set_font_size(c.fsize) end
    return c
end

function Card:update(actor, t)
    actor = actor or {}
    if not self._geo then
        pcall(function() self.root:set_visible(false) end)
        return false
    end
    if not self:_all_live() then return false end

    local g = self._geo
    local rows = self:_rows()
    local w = g.w
    local exp = {}

    local ok = pcall(function()
        shape(self.root, g.x, g.y, w, g.h)
        self.root:set_visible(true)
        self.root:set_alpha(1)
        exp.root = {x = g.x, y = g.y, w = w, h = g.h}

        local r0 = rows[1]
        local name_str = fmt_name(actor)
        local name_color = get_name_color(actor)
        shape(self._name_text, 2, r0.y, w - 4, r0.h)
        self._name_text:set_visible(true)
        exp.name_text_geo = {x = 2, y = r0.y, w = w - 4, h = r0.h}
        exp.name_text = self:_fit(self._name_text, "nm", name_str, r0.h * 0.72, true)
        pcall(function() self._name_text:set_color(name_color) end)
        exp.name_color = store_color(name_color)

        local r1 = rows[2]
        local hp_data = actor.health
        local hp_valid = hp_data and hp_data.valid == true
        local hp_ratio = hp_valid and hp_data.ratio or nil
        local hp_str = fmt_pct(hp_ratio)
        local bar_margin = 2
        local bar_w = w * 0.60 - bar_margin
        local bar_h = r1.h * 0.60
        local bar_y = r1.y + r1.h * 0.20
        local hp_fill_w = 0
        if hp_valid and finite(hp_ratio) then
            hp_fill_w = math.max(0, math.min(1, hp_ratio)) * bar_w
        end
        shape(self._hp_bg, bar_margin, bar_y, bar_w, bar_h)
        self._hp_bg:set_visible(true)
        exp.hp_bg_geo = {x = bar_margin, y = bar_y, w = bar_w, h = bar_h}
        shape(self._health_fill, bar_margin, bar_y, hp_fill_w, bar_h)
        local hp_clr = hp_color(hp_ratio)
        pcall(function() self._health_fill:set_color(hp_clr) end)
        self._health_fill:set_visible(true)
        exp.health_fill_geo = {x = bar_margin, y = bar_y, w = hp_fill_w, h = bar_h}
        exp.health_fill_color = store_color(hp_clr)
        local hp_tx_x = w * 0.60
        local hp_tx_w = w * 0.40
        shape(self._health_text, hp_tx_x, r1.y, hp_tx_w, r1.h)
        self._health_text:set_visible(true)
        exp.health_text_geo = {x = hp_tx_x, y = r1.y, w = hp_tx_w, h = r1.h}
        exp.health_text = self:_fit(self._health_text, "hp", hp_str, r1.h * 0.78, false)
        pcall(function() self._health_text:set_color(hp_clr) end)
        exp.health_text_color = store_color(hp_clr)

        local r2 = rows[3]
        local ar_data = actor.armor
        local ar_valid = ar_data and ar_data.valid == true
        local ar_ratio = ar_valid and ar_data.ratio or nil
        local ar_str = fmt_pct(ar_ratio)
        local ar_bar_h = r2.h * 0.60
        local ar_bar_y = r2.y + r2.h * 0.20
        local ar_fill_w = 0
        if ar_valid and finite(ar_ratio) then
            ar_fill_w = math.max(0, math.min(1, ar_ratio)) * bar_w
        end
        shape(self._ar_bg, bar_margin, ar_bar_y, bar_w, ar_bar_h)
        self._ar_bg:set_visible(true)
        exp.ar_bg_geo = {x = bar_margin, y = ar_bar_y, w = bar_w, h = ar_bar_h}
        shape(self._armor_fill, bar_margin, ar_bar_y, ar_fill_w, ar_bar_h)
        local ar_clr = ar_valid and ARMOR_CLR or DIM
        pcall(function() self._armor_fill:set_color(ar_clr) end)
        self._armor_fill:set_visible(true)
        exp.armor_fill_geo = {x = bar_margin, y = ar_bar_y, w = ar_fill_w, h = ar_bar_h}
        exp.armor_fill_color = store_color(ar_clr)
        local ar_tx_x = w * 0.60
        local ar_tx_w = w * 0.40
        shape(self._armor_text, ar_tx_x, r2.y, ar_tx_w, r2.h)
        self._armor_text:set_visible(true)
        exp.armor_text_geo = {x = ar_tx_x, y = r2.y, w = ar_tx_w, h = r2.h}
        exp.armor_text = self:_fit(self._armor_text, "ar", ar_str, r2.h * 0.78, false)
        pcall(function() self._armor_text:set_color(ar_clr) end)
        exp.armor_text_color = store_color(ar_clr)

        local r3 = rows[4]
        local wp_str, wp_suffix = fmt_weapon(actor)
        shape(self._weapon_text, 2, r3.y, w - 4, r3.h)
        self._weapon_text:set_visible(true)
        exp.weapon_text_geo = {x = 2, y = r3.y, w = w - 4, h = r3.h}
        exp.weapon_text = self:_fit(self._weapon_text, "wp", wp_str, r3.h * 0.78, true, wp_suffix)
        pcall(function() self._weapon_text:set_color(WHITE) end)
        exp.weapon_text_color = store_color(WHITE)

        local r4 = rows[5]
        local eq_str, cb_str, pj_str, dep_suffix = fmt_equipment(actor)
        local eq_x = 2
        local eq_w = w * 0.34 - 2
        local cb_x = w * 0.34
        local cb_w = w * 0.33
        local pj_x = w * 0.67
        local pj_w = w * 0.33
        local eq_sz = r4.h * 0.80
        shape(self._equipment_text, eq_x, r4.y, eq_w, r4.h)
        shape(self._cables_text, cb_x, r4.y, cb_w, r4.h)
        shape(self._projectile_text, pj_x, r4.y, pj_w, r4.h)
        exp.equipment_text = self:_fit(self._equipment_text, "dp", eq_str, eq_sz, false, dep_suffix)
        exp.cables_text = self:_fit(self._cables_text, "cb", cb_str, eq_sz, false)
        exp.projectile_text = self:_fit(self._projectile_text, "pj", pj_str, eq_sz, false)
        self._equipment_text:set_visible(true)
        self._cables_text:set_visible(true)
        self._projectile_text:set_visible(true)
        exp.equipment_text_geo = {x = eq_x, y = r4.y, w = eq_w, h = r4.h}
        exp.cables_text_geo = {x = cb_x, y = r4.y, w = cb_w, h = r4.h}
        exp.projectile_text_geo = {x = pj_x, y = r4.y, w = pj_w, h = r4.h}
        pcall(function()
            self._equipment_text:set_color(DIM)
            self._cables_text:set_color(DIM)
            self._projectile_text:set_color(DIM)
        end)
        exp.equipment_text_color = store_color(DIM)
        exp.cables_text_color = store_color(DIM)
        exp.projectile_text_color = store_color(DIM)

        local r5 = rows[6]
        local int_str = fmt_interaction(actor, t)
        local status_str = fmt_status(actor)
        local int_x = 2
        local int_w = w * 0.50 - 2
        local st_x = w * 0.50
        local st_w = w * 0.50
        shape(self._interaction_text, int_x, r5.y, int_w, r5.h)
        shape(self._status_text, st_x, r5.y, st_w, r5.h)
        exp.interaction_text = self:_fit(self._interaction_text, "itx", int_str, r5.h * 0.78, true)
        exp.status_text = self:_fit(self._status_text, "st", status_str, r5.h * 0.78, true)
        self._interaction_text:set_visible(true)
        self._status_text:set_visible(true)
        exp.interaction_text_geo = {x = int_x, y = r5.y, w = int_w, h = r5.h}
        exp.status_text_geo = {x = st_x, y = r5.y, w = st_w, h = r5.h}
        local st_clr = (finite(actor.downs) and actor.downs > 0) and WARN or DIM
        pcall(function()
            self._interaction_text:set_color(WHITE)
            self._status_text:set_color(st_clr)
        end)
        exp.interaction_text_color = store_color(WHITE)
        exp.status_text_color = store_color(st_clr)
    end)

    if ok then
        -- Normalize only our own primitives; color alpha shares the Diesel channel.
        for _, p in ipairs({self._name_text, self._hp_bg, self._health_fill, self._health_text,
            self._ar_bg, self._armor_fill, self._armor_text, self._weapon_text,
            self._equipment_text, self._cables_text, self._projectile_text,
            self._interaction_text, self._status_text}) do
            local worked = pcall(function()
                p:set_alpha(1)
                -- Font is immutable in the constructor. Do not call Diesel's
                -- font()/set_font() bindings here, including for readback.
            end)
            if not worked then ok = false end
        end
    end
    if ok then
        self._exp = exp
        return true
    end
    pcall(function() self.root:set_visible(false) end)
    self._exp = nil
    return false
end

function Card:verify()
    self._verify_failure = nil
    if not self:_all_live() then return false end
    if not self._geo then return false end
    if not self._exp then return false end

    local result = true
    local context = "root-or-gauge"
    local function chk(cond, metric)
        if not cond then
            result = false
            if not self._verify_failure then self._verify_failure = context .. ":" .. (metric or "geometry-color-visibility") end
        end
    end

    local worked = pcall(function()
        local exp = self._exp

        chk(near(self.root:x(), exp.root.x))
        chk(near(self.root:y(), exp.root.y))
        chk(near(self.root:w(), exp.root.w))
        chk(near(self.root:h(), exp.root.h))
        chk(self.root:visible() == true)
        chk(self.root:alpha() == 1)

        local function chk_text(p, e, geo_e, color_e, label)
            context = label
            chk(near(p:x(), geo_e.x))
            chk(near(p:y(), geo_e.y))
            chk(near(p:w(), geo_e.w))
            chk(near(p:h(), geo_e.h))
            chk(p:visible() == true)
            chk(p:alpha() == 1)

            if e then
                chk(p:text() == e.text, "text")
                chk(near(p:font_size(), e.fsize), "font-size")
            end
            if color_e then
                local c = nil
                pcall(function() c = p:color() end)
                if c then
                    chk(color_near(c.r or 0, color_e.r))
                    chk(color_near(c.g or 0, color_e.g))
                    chk(color_near(c.b or 0, color_e.b))
                else
                    result = false
                end
            end
            local tw, th = measure(p)
            if tw then
                if not (tw <= p:w() + 0.5) then chk(false, string.format("extent-width=%.2f/%.2f", tw, p:w())) end
                if not (th <= p:h() + 0.5) then chk(false, string.format("extent-height=%.2f/%.2f", th, p:h())) end
            else
                result = false
            end
        end

        chk_text(self._name_text, exp.name_text, exp.name_text_geo, exp.name_color, "name")
        context = "health-gauge"

        chk(near(self._hp_bg:x(), exp.hp_bg_geo.x))
        chk(near(self._hp_bg:y(), exp.hp_bg_geo.y))
        chk(near(self._hp_bg:w(), exp.hp_bg_geo.w))
        chk(near(self._hp_bg:h(), exp.hp_bg_geo.h))
        chk(self._hp_bg:visible() == true)

        chk(near(self._health_fill:x(), exp.health_fill_geo.x))
        chk(near(self._health_fill:y(), exp.health_fill_geo.y))
        chk(near(self._health_fill:w(), exp.health_fill_geo.w))
        chk(near(self._health_fill:h(), exp.health_fill_geo.h))
        chk(self._health_fill:visible() == true)
        local hfc = nil
        pcall(function() hfc = self._health_fill:color() end)
        if hfc then
            chk(color_near(hfc.r or 0, exp.health_fill_color.r))
            chk(color_near(hfc.g or 0, exp.health_fill_color.g))
            chk(color_near(hfc.b or 0, exp.health_fill_color.b))
        else
            result = false
        end

        chk_text(self._health_text, exp.health_text, exp.health_text_geo, exp.health_text_color, "health")
        context = "armor-gauge"

        chk(near(self._ar_bg:x(), exp.ar_bg_geo.x))
        chk(near(self._ar_bg:y(), exp.ar_bg_geo.y))
        chk(near(self._ar_bg:w(), exp.ar_bg_geo.w))
        chk(near(self._ar_bg:h(), exp.ar_bg_geo.h))
        chk(self._ar_bg:visible() == true)

        chk(near(self._armor_fill:x(), exp.armor_fill_geo.x))
        chk(near(self._armor_fill:y(), exp.armor_fill_geo.y))
        chk(near(self._armor_fill:w(), exp.armor_fill_geo.w))
        chk(near(self._armor_fill:h(), exp.armor_fill_geo.h))
        chk(self._armor_fill:visible() == true)
        local afc = nil
        pcall(function() afc = self._armor_fill:color() end)
        if afc then
            chk(color_near(afc.r or 0, exp.armor_fill_color.r))
            chk(color_near(afc.g or 0, exp.armor_fill_color.g))
            chk(color_near(afc.b or 0, exp.armor_fill_color.b))
        else
            result = false
        end

        chk_text(self._armor_text, exp.armor_text, exp.armor_text_geo, exp.armor_text_color, "armor")
        chk_text(self._weapon_text, exp.weapon_text, exp.weapon_text_geo, exp.weapon_text_color, "weapon")
        chk_text(self._equipment_text, exp.equipment_text, exp.equipment_text_geo, exp.equipment_text_color, "equipment")
        chk_text(self._cables_text, exp.cables_text, exp.cables_text_geo, exp.cables_text_color, "cables")
        chk_text(self._projectile_text, exp.projectile_text, exp.projectile_text_geo, exp.projectile_text_color, "projectile")
        chk_text(self._interaction_text, exp.interaction_text, exp.interaction_text_geo, exp.interaction_text_color, "interaction")
        chk_text(self._status_text, exp.status_text, exp.status_text_geo, exp.status_text_color, "status")
    end)

    if not worked then return false end
    return result
end

function Card:destroy()
    if live(self._parent) and live(self.root) then
        remove_owned(self._parent, self.root)
    end
    self.root = nil
    self._parent = nil
    self._name_text = nil
    self._hp_bg = nil
    self._health_fill = nil
    self._health_text = nil
    self._ar_bg = nil
    self._armor_fill = nil
    self._armor_text = nil
    self._weapon_text = nil
    self._equipment_text = nil
    self._cables_text = nil
    self._projectile_text = nil
    self._interaction_text = nil
    self._status_text = nil
    self._cache = nil
    self._geo = nil
    self._exp = nil
end

kyohud.hud.crew_card = CC
return CC

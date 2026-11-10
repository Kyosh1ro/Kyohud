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
local INNER_TRACK_CLR = Color(11 / 255, 12 / 255, 14 / 255)
local RANK_CLR = Color(166 / 255, 171 / 255, 177 / 255)
local FIXED_BLUE = Color(0.35, 0.70, 0.95)

local STATE_HEADER_E = 30
local STATE_BG_H_E = 28
local STATE_TEXT_Y_E = 2
local STATE_TEXT_H_E = 24
local STATE_TEXT_FONT_E = 18
local STATE_ICON_SZ_E = 24
local STROKE_W_E = 1
local STROKE_CLR = Color(0.7, 0.2, 0.18)
local STROKE_ALPHA = 0.3
local COND_CLR = Color(0.9, 0.25, 0.2)

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

local ROMAN_VALS = {1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1}
local ROMAN_SYMS = {"M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"}
local ROMAN_MAX = 3999

local _roman_cache = {}
local function to_roman(num)
    if _roman_cache[num] then return _roman_cache[num] end
    if not finite(num) or num <= 0 or num > ROMAN_MAX then return nil end
    local n = math.floor(num)
    local r = ""
    for i = 1, #ROMAN_VALS do
        while n >= ROMAN_VALS[i] do
            r = r .. ROMAN_SYMS[i]
            n = n - ROMAN_VALS[i]
        end
    end
    _roman_cache[num] = r
    return r
end

local function fmt_rank_level(actor)
    if actor.ai then return "" end
    local rank = actor.rank
    local level = actor.level
    local has_rank = finite(rank) and rank > 0
    local has_level = finite(level)
    if has_rank and has_level then
        local roman = to_roman(math.floor(rank))
        if roman then
            return roman .. "\194\183" .. math.floor(level)
        end
        return math.floor(rank) .. "\194\183" .. math.floor(level)
    elseif has_rank then
        local roman = to_roman(math.floor(rank))
        if roman then
            return roman
        end
        return tostring(math.floor(rank))
    elseif has_level then
        return tostring(math.floor(level))
    end
    return ""
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
        return display or "AI"
    end
    local n = actor.name
    if n == nil then return "--" end
    return n
end

local function fmt_ammo_value(v)
    if finite(v) and v >= 0 then
        return string.format("%03d", math.floor(v))
    end
    return "---"
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
    local pj_suffix
    if pj and finite(pj.amount) and pj.amount >= 0 then
        pj_str = (pj.kind or "?") .. " charge" .. math.floor(pj.amount)
        pj_suffix = " charge" .. math.floor(pj.amount)
    end
    return eq_str, cb_str, pj_str, dep_suffix, pj_suffix
end

local _icon_cache = {}

local function resolve_icon(icon_id)
    if type(icon_id) ~= "string" or icon_id == "" then return nil end
    local cached = _icon_cache[icon_id]
    if cached then return cached end
    local result = nil
    pcall(function()
        if type(tweak_data) ~= "table" or type(tweak_data.hud_icons) ~= "table" then
            error("no hud_icons")
        end
        local path, rect = tweak_data.hud_icons:get_icon_data(icon_id)
        if type(path) ~= "string" or path == "" then error("bad path") end
        if type(rect) ~= "table" then error("bad rect") end
        local r1, r2, r3, r4 = rect[1], rect[2], rect[3], rect[4]
        if not (finite(r1) and finite(r2) and finite(r3) and finite(r4)) then
            error("bad rect nums")
        end
        if r3 <= 0 or r4 <= 0 then error("bad rect dims") end
        if type(DB) ~= "table" and type(DB) ~= "userdata" then error("no DB") end
        if type(DB.has) ~= "function" then error("no DB.has") end
        local tex_ids = Idstring("texture")
        local path_ids = Idstring(path)
        if not DB:has(tex_ids, path_ids) then error("not in DB") end
        result = {ok = true, texture = path, rect = {r1, r2, r3, r4}}
    end)
    if not result then
        result = {ok = false}
    end
    _icon_cache[icon_id] = result
    return result
end

local function lookup_dep_icon_id(actor)
    local ok, id = pcall(function()
        local dep = actor.equipment and actor.equipment.deployable
        if not dep or not dep.id then return nil end
        local td = tweak_data.equipments[dep.id]
        return td and td.icon or nil
    end)
    return ok and id or nil
end

local function lookup_pj_icon_id(actor)
    local ok, id = pcall(function()
        local pj = actor.equipment and actor.equipment.projectile
        if not pj or not pj.id then return nil end
        local bm = tweak_data.blackmarket
        local tdp = bm and bm.projectiles and bm.projectiles[pj.id]
        return tdp and tdp.icon or nil
    end)
    return ok and id or nil
end

local function fmt_qty(amount)
    if finite(amount) and amount >= 0 then return tostring(math.floor(amount)) end
    return "--"
end

local function fmt_qty_cb(amount)
    if finite(amount) and amount >= 0 then return tostring(math.floor(amount)) end
    if amount == -1 then return "\226\136\158" end
    return ""
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
    if actor.ai == true or actor.condition_icon == "mugshot_normal" then return "" end
    local ct = actor.condition_text
    local cp = actor.phase
    if type(ct) == "string" and ct ~= "" and ct ~= "normal" then return ct end
    if type(cp) == "string" and cp ~= "" and cp ~= "normal" then return cp end
    local icon = actor.condition_icon
    if icon == "mugshot_downed" or icon == "mugshot_cuffed" or icon == "mugshot_in_custody" then
        return icon:sub(9)
    elseif icon == "mugshot_swansong" then
        return "swansong"
    end
    return ""
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

local function _obs_tex_key(bm)
    local tn
    pcall(function() tn = bm:texture_name() end)
    if tn == nil then return nil end
    if type(tn) == "string" then return tn end
    local k
    pcall(function() k = tn:key() end)
    return k
end

local function _des_tex_key(res)
    if not res or not res.ok then return nil end
    local k
    pcall(function() k = Idstring(res.texture):key() end)
    if k then return k end
    return res.texture
end

local function _bind_icon(self, bm, cfield, res, want)
    if not want then
        self[cfield] = nil
        return true
    end
    if not res or not res.ok then
        self[cfield] = nil
        return true
    end
    local dk = _des_tex_key(res)
    local cached = self[cfield]
    local needs_bind = true
    if cached and cached.t == res.texture
        and cached.rx == res.rect[1] and cached.ry == res.rect[2]
        and cached.rw == res.rect[3] and cached.rh == res.rect[4] then
        local obs = _obs_tex_key(bm)
        if obs and dk and obs == dk then
            needs_bind = false
        end
    end
    if needs_bind then
        local ok = pcall(function()
            bm:set_image(res.texture, res.rect[1], res.rect[2], res.rect[3], res.rect[4])
        end)
        if not ok then return false end
        local obs = _obs_tex_key(bm)
        if not (obs and dk and obs == dk) then return false end
        self[cfield] = {
            t = res.texture,
            rx = res.rect[1], ry = res.rect[2],
            rw = res.rect[3], rh = res.rect[4],
        }
    end
    return true
end

local _HEART_TEX = "guis/dlcs/chico/textures/pd2/specialization/icons_atlas"
local _HEART_RECT = {64, 0, 64, 64}
local _heart_res = nil
local _heart_resolved = false
local function resolve_heart()
    if _heart_resolved then return _heart_res end
    _heart_resolved = true
    _heart_res = {ok = false}
    pcall(function()
        if type(DB) ~= "table" and type(DB) ~= "userdata" then error("no DB") end
        if type(DB.has) ~= "function" then error("no DB.has") end
        local can_call_idstring = false
        if type(Idstring) == "function" then
            can_call_idstring = true
        elseif type(Idstring) == "table" then
            local mt = getmetatable(Idstring)
            if mt and mt.__call then can_call_idstring = true end
        end
        if not can_call_idstring then error("no callable Idstring") end
        local tex_id = Idstring("texture")
        local path_id = Idstring(_HEART_TEX)
        if not DB:has(tex_id, path_id) then error("not in DB") end
        _heart_res = {ok = true, texture = _HEART_TEX, rect = {_HEART_RECT[1], _HEART_RECT[2], _HEART_RECT[3], _HEART_RECT[4]}}
    end)
    return _heart_res
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

        self._backdrop = self.root:rect({name = name .. "_bg", layer = -1, color = Color(0.02, 0.025, 0.03)})

        self._name_text = self.root:text({name = name .. "_nm", font = FONT, layer = 2, text = ""})
        self._peer_dot = self.root:rect({name = name .. "_pd", layer = 2, color = WHITE})
        self._rank_text = self.root:text({name = name .. "_rnk", font = FONT, layer = 2, text = ""})

        self._ar_bg = self.root:rect({name = name .. "_arbg", layer = 0, color = BAR_BG})
        self._armor_fill = self.root:rect({name = name .. "_arfl", layer = 1, color = ARMOR_CLR})
        self._hp_bg = self.root:rect({name = name .. "_hpbg", layer = 2, color = BAR_BG})
        self._health_fill = self.root:rect({name = name .. "_hpfl", layer = 3, color = HP_HI})
        self._health_text = self.root:text({name = name .. "_hptx", font = FONT, layer = 3, text = ""})
        self._armor_text = self.root:text({name = name .. "_artx", font = FONT, layer = 3, text = ""})

        self._weapon_text = self.root:text({name = name .. "_wp", font = FONT, layer = 2, text = ""})
        self._reserve_text = self.root:text({name = name .. "_rv", font = FONT, layer = 2, text = ""})
        self._inactive_ammo_text = self.root:text({name = name .. "_iaw", font = FONT, layer = 2, text = ""})

        self._equipment_text = self.root:text({name = name .. "_dp", font = FONT, layer = 2, text = ""})
        self._cables_text = self.root:text({name = name .. "_cb", font = FONT, layer = 2, text = ""})
        self._projectile_text = self.root:text({name = name .. "_pj", font = FONT, layer = 2, text = ""})

        self._deployable_icon = self.root:bitmap({name = name .. "_di", layer = 2, visible = false})
        self._cables_icon = self.root:bitmap({name = name .. "_ci", layer = 2, visible = false})
        self._projectile_icon = self.root:bitmap({name = name .. "_pi", layer = 2, visible = false})

        self._interaction_text = self.root:text({name = name .. "_itx", font = FONT, layer = 2, text = ""})
        self._status_text = self.root:text({name = name .. "_st", font = FONT, layer = 2, text = ""})

        self._downs_icon = self.root:bitmap({name = name .. "_dwni", layer = 2, visible = false})
        self._downs_text = self.root:text({name = name .. "_dwnt", font = FONT, layer = 2, text = ""})
        self._downs_label = self.root:text({name = name .. "_dwnl", font = FONT, layer = 2, text = ""})

        self._state_bg = self.root:rect({name = name .. "_stbg", layer = 0, color = Color(0.02, 0.025, 0.03), visible = false})
        self._condition_icon = self.root:bitmap({name = name .. "_condi", layer = 2, visible = false})
        self._down_top = self.root:rect({name = name .. "_dnt", layer = 4, color = STROKE_CLR, visible = false})
        self._down_bottom = self.root:rect({name = name .. "_dnb", layer = 4, color = STROKE_CLR, visible = false})
        self._down_left = self.root:rect({name = name .. "_dnl", layer = 4, color = STROKE_CLR, visible = false})
        self._down_right = self.root:rect({name = name .. "_dnr", layer = 4, color = STROKE_CLR, visible = false})
    end)

    if not ok or not self.root then
        remove_owned(parent, self.root)
        return nil
    end

    return self
end

function Card:set_geometry(x, y, w, h, raster)
    if not (finite(x) and finite(y) and finite(w) and finite(h) and w > 0 and h > 0) then
        self._geo = nil
        return
    end
    self._geo = {x = x, y = y, w = w, h = h}
    if type(raster) == "table" and finite(raster.scale) and raster.scale > 0
        and finite(raster.x) and finite(raster.y) then
        self._geo.raster = {scale = raster.scale, x = raster.x, y = raster.y}
    end
    if live(self.root) then
        pcall(shape, self.root, x, y, w, h)
    end
end

function Card:_all_live()
    return live(self.root)
        and live(self._backdrop)
        and live(self._name_text)
        and live(self._peer_dot)
        and live(self._rank_text)
        and live(self._hp_bg) and live(self._health_fill) and live(self._health_text)
        and live(self._ar_bg) and live(self._armor_fill) and live(self._armor_text)
        and live(self._weapon_text)
        and live(self._reserve_text)
        and live(self._inactive_ammo_text)
        and live(self._equipment_text) and live(self._cables_text) and live(self._projectile_text)
        and live(self._deployable_icon) and live(self._cables_icon) and live(self._projectile_icon)
        and live(self._interaction_text) and live(self._status_text)
        and live(self._downs_icon) and live(self._downs_text) and live(self._downs_label)
        and live(self._state_bg) and live(self._condition_icon)
        and live(self._down_top) and live(self._down_bottom)
        and live(self._down_left) and live(self._down_right)
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
            fsize = math.max(10 * self._geo.h / 120, math.min(size, size * math.min(pw / math.max(tw, 1), ph / math.max(th, 1))))
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
                if tw and tw > pw and suffix then
                    local bare = suffix:gsub("^%s+", "")
                    fitted = bare
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
    local w = g.w
    local e = g.h / 120
    local is_bot = actor.ai == true
    local not_bot = not is_bot
    local int_str = not_bot and fmt_interaction(actor, t) or ""
    local status_str = fmt_status(actor)
    local int_visible = int_str ~= ""
    local status_visible = status_str ~= ""
    local state_active = int_visible or status_visible
    local downed_decor = (actor.condition_icon == "mugshot_downed") and not_bot
    local body_offset = state_active and STATE_HEADER_E * e or 0

    local rows = self:_rows()
    for _, r in ipairs(rows) do
        r.y = r.y + body_offset
    end

    local left_w = (w - 12 * e) * 0.52
    local right_x = left_w + 12 * e
    local right_w = w - right_x
    local exp = {}

    local ok = pcall(function()
        shape(self.root, g.x, g.y - body_offset, w, g.h + body_offset)
        self.root:set_visible(true)
        self.root:set_alpha(1)
        exp.root = {x = g.x, y = g.y - body_offset, w = w, h = g.h + body_offset}

        local r0 = rows[1]
        local name_str = fmt_name(actor)
        local rank_str = fmt_rank_level(actor)

        local peer_clr = get_name_color(actor)

        local dot_size = 10 * (w / 280)
        local dot_x = 2

        local rank_sz = r0.h * 0.65
        if self._rank_text:font_size() ~= rank_sz then self._rank_text:set_font_size(rank_sz) end
        if self._rank_text:text() ~= rank_str then self._rank_text:set_text(rank_str) end
        local rank_ink_w, rank_ink_h = measure(self._rank_text)
        if not (rank_ink_w and rank_ink_h) then
            error("rank measure failed")
        end
        local rank_w = rank_ink_w
        local rank_x = left_w - 2 - rank_w
        local rank_y = r0.y
        shape(self._rank_text, rank_x, rank_y, rank_w, r0.h)
        self._rank_text:set_visible(not_bot)
        exp.rank_text_visible = not_bot
        pcall(function() self._rank_text:set_color(RANK_CLR) end)
        exp.rank_text_geo = {x = rank_x, y = rank_y, w = rank_w, h = r0.h}
        exp.rank_text = {text = rank_str, fsize = rank_sz}
        exp.rank_text_color = store_color(RANK_CLR)

        local name_x, name_w
        if is_bot then
            name_x = 2
            name_w = w - 4
        else
            name_x = dot_x + dot_size + 2
            name_w = rank_x - name_x - 2
            if name_w <= 0 then
                error("name budget exhausted")
            end
        end
        shape(self._name_text, name_x, r0.y, name_w, r0.h)
        self._name_text:set_visible(true)
        exp.name_text_geo = {x = name_x, y = r0.y, w = name_w, h = r0.h}
        exp.name_text = self:_fit(self._name_text, "nm", name_str, 20 * e, true)
        local name_clr = is_bot and FIXED_BLUE or peer_clr
        pcall(function() self._name_text:set_color(name_clr) end)
        exp.name_color = store_color(name_clr)

        local nm_tr_x, nm_tr_y, nm_tr_w, nm_tr_h = self._name_text:text_rect()
        if not (finite(nm_tr_y) and finite(nm_tr_h)) then nm_tr_y, nm_tr_h = 0, r0.h end
        local name_ink_cy = r0.y + nm_tr_y + nm_tr_h * 0.5
        local dot_y = name_ink_cy - dot_size * 0.5
        shape(self._peer_dot, dot_x, dot_y, dot_size, dot_size)
        self._peer_dot:set_visible(not_bot)
        exp.peer_dot_visible = not_bot
        pcall(function() self._peer_dot:set_color(peer_clr) end)
        exp.peer_dot_geo = {x = dot_x, y = dot_y, w = dot_size, h = dot_size}
        exp.peer_dot_color = store_color(peer_clr)

        local r1 = rows[2]
        local r2 = rows[3]
        local hp_data = actor.health
        local hp_valid = hp_data and hp_data.valid == true
        local hp_ratio = hp_valid and hp_data.ratio or nil
        local hp_str = fmt_pct(hp_ratio)
        local ar_data = actor.armor
        local ar_valid = ar_data and ar_data.valid == true
        local ar_ratio = ar_valid and ar_data.ratio or nil
        local ar_str = fmt_pct(ar_ratio)
        local armor_visible = not actor.ai

        local hp_fill_w, ar_fill_w, hp_bg_x, hp_bg_y, hp_bg_w, hp_bg_h
        local ar_bg_x, ar_bg_y, ar_bg_w, ar_bg_h

        if is_bot then
            local bar_w = 0.30 * (left_w - 8 * e)
            local bar_h = r1.h * 0.60
            local bar_y = r1.y + r1.h * 0.20
            hp_fill_w = 0
            if hp_valid and finite(hp_ratio) then
                hp_fill_w = math.max(0, math.min(1, hp_ratio)) * bar_w
            end
            ar_bg_x = 0; ar_bg_y = 0; ar_bg_w = 0; ar_bg_h = 0
            hp_bg_x = 2; hp_bg_y = bar_y; hp_bg_w = bar_w; hp_bg_h = bar_h
            ar_fill_w = 0
        else
            local outer_x = 2 * e
            local outer_w = left_w - 4 * e
            local outer_h = 18 * e
            local region_y = r1.y
            local region_h = r1.h + r2.h
            local outer_y = region_y + (region_h - outer_h) * 0.5
            local inner_x = outer_x + 2 * e
            local inner_y = outer_y + 2 * e
            local inner_w = outer_w - 4 * e
            local inner_h = 14 * e

            -- Round in screen pixels, not logical HUD units. Derive the outer
            -- height from the inner height and equal insets to preserve borders.
            local raster = g.raster
            if raster then
                local mapped, wx, wy = pcall(function()
                    return self.root:world_x(), self.root:world_y()
                end)
                if mapped and finite(wx) and finite(wy) then
                    local ps = raster.scale
                    local inset = math.max(1, math.floor(2 * e * ps + 0.5))
                    local inner_pixels = math.max(1, math.floor(14 * e * ps + 0.5))
                    outer_x = (math.floor(raster.x + (wx + outer_x) * ps + 0.5) - raster.x) / ps - wx
                    outer_y = (math.floor(raster.y + (wy + outer_y) * ps + 0.5) - raster.y) / ps - wy
                    outer_w = math.max(2 * inset + 1, math.floor(outer_w * ps + 0.5)) / ps
                    outer_h = (inner_pixels + 2 * inset) / ps
                    inner_x = outer_x + inset / ps
                    inner_y = outer_y + inset / ps
                    inner_w = outer_w - 2 * inset / ps
                    inner_h = inner_pixels / ps
                end
            end

            ar_bg_x = outer_x; ar_bg_y = outer_y; ar_bg_w = outer_w; ar_bg_h = outer_h
            hp_bg_x = inner_x; hp_bg_y = inner_y; hp_bg_w = inner_w; hp_bg_h = inner_h

            ar_fill_w = 0
            if ar_valid and finite(ar_ratio) then
                ar_fill_w = math.max(0, math.min(1, ar_ratio)) * outer_w
            end
            hp_fill_w = 0
            if hp_valid and finite(hp_ratio) then
                hp_fill_w = math.max(0, math.min(1, hp_ratio)) * inner_w
            end
        end

        local ar_fill_clr = is_bot and ARMOR_CLR or WHITE
        pcall(function() self._ar_bg:set_color(BAR_BG) end)
        shape(self._ar_bg, ar_bg_x, ar_bg_y, ar_bg_w, ar_bg_h)
        self._ar_bg:set_visible(armor_visible)
        pcall(function() self._armor_fill:set_color(ar_fill_clr) end)
        shape(self._armor_fill, ar_bg_x, ar_bg_y, ar_fill_w, ar_bg_h)
        self._armor_fill:set_visible(armor_visible)
        local hp_bg_clr = is_bot and BAR_BG or INNER_TRACK_CLR
        pcall(function() self._hp_bg:set_color(hp_bg_clr) end)
        shape(self._hp_bg, hp_bg_x, hp_bg_y, hp_bg_w, hp_bg_h)
        self._hp_bg:set_visible(true)

        local hp_clr
        if is_bot then
            hp_clr = FIXED_BLUE
        else
            hp_clr = peer_clr
        end
        shape(self._health_fill, hp_bg_x, hp_bg_y, hp_fill_w, hp_bg_h)
        pcall(function() self._health_fill:set_color(hp_clr) end)
        self._health_fill:set_visible(true)
        exp.hp_bg_geo = {x = hp_bg_x, y = hp_bg_y, w = hp_bg_w, h = hp_bg_h}
        exp.hp_bg_color = store_color(hp_bg_clr)
        exp.health_fill_geo = {x = hp_bg_x, y = hp_bg_y, w = hp_fill_w, h = hp_bg_h}
        exp.health_fill_color = store_color(hp_clr)
        exp.ar_bg_geo = {x = ar_bg_x, y = ar_bg_y, w = ar_bg_w, h = ar_bg_h}
        exp.ar_bg_color = store_color(BAR_BG)
        exp.armor_fill_geo = {x = ar_bg_x, y = ar_bg_y, w = ar_fill_w, h = ar_bg_h}
        exp.armor_fill_color = store_color(ar_fill_clr)
        exp.armor_visible = armor_visible

        local hp_tx_x = w * 0.60
        local hp_tx_w = w * 0.40
        shape(self._health_text, hp_tx_x, r1.y, hp_tx_w, r1.h)
        exp.health_text_geo = {x = hp_tx_x, y = r1.y, w = hp_tx_w, h = r1.h}
        self._health_text:set_visible(false)
        exp.health_text_visible = false
        exp.health_text = self:_fit(self._health_text, "hp", hp_str, r1.h * 0.78, false)
        pcall(function() self._health_text:set_color(hp_clr) end)
        exp.health_text_color = store_color(hp_clr)

        local ar_tx_x = w * 0.60
        local ar_tx_w = w * 0.40
        shape(self._armor_text, ar_tx_x, r2.y, ar_tx_w, r2.h)
        self._armor_text:set_visible(false)
        exp.armor_text_visible = false
        exp.armor_text_geo = {x = ar_tx_x, y = r2.y, w = ar_tx_w, h = r2.h}
        exp.armor_text = self:_fit(self._armor_text, "ar", ar_str, r2.h * 0.78, false)
        pcall(function() self._armor_text:set_color(ar_fill_clr) end)
        exp.armor_text_color = store_color(ar_fill_clr)

        local wp = actor.weapon
        local ammo = wp and wp.ammo
        local clip_val = ammo and ammo.current_clip
        local res_val = ammo and ammo.reserve
        local clip_str = fmt_ammo_value(clip_val)
        local res_str = "/" .. fmt_ammo_value(res_val)

        local ammo_y = r0.y
        local ammo_h = r0.h
        local desired_sz = 22 * e
        local clip_gap = 4 * e
        local heart_gap = 6 * e
        local heart_sz_val = 22 * e
        local count_gap = 3 * e
        local count_sz = 20 * e

        local heart_res = resolve_heart()
        local heart_available = heart_res and heart_res.ok

        self._downs_icon:set_visible(false)
        if self._downs_icon:visible() ~= false then error("heart hide no-op") end

        local heart_bound = true
        if heart_available then
            if not _bind_icon(self, self._downs_icon, "_heart_ic", heart_res, true) then
                heart_bound = false
            end
        else
            self._heart_ic = nil
        end

        local heart_visible = not_bot and heart_available and heart_bound

        local downs = actor.downs
        local count_str
        if finite(downs) and downs >= 0 then
            count_str = tostring(math.floor(downs))
        else
            count_str = "--"
        end

        self._downs_text:set_font_size(count_sz)
        self._downs_text:set_text(count_str)
        local count_ink_w = measure(self._downs_text)
        if not count_ink_w then count_ink_w = 20 * e end

        local count_x = w - count_ink_w - 4.5 * e
        local heart_x = count_x - heart_sz_val - count_gap
        local heart_cy = ammo_y + ammo_h * 0.5

        local label_visible = not_bot and not heart_visible
        local ammo_right_budget

        if heart_visible then
            ammo_right_budget = heart_x - heart_gap
        elseif label_visible then
            local label_sz = 16 * e
            self._downs_label:set_font_size(label_sz)
            self._downs_label:set_text("DOWN")
            local label_ink_w = measure(self._downs_label)
            if not label_ink_w then label_ink_w = 30 * e end
            local label_x = count_x - count_gap - label_ink_w
            shape(self._downs_label, label_x, ammo_y, label_ink_w + 0.5 * e, ammo_h)
            self._downs_label:set_visible(true)
            exp.downs_label = self:_fit(self._downs_label, "dwl", "DOWN", label_sz, false)
            pcall(function() self._downs_label:set_color(DIM) end)
            exp.downs_label_geo = {x = label_x, y = ammo_y, w = label_ink_w + 0.5 * e, h = ammo_h}
            exp.downs_label_visible = true
            exp.downs_label_color = store_color(DIM)
            ammo_right_budget = label_x - heart_gap
        else
            ammo_right_budget = right_x + right_w
        end

        if not label_visible then
            local label_sz = 16 * e
            self._downs_label:set_font_size(label_sz)
            self._downs_label:set_text("")
            exp.downs_label = self:_fit(self._downs_label, "dwl", "", label_sz, false)
            shape(self._downs_label, heart_x, ammo_y, 0, ammo_h)
            self._downs_label:set_visible(false)
            pcall(function() self._downs_label:set_color(DIM) end)
            exp.downs_label_geo = {x = heart_x, y = ammo_y, w = 0, h = ammo_h}
            exp.downs_label_visible = false
            exp.downs_label_color = store_color(DIM)
        end

        local ammo_avail = ammo_right_budget - right_x
        if ammo_avail < 20 * e then ammo_avail = 20 * e end

        local common_sz = desired_sz
        if not_bot then
            self._weapon_text:set_font_size(desired_sz)
            self._weapon_text:set_text(clip_str)
            local clip_mw = measure(self._weapon_text)
            self._reserve_text:set_font_size(desired_sz)
            self._reserve_text:set_text(res_str)
            local res_mw = measure(self._reserve_text)
            if clip_mw and res_mw then
                local total = clip_mw + clip_gap + res_mw
                if total > ammo_avail then
                    common_sz = desired_sz * ammo_avail / total
                end
            end
        end

        shape(self._weapon_text, right_x, ammo_y, ammo_avail, ammo_h)
        self._weapon_text:set_visible(not_bot)
        exp.weapon_text_visible = not_bot
        exp.weapon_text = self:_fit(self._weapon_text, "wp", clip_str, common_sz, false)
        pcall(function() self._weapon_text:set_color(WHITE) end)
        exp.weapon_text_color = store_color(WHITE)
        local clip_ink_w = measure(self._weapon_text)
        if not clip_ink_w then clip_ink_w = ammo_avail end
        shape(self._weapon_text, right_x, ammo_y, clip_ink_w + 0.5 * e, ammo_h)
        exp.weapon_text_geo = {x = right_x, y = ammo_y, w = clip_ink_w + 0.5 * e, h = ammo_h}

        local res_x = right_x + clip_ink_w + 0.5 * e + clip_gap
        local res_avail = ammo_right_budget - res_x
        if res_avail < 10 * e then res_avail = 10 * e end
        shape(self._reserve_text, res_x, ammo_y, res_avail, ammo_h)
        self._reserve_text:set_visible(not_bot)
        exp.reserve_text_visible = not_bot
        exp.reserve_text = self:_fit(self._reserve_text, "rv", res_str, common_sz, false)
        pcall(function() self._reserve_text:set_color(DIM) end)
        exp.reserve_text_color = store_color(DIM)
        local res_ink_w = measure(self._reserve_text)
        if not res_ink_w then res_ink_w = res_avail end
        shape(self._reserve_text, res_x, ammo_y, res_ink_w + 0.5 * e, ammo_h)
        exp.reserve_text_geo = {x = res_x, y = ammo_y, w = res_ink_w + 0.5 * e, h = ammo_h}

        shape(self._downs_icon, heart_x, heart_cy - heart_sz_val * 0.5, heart_sz_val, heart_sz_val)
        self._downs_icon:set_visible(heart_visible)
        pcall(function() self._downs_icon:set_color(WHITE) end)

        exp.downs_icon_geo = {x = heart_x, y = heart_cy - heart_sz_val * 0.5, w = heart_sz_val, h = heart_sz_val}
        exp.downs_icon_visible = heart_visible
        exp.downs_icon_color = store_color(WHITE)
        if heart_visible and heart_res then
            exp.downs_icon_texture = heart_res.texture
        end

        shape(self._downs_text, count_x, ammo_y, count_ink_w + 0.5 * e, ammo_h)
        self._downs_text:set_visible(not_bot)
        exp.downs_text_visible = not_bot
        exp.downs_text = self:_fit(self._downs_text, "dwt", count_str, count_sz, false)
        pcall(function() self._downs_text:set_color(WHITE) end)
        exp.downs_text_color = store_color(WHITE)
        local count_ink_w2 = measure(self._downs_text)
        if not count_ink_w2 then count_ink_w2 = count_ink_w end
        shape(self._downs_text, count_x, ammo_y, count_ink_w2 + 0.5 * e, ammo_h)
        exp.downs_text_geo = {x = count_x, y = ammo_y, w = count_ink_w2 + 0.5 * e, h = ammo_h}

        if not_bot then
            if heart_visible then
                self._downs_label:set_text("")
                self._downs_label:set_visible(false)
            end
        end

        local eq_str, cb_str, pj_str, dep_suffix, pj_suffix = fmt_equipment(actor)
        local eq_x = right_x
        local eq_w = right_w / 3
        local cb_x = right_x + right_w / 3
        local cb_w = right_w / 3
        local pj_x = right_x + 2 * right_w / 3
        local pj_w = right_w / 3
        local eq_sz = 20 * e

        local dep_icon_vis = false
        local cb_icon_vis = false
        local pj_icon_vis = false
        local dep_res, cb_res, pj_res

        if not_bot then
            local dep_icon_id = lookup_dep_icon_id(actor)
            if dep_icon_id then
                dep_res = resolve_icon(dep_icon_id)
                if dep_res and dep_res.ok then dep_icon_vis = true end
            end
            local has_cable = actor.equipment and actor.equipment.cable_ties ~= nil
            if has_cable then
                cb_res = resolve_icon("equipment_cable_ties")
                if cb_res and cb_res.ok then cb_icon_vis = true end
            end
            local pj_icon_id = lookup_pj_icon_id(actor)
            if pj_icon_id then
                pj_res = resolve_icon(pj_icon_id)
                if pj_res and pj_res.ok then pj_icon_vis = true end
            end
        end

        local disp_eq = eq_str
        local disp_cb = cb_str
        local disp_pj = pj_str
        local disp_eq_suffix = dep_suffix
        local disp_pj_suffix = pj_suffix

        local icon_sz = 22 * e

        local eq_ref_cy
        if is_bot then
            eq_ref_cy = hp_bg_y + hp_bg_h * 0.5
        else
            eq_ref_cy = ar_bg_y + ar_bg_h * 0.5
        end
        local eq_text_y = eq_ref_cy - r1.h * 0.5
        local icon_y = eq_ref_cy - icon_sz * 0.5

        local di_x = eq_x
        local di_y = icon_y
        local ci_x = cb_x
        local ci_y = icon_y
        local pi_x = pj_x
        local pi_y = icon_y
        shape(self._deployable_icon, di_x, di_y, icon_sz, icon_sz)
        shape(self._cables_icon, ci_x, ci_y, icon_sz, icon_sz)
        shape(self._projectile_icon, pi_x, pi_y, icon_sz, icon_sz)

        self._deployable_icon:set_visible(false)
        if self._deployable_icon:visible() ~= false then error("deployable hide no-op") end
        self._cables_icon:set_visible(false)
        if self._cables_icon:visible() ~= false then error("cables hide no-op") end
        self._projectile_icon:set_visible(false)
        if self._projectile_icon:visible() ~= false then error("projectile hide no-op") end

        local all_bound = true
        if not _bind_icon(self, self._deployable_icon, "_di_ic", dep_res, dep_icon_vis) then
            all_bound = false
        end
        if not _bind_icon(self, self._cables_icon, "_ci_ic", cb_res, cb_icon_vis) then
            all_bound = false
        end
        if not _bind_icon(self, self._projectile_icon, "_pj_ic", pj_res, pj_icon_vis) then
            all_bound = false
        end

        local di_actual = all_bound and dep_icon_vis
        local cb_actual = all_bound and cb_icon_vis
        local pj_actual = all_bound and pj_icon_vis

        if di_actual then
            local dep = actor.equipment and actor.equipment.deployable
            disp_eq = fmt_qty(dep and dep.amount)
            disp_eq_suffix = nil
        end
        if cb_actual then
            local cb = actor.equipment and actor.equipment.cable_ties
            disp_cb = fmt_qty_cb(cb and cb.amount)
        end
        if pj_actual then
            local pj = actor.equipment and actor.equipment.projectile
            disp_pj = fmt_qty(pj and pj.amount)
            disp_pj_suffix = nil
        end

        self._deployable_icon:set_visible(di_actual)
        self._cables_icon:set_visible(cb_actual)
        self._projectile_icon:set_visible(pj_actual)

        exp.deployable_icon_geo = {x = di_x, y = di_y, w = icon_sz, h = icon_sz}
        exp.deployable_icon_visible = di_actual
        exp.cables_icon_geo = {x = ci_x, y = ci_y, w = icon_sz, h = icon_sz}
        exp.cables_icon_visible = cb_actual
        exp.projectile_icon_geo = {x = pi_x, y = pi_y, w = icon_sz, h = icon_sz}
        exp.projectile_icon_visible = pj_actual
        if di_actual and dep_res then
            exp.deployable_icon_texture = dep_res.texture
        end
        if cb_actual and cb_res then
            exp.cables_icon_texture = cb_res.texture
        end
        if pj_actual and pj_res then
            exp.projectile_icon_texture = pj_res.texture
        end

        pcall(function()
            self._deployable_icon:set_color(WHITE)
            self._cables_icon:set_color(WHITE)
            self._projectile_icon:set_color(WHITE)
        end)
        exp.deployable_icon_color = store_color(WHITE)
        exp.cables_icon_color = store_color(WHITE)
        exp.projectile_icon_color = store_color(WHITE)

        local eq_tx_x, eq_tx_w = eq_x, eq_w
        local cb_tx_x, cb_tx_w = cb_x, cb_w
        local pj_tx_x, pj_tx_w = pj_x, pj_w
        local icon_margin = 2

        if di_actual then
            eq_tx_x = eq_x + icon_sz + icon_margin
            eq_tx_w = eq_x + eq_w - eq_tx_x
            if eq_tx_w < 0 then eq_tx_w = 0 end
        end
        if cb_actual then
            cb_tx_x = cb_x + icon_sz + icon_margin
            cb_tx_w = cb_x + cb_w - cb_tx_x
            if cb_tx_w < 0 then cb_tx_w = 0 end
        end
        if pj_actual then
            pj_tx_x = pj_x + icon_sz + icon_margin
            pj_tx_w = pj_x + pj_w - pj_tx_x
            if pj_tx_w < 0 then pj_tx_w = 0 end
        end

        shape(self._equipment_text, eq_tx_x, eq_text_y, eq_tx_w, r1.h)
        shape(self._cables_text, cb_tx_x, eq_text_y, cb_tx_w, r1.h)
        shape(self._projectile_text, pj_tx_x, eq_text_y, pj_tx_w, r1.h)

        exp.equipment_text = self:_fit(self._equipment_text, "dp", disp_eq, eq_sz, false, disp_eq_suffix)
        exp.cables_text = self:_fit(self._cables_text, "cb", disp_cb, eq_sz, false)
        exp.projectile_text = self:_fit(self._projectile_text, "pj", disp_pj, eq_sz, true, disp_pj_suffix)

        self._equipment_text:set_visible(not_bot)
        self._cables_text:set_visible(not_bot)
        self._projectile_text:set_visible(not_bot)

        exp.equipment_text_geo = {x = eq_tx_x, y = eq_text_y, w = eq_tx_w, h = r1.h}
        exp.cables_text_geo = {x = cb_tx_x, y = eq_text_y, w = cb_tx_w, h = r1.h}
        exp.projectile_text_geo = {x = pj_tx_x, y = eq_text_y, w = pj_tx_w, h = r1.h}

        pcall(function()
            self._equipment_text:set_color(DIM)
            self._cables_text:set_color(DIM)
            self._projectile_text:set_color(DIM)
        end)
        exp.equipment_text_color = store_color(DIM)
        exp.cables_text_color = store_color(DIM)
        exp.projectile_text_color = store_color(DIM)

        local body_bottom = is_bot and (hp_bg_y + hp_bg_h)
            or math.max(ar_bg_y + ar_bg_h, eq_text_y + r1.h, icon_y + icon_sz)

        -- Inactive weapon slot ammo row (humans only): the other slot's
        -- clip/reserve, gray nominal 16e vs the active 22e, below existing
        -- equipment content inside the owned backdrop. Bots hide the row and
        -- add no height; unknown is shown as ---/---, never invented.
        local ia_visible = not_bot
        local ia_str = ""
        local ia_sz = 16 * e
        local ia_x = 2 * e
        local ia_y = body_bottom
        local ia_w = 0
        local ia_h = 18 * e
        if ia_visible then
            local wp_sel = actor.weapon and actor.weapon.selection_index
            local other = (wp_sel == 1 and 2) or (wp_sel == 2 and 1) or nil
            local ia_data = other and actor.ammo_slots and actor.ammo_slots[other] or nil
            ia_str = fmt_ammo_value(ia_data and ia_data.current_clip)
                .. "/" .. fmt_ammo_value(ia_data and ia_data.reserve)
            ia_y = body_bottom + 2 * e
            ia_w = w - 4 * e
        end
        shape(self._inactive_ammo_text, ia_x, ia_y, ia_w, ia_h)
        self._inactive_ammo_text:set_visible(ia_visible)
        exp.inactive_ammo_text = self:_fit(self._inactive_ammo_text, "iaw", ia_str, ia_sz, false)
        exp.inactive_ammo_text_geo = {x = ia_x, y = ia_y, w = ia_w, h = ia_h}
        exp.inactive_ammo_text_visible = ia_visible
        pcall(function() self._inactive_ammo_text:set_color(DIM) end)
        exp.inactive_ammo_text_color = store_color(DIM)

        local content_bottom = math.max(r0.y + r0.h, body_bottom)
        if ia_visible and ia_y + ia_h > content_bottom then
            content_bottom = ia_y + ia_h
        end
        local backdrop_w = w
        if is_bot then
            local name_ink = measure(self._name_text)
            if not name_ink then error("name measure failed") end
            backdrop_w = math.min(w, math.max(name_x + name_ink, hp_bg_x + hp_bg_w) + 2 * e)
        end
        local backdrop_h = content_bottom - body_offset + 2 * e
        if backdrop_h > g.h then error("crew content exceeds card") end
        shape(self._backdrop, 0, body_offset, backdrop_w, backdrop_h)
        self._backdrop:set_color(Color(0.02, 0.025, 0.03))
        self._backdrop:set_alpha(0.65)
        self._backdrop:set_visible(true)
        exp.backdrop_geo = {x = 0, y = body_offset, w = backdrop_w, h = backdrop_h}

        local state_font = STATE_TEXT_FONT_E * e
        local state_text_y = STATE_TEXT_Y_E * e
        local state_text_h = STATE_TEXT_H_E * e
        local state_icon_sz = STATE_ICON_SZ_E * e
        local icon_offset = downed_decor and (state_icon_sz + 2 * e) or 0
        local condition_x = 2 * e
        self._condition_icon:set_visible(false)
        if self._condition_icon:visible() ~= false then error("condition hide no-op") end
        self._condition_icon:set_alpha(1)
        self._interaction_text:set_color(WHITE)
        self._status_text:set_color(WARN)
        self._state_bg:set_color(Color(0.02, 0.025, 0.03))
        self._state_bg:set_alpha(0.65)

        if state_active then
            shape(self._state_bg, 0, 0, w, STATE_BG_H_E * e)
            self._state_bg:set_color(Color(0.02, 0.025, 0.03))
            self._state_bg:set_alpha(0.65)
            self._state_bg:set_visible(true)
            exp.state_bg_geo = {x = 0, y = 0, w = w, h = STATE_BG_H_E * e}
            exp.state_bg_visible = true

            local st_str, st_x, st_w = status_str, 2 * e + icon_offset, 0
            local it_str, it_x, it_w = int_str, 2 * e, 0
            if status_visible and int_visible then
                local half_w = (w - 8 * e) * 0.5
                it_w = half_w
                condition_x = 2 * e + half_w + 4 * e
                st_x = condition_x + icon_offset
                st_w = half_w - icon_offset
            elseif status_visible then
                st_w = w - 4 * e - icon_offset
            else
                it_w = w - 4 * e
            end
            if st_w < 0 then error("state budget exhausted") end

            shape(self._status_text, st_x, state_text_y, st_w, state_text_h)
            self._status_text:set_visible(status_visible)
            exp.status_text = self:_fit(self._status_text, "st", st_str, state_font, true)
            exp.status_text_geo = {x = st_x, y = state_text_y, w = st_w, h = state_text_h}
            exp.status_text_visible = status_visible
            pcall(function() self._status_text:set_color(WARN) end)
            exp.status_text_color = store_color(WARN)

            if it_str ~= "" then
                shape(self._interaction_text, it_x, state_text_y, it_w, state_text_h)
                self._interaction_text:set_visible(true)
                exp.interaction_text = self:_fit(self._interaction_text, "itx", it_str, state_font, true)
                exp.interaction_text_geo = {x = it_x, y = state_text_y, w = it_w, h = state_text_h}
                exp.interaction_text_visible = true
                pcall(function() self._interaction_text:set_color(WHITE) end)
                exp.interaction_text_color = store_color(WHITE)
            else
                self._interaction_text:set_visible(false)
                self._interaction_text:set_text("")
                shape(self._interaction_text, 0, state_text_y, 0, state_text_h)
                exp.interaction_text = self:_fit(self._interaction_text, "itx", "", state_font, true)
                exp.interaction_text_geo = {x = 0, y = state_text_y, w = 0, h = state_text_h}
                exp.interaction_text_visible = false
                exp.interaction_text_color = store_color(WHITE)
            end

            if downed_decor then
                local cond_res = resolve_icon("mugshot_downed")
                local bound = cond_res and cond_res.ok
                    and _bind_icon(self, self._condition_icon, "_condition_ic", cond_res, true)
                shape(self._condition_icon, condition_x, state_text_y, state_icon_sz, state_icon_sz)
                self._condition_icon:set_visible(bound == true)
                pcall(function() self._condition_icon:set_color(COND_CLR) end)
                local pulse_t = finite(t) and t or 0
                local pulse_alpha = 0.775 + 0.225 * math.cos(math.pi * pulse_t)
                self._condition_icon:set_alpha(pulse_alpha)
                exp.condition_icon_geo = {x = condition_x, y = state_text_y, w = state_icon_sz, h = state_icon_sz}
                exp.condition_icon_visible = bound == true
                exp.condition_icon_color = store_color(COND_CLR)
                exp.condition_icon_alpha = pulse_alpha
                if bound then
                    exp.condition_icon_texture = cond_res.texture
                end

                local sw = STROKE_W_E * e
                local bd_x = 0
                local bd_y = body_offset
                shape(self._down_top, bd_x, bd_y, backdrop_w, sw)
                shape(self._down_bottom, bd_x, bd_y + backdrop_h - sw, backdrop_w, sw)
                shape(self._down_left, bd_x, bd_y, sw, backdrop_h)
                shape(self._down_right, bd_x + backdrop_w - sw, bd_y, sw, backdrop_h)
                local sa = STROKE_ALPHA
                self._down_top:set_visible(true)
                self._down_bottom:set_visible(true)
                self._down_left:set_visible(true)
                self._down_right:set_visible(true)
                pcall(function()
                    self._down_top:set_color(STROKE_CLR)
                    self._down_bottom:set_color(STROKE_CLR)
                    self._down_left:set_color(STROKE_CLR)
                    self._down_right:set_color(STROKE_CLR)
                    self._down_top:set_alpha(sa)
                    self._down_bottom:set_alpha(sa)
                    self._down_left:set_alpha(sa)
                    self._down_right:set_alpha(sa)
                end)
                exp.down_top_geo = {x = bd_x, y = bd_y, w = backdrop_w, h = sw}
                exp.down_top_visible = true
                exp.down_top_color = store_color(STROKE_CLR)
                exp.down_top_alpha = sa
                exp.down_bottom_geo = {x = bd_x, y = bd_y + backdrop_h - sw, w = backdrop_w, h = sw}
                exp.down_bottom_visible = true
                exp.down_bottom_color = store_color(STROKE_CLR)
                exp.down_bottom_alpha = sa
                exp.down_left_geo = {x = bd_x, y = bd_y, w = sw, h = backdrop_h}
                exp.down_left_visible = true
                exp.down_left_color = store_color(STROKE_CLR)
                exp.down_left_alpha = sa
                exp.down_right_geo = {x = bd_x + backdrop_w - sw, y = bd_y, w = sw, h = backdrop_h}
                exp.down_right_visible = true
                exp.down_right_color = store_color(STROKE_CLR)
                exp.down_right_alpha = sa
            else
                self._condition_icon:set_visible(false)
                shape(self._condition_icon, 0, 0, 0, 0)
                exp.condition_icon_geo = {x = 0, y = 0, w = 0, h = 0}
                exp.condition_icon_visible = false
                exp.condition_icon_alpha = 1
                self._down_top:set_visible(false)
                self._down_bottom:set_visible(false)
                self._down_left:set_visible(false)
                self._down_right:set_visible(false)
                shape(self._down_top, 0, 0, 0, 0)
                shape(self._down_bottom, 0, 0, 0, 0)
                shape(self._down_left, 0, 0, 0, 0)
                shape(self._down_right, 0, 0, 0, 0)
                exp.down_top_geo = {x = 0, y = 0, w = 0, h = 0}
                exp.down_top_visible = false
                exp.down_top_alpha = 1
                exp.down_bottom_geo = {x = 0, y = 0, w = 0, h = 0}
                exp.down_bottom_visible = false
                exp.down_bottom_alpha = 1
                exp.down_left_geo = {x = 0, y = 0, w = 0, h = 0}
                exp.down_left_visible = false
                exp.down_left_alpha = 1
                exp.down_right_geo = {x = 0, y = 0, w = 0, h = 0}
                exp.down_right_visible = false
                exp.down_right_alpha = 1
            end
        else
            self._state_bg:set_visible(false)
            shape(self._state_bg, 0, 0, 0, 0)
            exp.state_bg_geo = {x = 0, y = 0, w = 0, h = 0}
            exp.state_bg_visible = false
            self._condition_icon:set_visible(false)
            shape(self._condition_icon, 0, 0, 0, 0)
            exp.condition_icon_geo = {x = 0, y = 0, w = 0, h = 0}
            exp.condition_icon_visible = false
            exp.condition_icon_alpha = 1
            self._interaction_text:set_visible(false)
            self._interaction_text:set_text("")
            shape(self._interaction_text, 0, state_text_y, 0, state_text_h)
            exp.interaction_text = self:_fit(self._interaction_text, "itx", "", state_font, true)
            exp.interaction_text_geo = {x = 0, y = state_text_y, w = 0, h = state_text_h}
            exp.interaction_text_visible = false
            exp.interaction_text_color = store_color(WHITE)
            self._status_text:set_visible(false)
            self._status_text:set_text("")
            shape(self._status_text, 0, state_text_y, 0, state_text_h)
            exp.status_text = self:_fit(self._status_text, "st", "", state_font, true)
            exp.status_text_geo = {x = 0, y = state_text_y, w = 0, h = state_text_h}
            exp.status_text_visible = false
            exp.status_text_color = store_color(WARN)
            self._down_top:set_visible(false)
            self._down_bottom:set_visible(false)
            self._down_left:set_visible(false)
            self._down_right:set_visible(false)
            exp.down_top_geo = {x = 0, y = 0, w = 0, h = 0}
            exp.down_top_visible = false
            exp.down_top_alpha = 1
            exp.down_bottom_geo = {x = 0, y = 0, w = 0, h = 0}
            exp.down_bottom_visible = false
            exp.down_bottom_alpha = 1
            exp.down_left_geo = {x = 0, y = 0, w = 0, h = 0}
            exp.down_left_visible = false
            exp.down_left_alpha = 1
            exp.down_right_geo = {x = 0, y = 0, w = 0, h = 0}
            exp.down_right_visible = false
            exp.down_right_alpha = 1
        end
        if not downed_decor then
            for _, p in ipairs({self._down_top, self._down_bottom, self._down_left, self._down_right}) do
                shape(p, 0, 0, 0, 0)
                p:set_alpha(1)
            end
        end
    end)

    if ok then
        -- Normalize only our own primitives; color alpha shares the Diesel channel.
        for _, p in ipairs({self._name_text, self._peer_dot, self._rank_text,
            self._hp_bg, self._health_fill, self._health_text,
            self._ar_bg, self._armor_fill, self._armor_text, self._weapon_text,
            self._reserve_text, self._inactive_ammo_text,
            self._equipment_text, self._cables_text, self._projectile_text,
            self._deployable_icon, self._cables_icon, self._projectile_icon,
            self._interaction_text, self._status_text,
            self._downs_icon, self._downs_text, self._downs_label}) do
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
    if not self:_all_live() then return false end
    if not self._geo then return false end
    if not self._exp then return false end

    local result = true
    local function chk(cond)
        if not cond then
            result = false
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

        local bg = self._backdrop
        local bg_geo = exp.backdrop_geo
        chk(bg:parent() == self.root and bg:visible() == true)
        chk(near(bg:x(), bg_geo.x) and near(bg:y(), bg_geo.y))
        chk(near(bg:w(), bg_geo.w) and near(bg:h(), bg_geo.h))
        chk(color_near(bg:alpha(), 0.65))
        local bg_color = bg:color()
        chk(bg_color ~= nil and color_near(bg_color.r, 0.02)
            and color_near(bg_color.g, 0.025) and color_near(bg_color.b, 0.03))

        local function chk_text(p, e, geo_e, color_e, visible_e)
            if visible_e == nil then visible_e = true end
            chk(near(p:x(), geo_e.x))
            chk(near(p:y(), geo_e.y))
            chk(near(p:w(), geo_e.w))
            chk(near(p:h(), geo_e.h))
            chk(p:visible() == visible_e)
            chk(p:alpha() == 1)

            if e then
                chk(p:text() == e.text)
                chk(near(p:font_size(), e.fsize))
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
                chk(tw <= p:w() + 0.5)
                chk(th <= p:h() + 0.5)
            else
                result = false
            end
        end

        chk_text(self._name_text, exp.name_text, exp.name_text_geo, exp.name_color)

        chk(near(self._peer_dot:x(), exp.peer_dot_geo.x))
        chk(near(self._peer_dot:y(), exp.peer_dot_geo.y))
        chk(near(self._peer_dot:w(), exp.peer_dot_geo.w))
        chk(near(self._peer_dot:h(), exp.peer_dot_geo.h))
        chk(self._peer_dot:visible() == exp.peer_dot_visible)
        chk(self._peer_dot:alpha() == 1)
        local pdc = nil
        pcall(function() pdc = self._peer_dot:color() end)
        if pdc then
            chk(color_near(pdc.r or 0, exp.peer_dot_color.r))
            chk(color_near(pdc.g or 0, exp.peer_dot_color.g))
            chk(color_near(pdc.b or 0, exp.peer_dot_color.b))
        else
            result = false
        end

        chk_text(self._rank_text, exp.rank_text, exp.rank_text_geo, exp.rank_text_color, exp.rank_text_visible)

        chk(near(self._hp_bg:x(), exp.hp_bg_geo.x))
        chk(near(self._hp_bg:y(), exp.hp_bg_geo.y))
        chk(near(self._hp_bg:w(), exp.hp_bg_geo.w))
        chk(near(self._hp_bg:h(), exp.hp_bg_geo.h))
        chk(self._hp_bg:visible() == true)
        local hpbgc = nil
        pcall(function() hpbgc = self._hp_bg:color() end)
        if hpbgc then
            chk(color_near(hpbgc.r or 0, exp.hp_bg_color.r))
            chk(color_near(hpbgc.g or 0, exp.hp_bg_color.g))
            chk(color_near(hpbgc.b or 0, exp.hp_bg_color.b))
        else
            result = false
        end

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

        chk_text(self._health_text, exp.health_text, exp.health_text_geo, exp.health_text_color, exp.health_text_visible)

        chk(near(self._ar_bg:x(), exp.ar_bg_geo.x))
        chk(near(self._ar_bg:y(), exp.ar_bg_geo.y))
        chk(near(self._ar_bg:w(), exp.ar_bg_geo.w))
        chk(near(self._ar_bg:h(), exp.ar_bg_geo.h))
        chk(self._ar_bg:visible() == exp.armor_visible)
        local arbgc = nil
        pcall(function() arbgc = self._ar_bg:color() end)
        if arbgc then
            chk(color_near(arbgc.r or 0, exp.ar_bg_color.r))
            chk(color_near(arbgc.g or 0, exp.ar_bg_color.g))
            chk(color_near(arbgc.b or 0, exp.ar_bg_color.b))
        else
            result = false
        end

        chk(near(self._armor_fill:x(), exp.armor_fill_geo.x))
        chk(near(self._armor_fill:y(), exp.armor_fill_geo.y))
        chk(near(self._armor_fill:w(), exp.armor_fill_geo.w))
        chk(near(self._armor_fill:h(), exp.armor_fill_geo.h))
        chk(self._armor_fill:visible() == exp.armor_visible)
        local afc = nil
        pcall(function() afc = self._armor_fill:color() end)
        if afc then
            chk(color_near(afc.r or 0, exp.armor_fill_color.r))
            chk(color_near(afc.g or 0, exp.armor_fill_color.g))
            chk(color_near(afc.b or 0, exp.armor_fill_color.b))
        else
            result = false
        end

        chk_text(self._armor_text, exp.armor_text, exp.armor_text_geo, exp.armor_text_color, exp.armor_text_visible)
        chk_text(self._weapon_text, exp.weapon_text, exp.weapon_text_geo, exp.weapon_text_color, exp.weapon_text_visible)
        chk_text(self._reserve_text, exp.reserve_text, exp.reserve_text_geo, exp.reserve_text_color, exp.reserve_text_visible)
        chk_text(self._inactive_ammo_text, exp.inactive_ammo_text, exp.inactive_ammo_text_geo, exp.inactive_ammo_text_color, exp.inactive_ammo_text_visible)
        chk_text(self._equipment_text, exp.equipment_text, exp.equipment_text_geo, exp.equipment_text_color, exp.armor_visible)
        chk_text(self._cables_text, exp.cables_text, exp.cables_text_geo, exp.cables_text_color, exp.armor_visible)
        chk_text(self._projectile_text, exp.projectile_text, exp.projectile_text_geo, exp.projectile_text_color, exp.armor_visible)

        local function chk_icon(p, geo_e, vis_e, tex_e, color_e)
            chk(near(p:x(), geo_e.x))
            chk(near(p:y(), geo_e.y))
            chk(near(p:w(), geo_e.w))
            chk(near(p:h(), geo_e.h))
            chk(p:visible() == vis_e)
            chk(p:alpha() == 1)
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
            if tex_e then
                local tn = nil
                pcall(function() tn = p:texture_name() end)
                local tex_match = false
                if type(tn) == "string" then
                    tex_match = (tn == tex_e)
                elseif tn ~= nil then
                    pcall(function()
                        local expected = Idstring(tex_e)
                        tex_match = (tn:key() == expected:key())
                    end)
                end
                chk(tex_match)
            end
        end

        chk_icon(self._deployable_icon, exp.deployable_icon_geo, exp.deployable_icon_visible,
            exp.deployable_icon_texture, exp.deployable_icon_color)
        chk_icon(self._cables_icon, exp.cables_icon_geo, exp.cables_icon_visible,
            exp.cables_icon_texture, exp.cables_icon_color)
        chk_icon(self._projectile_icon, exp.projectile_icon_geo, exp.projectile_icon_visible,
            exp.projectile_icon_texture, exp.projectile_icon_color)

        chk_text(self._interaction_text, exp.interaction_text, exp.interaction_text_geo, exp.interaction_text_color, exp.interaction_text_visible)
        chk_text(self._status_text, exp.status_text, exp.status_text_geo, exp.status_text_color, exp.status_text_visible)

        chk_icon(self._downs_icon, exp.downs_icon_geo, exp.downs_icon_visible,
            exp.downs_icon_texture, exp.downs_icon_color)
        chk_text(self._downs_text, exp.downs_text, exp.downs_text_geo, exp.downs_text_color, exp.downs_text_visible)
        chk_text(self._downs_label, exp.downs_label, exp.downs_label_geo, exp.downs_label_color, exp.downs_label_visible)

        local sbg = self._state_bg
        local sbg_geo = exp.state_bg_geo
        chk(sbg:parent() == self.root)
        chk(sbg:visible() == exp.state_bg_visible)
        chk(near(sbg:x(), sbg_geo.x))
        chk(near(sbg:y(), sbg_geo.y))
        chk(near(sbg:w(), sbg_geo.w))
        chk(near(sbg:h(), sbg_geo.h))
        chk(color_near(sbg:alpha(), 0.65))
        local sbg_color = sbg:color()
        chk(sbg_color ~= nil and color_near(sbg_color.r, 0.02)
            and color_near(sbg_color.g, 0.025) and color_near(sbg_color.b, 0.03))

        local ci = self._condition_icon
        local ci_geo = exp.condition_icon_geo
        chk(ci:parent() == self.root)
        chk(ci:visible() == exp.condition_icon_visible)
        chk(near(ci:x(), ci_geo.x))
        chk(near(ci:y(), ci_geo.y))
        chk(near(ci:w(), ci_geo.w))
        chk(near(ci:h(), ci_geo.h))
        chk(color_near(ci:alpha(), exp.condition_icon_alpha))
        if exp.condition_icon_color then
            local cic = nil
            pcall(function() cic = ci:color() end)
            if cic then
                chk(color_near(cic.r or 0, exp.condition_icon_color.r))
                chk(color_near(cic.g or 0, exp.condition_icon_color.g))
                chk(color_near(cic.b or 0, exp.condition_icon_color.b))
            else
                result = false
            end
        end
        if exp.condition_icon_texture then
            local tn = nil
            pcall(function() tn = ci:texture_name() end)
            local tex_match = false
            if type(tn) == "string" then
                tex_match = (tn == exp.condition_icon_texture)
            elseif tn ~= nil then
                pcall(function()
                    local expected = Idstring(exp.condition_icon_texture)
                    tex_match = (tn:key() == expected:key())
                end)
            end
            chk(tex_match)
        end

        local function chk_stroke(p, geo_e, vis_e, color_e, alpha_e)
            chk(p:parent() == self.root)
            chk(p:visible() == vis_e)
            chk(near(p:x(), geo_e.x))
            chk(near(p:y(), geo_e.y))
            chk(near(p:w(), geo_e.w))
            chk(near(p:h(), geo_e.h))
            chk(color_near(p:alpha(), alpha_e))
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
        end

        chk_stroke(self._down_top, exp.down_top_geo, exp.down_top_visible, exp.down_top_color, exp.down_top_alpha)
        chk_stroke(self._down_bottom, exp.down_bottom_geo, exp.down_bottom_visible, exp.down_bottom_color, exp.down_bottom_alpha)
        chk_stroke(self._down_left, exp.down_left_geo, exp.down_left_visible, exp.down_left_color, exp.down_left_alpha)
        chk_stroke(self._down_right, exp.down_right_geo, exp.down_right_visible, exp.down_right_color, exp.down_right_alpha)
    end)

    if not worked then return false end
    return result
end

function Card:destroy()
    if live(self._parent) and live(self.root) then
        remove_owned(self._parent, self.root)
    end
    self.root = nil
    self._backdrop = nil
    self._parent = nil
    self._name_text = nil
    self._peer_dot = nil
    self._rank_text = nil
    self._hp_bg = nil
    self._health_fill = nil
    self._health_text = nil
    self._ar_bg = nil
    self._armor_fill = nil
    self._armor_text = nil
    self._weapon_text = nil
    self._reserve_text = nil
    self._inactive_ammo_text = nil
    self._equipment_text = nil
    self._cables_text = nil
    self._projectile_text = nil
    self._deployable_icon = nil
    self._cables_icon = nil
    self._projectile_icon = nil
    self._di_ic = nil
    self._ci_ic = nil
    self._pj_ic = nil
    self._interaction_text = nil
    self._status_text = nil
    self._downs_icon = nil
    self._downs_text = nil
    self._downs_label = nil
    self._heart_ic = nil
    self._condition_ic = nil
    self._state_bg = nil
    self._condition_icon = nil
    self._down_top = nil
    self._down_bottom = nil
    self._down_left = nil
    self._down_right = nil
    self._cache = nil
    self._geo = nil
    self._exp = nil
end

kyohud.hud.crew_card = CC
return CC

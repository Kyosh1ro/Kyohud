kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then
    Kyosh1roHUD = kyohud
end

kyohud.hud = kyohud.hud or {}

local L = {}

local REF_W = 1920
local REF_H = 1080
local MARGIN_FRAC = 0.02
local SCALE_MIN = 0.95
local SCALE_MAX = 1.05

local function finite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function posfinite(v)
    return finite(v) and v > 0
end

local function clamp_scale(s)
    if s == nil then return 1.0 end
    if type(s) == "string" then
        s = tonumber(s)
        if s == nil then return 1.0 end
    end
    if type(s) ~= "number" then return 1.0 end
    if s ~= s then return 1.0 end
    if s == math.huge then return 1.0 end
    if s <= 0 then return 1.0 end
    if s < SCALE_MIN then return SCALE_MIN end
    if s > SCALE_MAX then return SCALE_MAX end
    return s
end

function L.resolve(w, h, user_scale)
    local valid = posfinite(w) and posfinite(h)
    if not valid then
        return {
            valid = false,
            width = 0,
            height = 0,
            uniform_scale = 0,
            scale = clamp_scale(user_scale),
            margin_x = 0,
            margin_y = 0,
            available_x = 0,
            available_y = 0,
        }
    end
    local uw = w / REF_W
    local uh = h / REF_H
    local us = math.min(uw, uh)
    local s = clamp_scale(user_scale)
    local mx = w * MARGIN_FRAC
    local my = h * MARGIN_FRAC
    return {
        valid = true,
        width = w,
        height = h,
        uniform_scale = us,
        scale = s,
        margin_x = mx,
        margin_y = my,
        available_x = math.max(0, w - 2 * mx),
        available_y = math.max(0, h - 2 * my),
    }
end

function L.anchor_rect(geom, x_pct, y_pct, ref_w, ref_h)
    if geom == nil or type(geom) ~= "table" then
        return { x = 0, y = 0, w = 0, h = 0 }
    end
    local ax = geom.available_x or 0
    local ay = geom.available_y or 0
    local mx = geom.margin_x or 0
    local my = geom.margin_y or 0
    local us = geom.uniform_scale or 0
    local sc = geom.scale or 1

    if not finite(x_pct) then x_pct = 0 end
    if not finite(y_pct) then y_pct = 0 end
    if x_pct < 0 then x_pct = 0 end
    if x_pct > 100 then x_pct = 100 end
    if y_pct < 0 then y_pct = 0 end
    if y_pct > 100 then y_pct = 100 end

    local rw = 0
    if finite(ref_w) and ref_w > 0 then
        rw = ref_w * us * sc
    end
    local rh = 0
    if finite(ref_h) and ref_h > 0 then
        rh = ref_h * us * sc
    end

    if rw > ax then rw = ax end
    if rh > ay then rh = ay end
    if rw < 0 then rw = 0 end
    if rh < 0 then rh = 0 end

    local x = mx + (x_pct / 100) * ax - rw * 0.5
    local y = my + (y_pct / 100) * ay - rh * 0.5

    if x < mx then x = mx end
    if y < my then y = my end
    if x + rw > mx + ax then x = mx + ax - rw end
    if y + rh > my + ay then y = my + ay - rh end
    if x < mx then x = mx end
    if y < my then y = my end

    return { x = x, y = y, w = rw, h = rh }
end

-- E reference coordinates; the native reservation below remains independent.
function L.mission_objectives(w, h, scale, mission, objectives, reserve_native)
    local g = L.resolve(w, h, scale)
    if not g.valid then return nil end
    local e = g.uniform_scale * g.scale
    local x, y = 40 * e, 36 * e
    if reserve_native then y = math.min(100, h) + y end
    local width = math.min(640 * e, w - 2 * x)
    -- Keep the native centered timer readable when Mission is disabled.
    if not mission then width = math.min(width, w * 0.5 - x - 80 * e) end
    local objective_y = y + (mission and (44 + 3) * e or 0)
    if width <= 0 or y + 44 * e > h or objective_y + 120 * e > h then return nil end
    return { e = e, x = x, y = y, w = width, mission_h = 44 * e,
        objectives_y = objective_y, row_h = 41 * e, content_h = 38 * e,
        objectives_h = 123 * e }
end

function L.objectives_region(w, h)
    if not posfinite(w) or not posfinite(h) then
        return nil
    end
    return {
        x = 0,
        y = 0,
        w = math.min(500, w),
        h = math.min(100, h),
    }
end

function L.assault_alerts(parent_w, parent_h, scale, variant)
    local g = L.resolve(parent_w, parent_h, scale)
    if not g.valid then return nil end
    local es = g.uniform_scale * g.scale
    local RIGHT_MARGIN = 40 * es
    local TOP = 36 * es
    local TICKER_W = 340 * es
    local TICKER_H = 40 * es
    local GAP = 3 * es
    local STATUS_W = 40 * es
    local STATUS_H = 40 * es
    local COUNTER_VGAP = 4 * es
    local COUNTER_H = 26 * es
    local ROOT_W = TICKER_W + GAP + STATUS_W
    local ROOT_H = (variant == "casing") and TICKER_H or (TICKER_H + COUNTER_VGAP + COUNTER_H)
    local root_x = parent_w - RIGHT_MARGIN - ROOT_W
    local root_y = TOP
    if not finite(root_x) or not finite(root_y) then return nil end
    if root_x < 0 or root_y < 0 then return nil end
    if root_x + ROOT_W > parent_w or root_y + ROOT_H > parent_h then return nil end
    local obj = L.objectives_region(parent_w, parent_h)
    if obj and root_x < obj.w and root_y < obj.h then return nil end
    return {
        valid = true,
        es = es,
        root_x = root_x,
        root_y = root_y,
        root_w = ROOT_W,
        root_h = ROOT_H,
        ticker = { x = 0, y = 0, w = TICKER_W, h = TICKER_H },
        bg = { x = 0, y = 0, w = TICKER_W, h = TICKER_H },
        status = { x = TICKER_W + GAP, y = 0, w = STATUS_W, h = STATUS_H },
        counter_y = TICKER_H + COUNTER_VGAP,
        counter_h = COUNTER_H,
        ticker_font = math.max(12, math.floor(20 * es)),
        counter_font = math.max(10, math.floor(16 * es)),
        cell_pad = 10 * es,
        icon_size = 16 * es,
        icon_gap = 6 * es,
        cell_gap = 3 * es,
    }
end

-- Compact E loadout above the unchanged, elevated local gauge. The 380-wide
-- reference is the complete block target, not the width of either weapon column.
function L.local_loadout(w,h,scale)
    local g=L.resolve(w,h,scale)
    if not g.valid then return nil end
    local e=g.uniform_scale*g.scale
    if e<.35 then return nil end
    local rw,rh=380*e,102*e
    local x=w-g.margin_x-rw
    local player_y=h-g.margin_x-200*g.uniform_scale-120*e
    local y=player_y+(22-6)*e-rh
    if x<g.margin_x or y<g.margin_y or x+rw>w or y+rh>h then return nil end
    return {x=x,y=y,w=rw,h=rh,e=e}
end

kyohud.hud.layout = L

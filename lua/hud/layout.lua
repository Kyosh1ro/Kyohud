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
local SCALE_MIN = 0.5
local SCALE_MAX = 2.0

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

kyohud.hud.layout = L

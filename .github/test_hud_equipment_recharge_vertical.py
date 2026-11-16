"""Vertical equipment recharge fill tracer (TEST ONLY).

The recharge reveal must fill bottom-up: at progress p the owned
`_recharge_reveal` panel is x=0, y=row_height*(1-p), w=row_width,
h=row_height*p. Its silhouette children must use the existing
KILLFEED_SCORE_COLOR orange (1, 0.63, 0.12), preserve the icon/text
content, and stay inside the local reveal box without relying on panel
clipping. The right cut's captured triangle payload must have a bounding
box width of the full cut width times p, never the full cut width.

The fixture extends the presentation primitive mock with the native
CircleGuiObject polygon API (`clear` / `add_triangles`) before production
component chunks load. `add_triangles` eagerly copies x/y/z so a later
`mvector3.set_static` reuse of a cached vector cannot hide the observed
payload. `Vector3` calls are counted from the same pre-load window.
"""
import unittest

import test_hud_equipment_presentation as presentation_module
from test_hud_equipment_recharge_visual import _presentation_with_text_align

POLYGON_TRACER_FIXTURE = r'''
    _G._vector3_calls = 0
    local base_vector3 = Vector3
    if type(base_vector3) == 'function' then
        Vector3 = function(...)
            _G._vector3_calls = _G._vector3_calls + 1
            return base_vector3(...)
        end
    elseif type(base_vector3) == 'table' then
        local mt = getmetatable(base_vector3) or {}
        local base_call = mt.__call
        mt.__call = function(cls, ...)
            _G._vector3_calls = _G._vector3_calls + 1
            if base_call then return base_call(cls, ...) end
        end
        setmetatable(base_vector3, mt)
        if type(base_vector3.new) == 'function' then
            local base_new = base_vector3.new
            base_vector3.new = function(...)
                _G._vector3_calls = _G._vector3_calls + 1
                return base_new(...)
            end
        end
    end

    local function copy_point(v)
        if type(v) ~= 'table' then return nil end
        if type(v.x) == 'number' and type(v.y) == 'number' then
            return {x = v.x, y = v.y, z = v.z or 0}
        end
        if #v == 3 and type(v[1]) == 'number' and type(v[2]) == 'number' then
            return {x = v[1], y = v[2], z = v[3] or 0}
        end
        return nil
    end

    local function collect(v, out)
        if type(v) ~= 'table' then return end
        local pt = copy_point(v)
        if pt then out[#out + 1] = pt return end
        if type(v[1]) == 'number' then
            for i = 1, #v - 2, 3 do
                out[#out + 1] = {x = v[i], y = v[i + 1], z = v[i + 2] or 0}
            end
            return
        end
        for i = 1, #v do collect(v[i], out) end
    end

    local function copy_triangles(triangles)
        local out = {}
        collect(triangles, out)
        return out
    end

    local function attach(p)
        p._test_points = copy_triangles(p._triangles)
        p._test_triangle_groups = {}
        p.clear = function(self)
            self._test_points = {}
            self._test_triangle_groups = {}
        end
        p.add_triangles = function(self, ...)
            local args = {...}
            for i = 1, #args do
                local before = #self._test_points
                collect(args[i], self._test_points)
                local group = {}
                for j = before + 1, #self._test_points do
                    group[#group + 1] = self._test_points[j]
                end
                if #group > 0 then
                    self._test_triangle_groups[#self._test_triangle_groups + 1] = group
                end
            end
        end
    end

    local proto = getmetatable(panel_double)
    assert(proto and proto.polygon, 'fixture prototype must expose polygon')
    local base_polygon = proto.polygon
    proto.polygon = function(self, cfg)
        local p = base_polygon(self, cfg)
        attach(p)
        return p
    end

    local function seed(p)
        if type(p) ~= 'table' then return end
        if p._kind == 'polygon' or p._triangles ~= nil then attach(p) end
        for _, child in pairs(p._children or {}) do seed(child) end
    end
    seed(panel_double)

    mvector3 = mvector3 or {}
    local base_set_static = mvector3.set_static
    mvector3.set_static = function(vec, x, y, z)
        if type(y) == 'table' then
            x, y, z = y.x, y.y, y.z
        end
        if type(vec) == 'table' then
            vec.x = x
            vec.y = y
            vec.z = z
        end
        if base_set_static then pcall(base_set_static, vec, x, y, z) end
        return vec
    end
'''


def _presentation_with_vertical_fixture():
    """Reuse _presentation_with_text_align, but install polygon tracing first."""
    original = presentation_module._lua_with_weapons_runtime

    def wrapped():
        lua, weapons_exists, player_exists = original()
        lua.execute(POLYGON_TRACER_FIXTURE)
        return lua, weapons_exists, player_exists

    presentation_module._lua_with_weapons_runtime = wrapped
    try:
        return _presentation_with_text_align()
    finally:
        presentation_module._lua_with_weapons_runtime = original


RUNTIME_SETUP = r'''
    tweak_data.hud_icons = {
        get_icon_data = function(self, id, default_rect)
            if id == 'fixture_grenade' then
                return 'guis/textures/pd2/equip_icons', {128, 0, 32, 32}
            end
            return id, default_rect or {0, 0, 48, 48}
        end,
    }
    DB = {has = function() return true end}
    Idstring = function(value) return value end
    tweak_data.blackmarket.projectiles.pocket.icon = 'fixture_grenade'
    E._icon_cache = nil
    E:refresh(managers.hud)
    E:_present()

    _game_clock:set_time(997)
    managers.player:_native_set_replenish_timer(1017)
    dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
        HUDManager.PLAYER_PANEL, {duration = 20})
    RT:update(managers.hud, 1, 0.06)

    local row = E._rows[4]
    local reveal = row and row._recharge_reveal
    assert(row and reveal, 'vertical recharge reveal panel must exist')
    local row_w, row_h = row._root:w(), row._root:h()
    local icon, label, value = row._icon, row._label, row._value
    local icon_rect = {icon:x(), icon:y(), icon:w(), icon:h()}
    local icon_parent, label_parent, value_parent =
        icon:parent(), label:parent(), value:parent()
'''

HELPERS = r'''
    local function close(a, b, tol)
        return type(a) == 'number' and type(b) == 'number'
            and math.abs(a - b) <= (tol or 0.05)
    end
    local function kids(p)
        local out = {}
        for _, child in pairs(p:children()) do out[#out + 1] = child end
        return out
    end
    local function is_orange(c)
        return c and close(c.r, 1) and close(c.g, 0.63) and close(c.b, 0.12)
    end
    local function bbox(child)
        local minx, miny, maxx, maxy
        local function add(x, y)
            minx = minx and math.min(minx, x) or x
            miny = miny and math.min(miny, y) or y
            maxx = maxx and math.max(maxx, x) or x
            maxy = maxy and math.max(maxy, y) or y
        end
        local pts = child._test_points or {}
        for _, pt in ipairs(pts) do add(child:x() + pt.x, child:y() + pt.y) end
        if child:w() ~= 0 or child:h() ~= 0 or #pts == 0 then
            add(child:x(), child:y())
            add(child:x() + child:w(), child:y() + child:h())
        end
        return minx, miny, maxx, maxy, #pts
    end
    local function visible_orange()
        local n = 0
        for _, child in ipairs(kids(reveal)) do
            if child:visible() and is_orange(child:color()) then
                n = n + 1
            end
        end
        return n
    end
    local function assert_content_untouched(tag)
        assert(icon:parent() == icon_parent and label:parent() == label_parent
            and value:parent() == value_parent, tag .. ': icon/text parent must stay')
        assert(icon:visible() and label:visible() == false and value:visible(),
            tag .. ': icon/value must stay visible and label must stay hidden')
        assert(icon:layer() == 2 and label:layer() == 2 and value:layer() == 2,
            tag .. ': icon/text must stay on layer 2')
        assert(close(icon:x(), icon_rect[1]) and close(icon:y(), icon_rect[2])
            and close(icon:w(), icon_rect[3]) and close(icon:h(), icon_rect[4]),
            tag .. ': icon geometry must be unaffected')
    end
    local function check_zero(tag)
        assert(close(reveal:x(), 0) and close(reveal:y(), row_h)
            and close(reveal:w(), row_w) and close(reveal:h(), 0),
            tag .. ': zero progress reveal must sit at the bottom with h=0')
        assert(reveal:visible(), tag .. ': reveal must be visible')
        assert(#kids(reveal) == 3, tag .. ': three fixed silhouette children must exist')
        assert(visible_orange() == 0, tag .. ': zero progress must show no visible orange child')
        assert_content_untouched(tag)
    end
    local function check_fill(p, tag, expected_text)
        assert(close(reveal:x(), 0) and close(reveal:y(), row_h * (1 - p))
            and close(reveal:w(), row_w) and close(reveal:h(), row_h * p),
            tag .. ': reveal must fill bottom-up at x=0,y=rowH*(1-p),w=rowW,h=rowH*p')
        assert(reveal:visible(), tag .. ': reveal must be visible')
        assert(value:text() == expected_text, tag .. ': value text must track the timer')
        local fill_h = row_h * p
        local shapes = row:_cell_shapes(row._icon_descriptor)
        local full_cut_w = shapes and shapes.cut and shapes.cut[3] or nil
        local children = kids(reveal)
        assert(#children == 3, tag .. ': three silhouette children are required')
        local cut_found = false
        for _, child in ipairs(children) do
            local minx, miny, maxx, maxy, npoints = bbox(child)
            assert(minx and maxx and miny and maxy, tag .. ': child bbox required')
            assert(minx >= -0.05 and maxx <= row_w + 0.05,
                tag .. ': child rect/triangle x must stay inside the row')
            assert(miny >= -0.05 and maxy <= fill_h + 0.05,
                tag .. ': child rect/triangle y must stay inside local 0..fillH')
            assert(is_orange(child:color()),
                tag .. ': reveal children must use KILLFEED_SCORE_COLOR orange')
            assert(child:visible(), tag .. ': reveal children must be visible')
            for _, pt in ipairs(child._test_points or {}) do
                assert(pt.x >= -0.05 and pt.x <= row_w + 0.05,
                    tag .. ': actual triangle x must stay inside the row')
                assert(pt.y >= -0.05 and pt.y <= fill_h + 0.05,
                    tag .. ': actual triangle y must stay inside local 0..fillH')
            end
            if child:name() == 'reveal_cut' then
                cut_found = true
                assert(npoints > 0, tag .. ': right cut must expose actual triangle payload')
                local cut_w = maxx - minx
                assert(full_cut_w, tag .. ': right cut shape width is required')
                assert(close(cut_w, full_cut_w * p, 0.1),
                    tag .. ': right cut bbox width must be fullCutW*p, not fullCutW')
                assert(cut_w <= full_cut_w + 0.05,
                    tag .. ': right cut must not keep its full width')
            end
        end
        assert(cut_found, tag .. ': right cut child must be owned by the reveal')
        assert_content_untouched(tag)
        return children
    end
'''


class EquipmentRechargeVerticalFillTests(unittest.TestCase):
    def test_reveal_fills_bottom_up_at_015_and_04_without_panel_clip(self):
        lua = _presentation_with_vertical_fixture()
        lua.execute(RUNTIME_SETUP + HELPERS + r'''
            check_zero('progress 0')
            local reveal_at_zero = reveal
            local children_at_zero = kids(reveal)

            _game_clock:set_time(1000)
            RT:update(managers.hud, 1, 0.06)
            local children_015 = check_fill(0.15, 'progress 0.15', '17s')
            assert(row._recharge_reveal == reveal_at_zero,
                'reveal must be retained from zero progress')
            for i, child in ipairs(children_at_zero) do
                assert(children_015[i] == child,
                    'silhouette children must be retained from zero progress')
            end
            local calls_at_015 = _G._vector3_calls
            assert(calls_at_015 > 0, 'Vector3 wrapper must observe creation')

            _game_clock:set_time(1005)
            RT:update(managers.hud, 1.06, 0.06)
            local children_04 = check_fill(0.4, 'progress 0.4', '12s')
            assert(row._recharge_reveal == reveal_at_zero,
                'reveal must be retained while progress advances')
            for i, child in ipairs(children_015) do
                assert(children_04[i] == child,
                    'silhouette children must be retained while progress advances')
            end
            assert(_G._vector3_calls == calls_at_015,
                'progress must not allocate new Vector3/polygon payload')
        ''')

    def test_zero_progress_hides_orange_and_full_progress_shows_full_shape(self):
        lua = _presentation_with_vertical_fixture()
        lua.execute(RUNTIME_SETUP + HELPERS + r'''
            row:render('RECHARGE', '20s', 0, true, row._icon_descriptor)
            check_zero('direct progress 0')

            row:render('RECHARGE', '0s', 1, true, row._icon_descriptor)
            local children = check_fill(1, 'direct progress 1', '0s')
            assert(#children == 3, 'full progress must keep three silhouettes')
            assert(visible_orange() == 3,
                'full progress must show every orange silhouette child')
        ''')

    def test_missing_static_setter_fails_closed_then_recovers_same_reveal(self):
        """Missing mvector3.set_static must fail verify/hide, then recover in place.

        The real runtime row is brought to positive progress 0.15. Removing only
        mvector3.set_static makes the production helper return false, but the
        current reveal path ignores that result and keeps the owned root visible,
        so the negative assertions are RED. Restoring the same API and running an
        ordinary RT:update must recertify the same row/reveal identities.
        """
        lua = _presentation_with_vertical_fixture()
        lua.execute(RUNTIME_SETUP + HELPERS + r'''
            _game_clock:set_time(1000)
            RT:update(managers.hud, 1, 0.06)
            local positive_children = check_fill(0.15, 'positive 0.15', '17s')
            local owner_row = row
            local owner_reveal = reveal
            local owner_children = kids(reveal)
            positive_verify = E:verify() == true
            positive_visible = E._root:visible() == true
            positive_count = #positive_children

            local saved_set_static = mvector3.set_static
            mvector3.set_static = nil

            _game_clock:set_time(1005)
            E:_animate_recharge()

            missing_verify_failed = E:verify() == false
            missing_hidden = E._root:visible() == false
            missing_same_row = E._rows[4] == owner_row
            missing_same_reveal = row._recharge_reveal == owner_reveal
            missing_same_children = true
            local missing_children = kids(reveal)
            if #missing_children ~= #owner_children then
                missing_same_children = false
            end
            for i, child in ipairs(owner_children) do
                if missing_children[i] ~= child then
                    missing_same_children = false
                end
            end

            mvector3.set_static = saved_set_static
            _game_clock:set_time(1010)
            RT:update(managers.hud, 1.12, 0.06)

            recovered_verify = E:verify() == true
            recovered_visible = E._root:visible() == true
            recovered_same_row = E._rows[4] == owner_row
            recovered_same_reveal = row._recharge_reveal == owner_reveal
            recovered_same_children = true
            local recovered_children = kids(reveal)
            if #recovered_children ~= #owner_children then
                recovered_same_children = false
            end
            for i, child in ipairs(owner_children) do
                if recovered_children[i] ~= child then
                    recovered_same_children = false
                end
            end
        ''')
        g = lua.globals()
        self.assertEqual(int(g.positive_count), 3,
                         "positive 0.15 must expose three silhouette children")
        self.assertIs(g.positive_verify, True,
                      "positive 0.15 row must certify before the setter is removed")
        self.assertIs(g.positive_visible, True,
                      "positive 0.15 owned root must be visible")
        self.assertIs(g.missing_verify_failed, True,
                      "RED: missing mvector3.set_static must fail owned verification")
        self.assertIs(g.missing_hidden, True,
                      "RED: a failed recharge write must hide the owned root")
        self.assertIs(g.missing_same_row, True,
                      "failure must retain the same equipment row")
        self.assertIs(g.missing_same_reveal, True,
                      "failure must retain the same reveal panel")
        self.assertIs(g.missing_same_children, True,
                      "failure must retain the same reveal children")
        self.assertIs(g.recovered_verify, True,
                      "restoring mvector3.set_static must recertify on ordinary update")
        self.assertIs(g.recovered_visible, True,
                      "restored ordinary update must show the owned root again")
        self.assertIs(g.recovered_same_row, True,
                      "recovery must reuse the same equipment row")
        self.assertIs(g.recovered_same_reveal, True,
                      "recovery must reuse the same reveal panel")
        self.assertIs(g.recovered_same_children, True,
                      "recovery must reuse the same reveal children")


if __name__ == '__main__':
    unittest.main()

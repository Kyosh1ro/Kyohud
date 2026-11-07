"""Rounded backdrop radius 6e and heart/count containment (RED tracer).

Approved new commonbg contract:
- Rounded rectangle radius 6e replaces 34-degree left bevel
- RT._local_bg_body rect: x=6e, w=bgw-12e, h=full
- RT._local_bg_cut polygon: shape 0,0,full_bgw,bgh (two rounded side caps mesh, not oblique)
- Mesh _triangles: all vertices finite inside bg, no vertices at four outer corners,
  contains rounded corner boundary points
- Sides+body disjoint interiors: every triangle has all x<=6e or all x>=w-6e
- Exact point count not contract
- Heart x=24e, size=16e, count x=42e, w=32e, gauge unchanged x=80e, real w=300e
- Heart and number world inside background, gap 2e, same vertical centerline
- P:verify() and RT:_verify_local_backdrop()

RED until implementation updated in runtime.lua and player.lua.
"""
import unittest
from test_hud_revised_e_composition import _crew_lua, SETUP, mounted


class RoundedBackdropGeometryTests(unittest.TestCase):

    def test_rounded_backdrop_body_cut_mesh_and_heart_count_containment(self):
        for width, height in ((1920, 1080), (1680, 1050), (1280, 720)):
            for scale in (.95, 1, 1.05):
                with self.subTest(width=width, height=height, scale=scale):
                    lua = mounted()
                    lua.globals().pw = width
                    lua.globals().ph = height
                    lua.globals().requested_scale = scale
                    lua.execute(r'''
                        RT._parent_panel:set_shape(0, 0, pw, ph)
                        kyohud.settings.hud_scale = requested_scale
                        RT:refresh_settings(managers.hud)
                        RT:update(managers.hud, 2, .06)
                        local e = math.min(pw / 1920, ph / 1080) * requested_scale
                        local ge = (360 / 440) * e
                        local bg = RT._local_bg_panel
                        local body = RT._local_bg_body
                        local cut = RT._local_bg_cut
                        assert(bg ~= nil, 'RED: shared backdrop exists')
                        local bgw = bg:w()
                        local bgh = bg:h()
                        assert(math.abs(body:x() - 6 * e) < .05, 'RED: body x6e')
                        assert(math.abs(body:w() - (bgw - 12 * e)) < .05, 'RED: body w=bgw-12e')
                        assert(math.abs(body:h() - bgh) < .05, 'RED: body h=full')
                        assert(math.abs(cut:x() - 0) < .05, 'RED: cut x=0')
                        assert(math.abs(cut:y() - 0) < .05, 'RED: cut y=0')
                        assert(math.abs(cut:w() - bgw) < .05, 'RED: cut w=full bgw')
                        assert(math.abs(cut:h() - bgh) < .05, 'RED: cut h=full bgh')
                        local tri = cut._triangles
                        assert(tri ~= nil and #tri > 0, 'RED: cut has triangles')
                        for i, v in ipairs(tri) do
                            assert(type(v.x) == 'number' and v.x == v.x, 'RED: vert ' .. i .. ' x finite')
                            assert(type(v.y) == 'number' and v.y == v.y, 'RED: vert ' .. i .. ' y finite')
                            assert(v.x ~= math.huge and v.x ~= -math.huge, 'RED: vert ' .. i .. ' x not inf')
                            assert(v.y ~= math.huge and v.y ~= -math.huge, 'RED: vert ' .. i .. ' y not inf')
                            assert(v.x >= -0.05 and v.x <= bgw + 0.05, 'RED: vert ' .. i .. ' x inside bg')
                            assert(v.y >= -0.05 and v.y <= bgh + 0.05, 'RED: vert ' .. i .. ' y inside bg')
                        end
                        local corner_eps = 0.5
                        for i, v in ipairs(tri) do
                            local at_tl = (math.abs(v.x) < corner_eps and math.abs(v.y) < corner_eps)
                            local at_tr = (math.abs(v.x - bgw) < corner_eps and math.abs(v.y) < corner_eps)
                            local at_bl = (math.abs(v.x) < corner_eps and math.abs(v.y - bgh) < corner_eps)
                            local at_br = (math.abs(v.x - bgw) < corner_eps and math.abs(v.y - bgh) < corner_eps)
                            assert(not (at_tl or at_tr or at_bl or at_br),
                                'RED: vert ' .. i .. ' at outer corner')
                        end
                        local r = 6 * e
                        local has_left_boundary = false
                        local has_right_boundary = false
                        for i, v in ipairs(tri) do
                            if v.x <= r + 0.5 and v.y > 0.5 and v.y < bgh - 0.5 then
                                has_left_boundary = true
                            end
                            if v.x >= bgw - r - 0.5 and v.y > 0.5 and v.y < bgh - 0.5 then
                                has_right_boundary = true
                            end
                        end
                        assert(has_left_boundary, 'RED: mesh has left rounded boundary points')
                        assert(has_right_boundary, 'RED: mesh has right rounded boundary points')
                        local tri_w = r * 3
                        for tidx = 1, #tri, 3 do
                            local v1 = tri[tidx]
                            local v2 = tri[tidx + 1]
                            local v3 = tri[tidx + 2]
                            assert(v1 and v2 and v3, 'RED: complete triangle at ' .. tidx)
                            local all_left = (v1.x <= r + 0.5) and (v2.x <= r + 0.5) and (v3.x <= r + 0.5)
                            local all_right = (v1.x >= bgw - r - 0.5) and (v2.x >= bgw - r - 0.5) and (v3.x >= bgw - r - 0.5)
                            assert(all_left or all_right,
                                'RED: triangle ' .. tidx .. ' must be all x<=' .. r .. ' or all x>=' .. (bgw - r))
                        end
                        local P = kyohud.hud.player
                        assert(P._downs_icon, 'RED: heart icon exists')
                        local hx = P._downs_icon:x()
                        local hy = P._downs_icon:y()
                        local hw = P._downs_icon:w()
                        local hh = P._downs_icon:h()
                        assert(math.abs(hx - 24 * e) < .05, 'RED: heart x=24e got ' .. hx)
                        assert(math.abs(hw - 16 * e) < .05, 'RED: heart w=16e')
                        assert(math.abs(hh - 16 * e) < .05, 'RED: heart h=16e')
                        local nx = P._downs_text:x()
                        local nw = P._downs_text:w()
                        assert(math.abs(nx - 42 * e) < .05, 'RED: count x=42e got ' .. nx)
                        assert(math.abs(nw - 32 * e) < .05, 'RED: count w=32e')
                        assert(math.abs(P._gauge.root:x() - 80 * e) < .05, 'RED: gauge x=80e unchanged')
                        assert(math.abs(P._gauge.root:w() - 300 * e) < .05, 'RED: gauge w=300e unchanged')
                        local heart_right = hx + hw
                        local count_left = nx
                        local gap = count_left - heart_right
                        assert(math.abs(gap - 2 * e) < .05, 'RED: heart-count gap=2e got ' .. gap)
                        local heart_cy = hy + hh / 2
                        local count_cy = P._downs_text:y() + P._downs_text:h() / 2
                        assert(math.abs(heart_cy - count_cy) < .05, 'RED: same vertical centerline')
                        local function world(p, axis)
                            local s = 0
                            while p do
                                s = s + p[axis](p)
                                p = p:parent()
                            end
                            return s
                        end
                        local bg_world_x = world(bg, "x")
                        local bg_world_y = world(bg, "y")
                        local bg_world_r = bg_world_x + bgw
                        local bg_world_b = bg_world_y + bgh
                        local heart_world_x = world(P._root, "x") + hx
                        local heart_world_y = world(P._root, "y") + hy
                        local heart_world_r = heart_world_x + hw
                        local heart_world_b = heart_world_y + hh
                        assert(heart_world_x >= bg_world_x - 0.05, 'RED: heart world x inside bg left')
                        assert(heart_world_y >= bg_world_y - 0.05, 'RED: heart world y inside bg top')
                        assert(heart_world_r <= bg_world_r + 0.05, 'RED: heart world right inside bg')
                        assert(heart_world_b <= bg_world_b + 0.05, 'RED: heart world bottom inside bg')
                        local count_world_x = world(P._root, "x") + nx
                        local count_world_y = world(P._root, "y") + P._downs_text:y()
                        local count_world_r = count_world_x + nw
                        local count_world_b = count_world_y + P._downs_text:h()
                        assert(count_world_x >= bg_world_x - 0.05, 'RED: count world x inside bg left')
                        assert(count_world_y >= bg_world_y - 0.05, 'RED: count world y inside bg top')
                        assert(count_world_r <= bg_world_r + 0.05, 'RED: count world right inside bg')
                        assert(count_world_b <= bg_world_b + 0.05, 'RED: count world bottom inside bg')
                        assert(P:verify(), 'RED: P verify')
                        assert(RT:_verify_local_backdrop(), 'RED: RT backdrop verify')
                    ''')

    def test_mesh_identity_stable_then_corrupted_shape_rejected_then_repaired(self):
        lua = mounted()
        lua.execute(r'''
            local cut = RT._local_bg_cut
            local tri_before = cut._triangles
            local original_Vector3 = Vector3
            local allocations = 0
            Vector3 = function(...) allocations = allocations + 1; return original_Vector3(...) end
            for i = 1, 5 do
                RT:update(managers.hud, 1 + i * 0.1, 0.06)
                assert(RT:_verify_local_backdrop(), 'RED: backdrop stable at step ' .. i)
            end
            assert(allocations == 0, 'RED: no Vector3 allocations during unchanged updates')
            assert(RT._local_bg_cut == cut, 'RED: same cut object after stable updates')
            assert(RT._local_bg_cut._triangles == tri_before, 'RED: same triangle table')
            Vector3 = original_Vector3
            local body = RT._local_bg_body
            body:set_shape(body:x() + 50, body:y(), body:w(), body:h())
            assert(not RT:_verify_local_backdrop(), 'RED: corrupted body shape rejected')
            RT:update(managers.hud, 2, .06)
            assert(RT:_verify_local_backdrop(), 'RED: repaired by ordinary update')
            assert(RT._local_bg_body == body, 'RED: same body primitive after repair')
            assert(RT._local_bg_cut == cut, 'RED: same cut primitive after repair')
            local cut2 = RT._local_bg_cut
            local sx, sy, sw, sh = cut2:x(), cut2:y(), cut2:w(), cut2:h()
            cut2:set_shape(sx + 99, sy, sw, sh)
            assert(not RT:_verify_local_backdrop(), 'RED: corrupted cut shape rejected')
            RT:update(managers.hud, 3, .06)
            assert(RT:_verify_local_backdrop(), 'RED: cut repaired by ordinary update')
            assert(RT._local_bg_cut == cut2, 'RED: same cut identity after shape repair')
        ''')


    def test_native_construction_bounds_bg_panel_and_cut_polygon(self):
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        assert crew_ok and weapons_ok and equipment_ok
        lua.execute(r'''
            local Panel_mt = getmetatable(panel_double)
            local orig_panel = Panel_mt.__index.panel
            local orig_polygon = Panel_mt.__index.polygon
            captured_bg_panels = {}
            captured_cut_polys = {}
            captured_bg_cfgs = {}
            captured_cut_cfgs = {}
            Panel_mt.__index.panel = function(self, cfg)
                if type(cfg) == "table" and cfg.name == "kyohud_shared_bg_panel" then
                    local snap = {x=cfg.x, y=cfg.y, w=cfg.w, h=cfg.h}
                    captured_bg_cfgs[#captured_bg_cfgs + 1] = snap
                end
                local ch = orig_panel(self, cfg)
                if type(cfg) == "table" and cfg.name == "kyohud_shared_bg_panel" then
                    captured_bg_panels[#captured_bg_panels + 1] = ch
                end
                return ch
            end
            Panel_mt.__index.polygon = function(self, cfg)
                if type(cfg) == "table" and cfg.name == "kyohud_shared_bg_cut" then
                    local snap = {x=cfg.x, y=cfg.y, w=cfg.w, h=cfg.h}
                    captured_cut_cfgs[#captured_cut_cfgs + 1] = snap
                end
                local ch = orig_polygon(self, cfg)
                if type(cfg) == "table" and cfg.name == "kyohud_shared_bg_cut" then
                    captured_cut_polys[#captured_cut_polys + 1] = ch
                end
                return ch
            end
        ''')
        lua.execute(SETUP)
        lua.execute(r'''
            assert(#captured_bg_panels >= 1, 'RED: bg panel factory captured')
            assert(#captured_bg_cfgs >= 1, 'RED: bg panel cfg captured')
            local bg = RT._local_bg_panel
            assert(bg == captured_bg_panels[1], 'RED: captured bg panel is RT bg')
            local bgx = bg:x()
            local bgy = bg:y()
            local bgw = bg:w()
            local bgh = bg:h()
            assert(type(bgx) == 'number' and bgx == bgx and bgx ~= math.huge and bgx ~= -math.huge, 'RED: bg panel x finite')
            assert(type(bgy) == 'number' and bgy == bgy and bgy ~= math.huge and bgy ~= -math.huge, 'RED: bg panel y finite')
            assert(type(bgw) == 'number' and bgw == bgw and bgw ~= math.huge and bgw ~= -math.huge, 'RED: bg panel w finite')
            assert(type(bgh) == 'number' and bgh == bgh and bgh ~= math.huge and bgh ~= -math.huge, 'RED: bg panel h finite')
            assert(bgx >= 0, 'RED: bg panel x non-negative')
            assert(bgy >= 0, 'RED: bg panel y non-negative')
            assert(bgw > 0, 'RED: bg panel w positive')
            assert(bgh > 0, 'RED: bg panel h positive')

            local first_bg_cfg = captured_bg_cfgs[1]
            assert(type(first_bg_cfg.x) == 'number' and first_bg_cfg.x == first_bg_cfg.x, 'RED: first bg_cfg x explicit number')
            assert(type(first_bg_cfg.y) == 'number' and first_bg_cfg.y == first_bg_cfg.y, 'RED: first bg_cfg y explicit number')
            assert(type(first_bg_cfg.w) == 'number' and first_bg_cfg.w == first_bg_cfg.w and first_bg_cfg.w > 0, 'RED: first bg_cfg w explicit number')
            assert(type(first_bg_cfg.h) == 'number' and first_bg_cfg.h == first_bg_cfg.h and first_bg_cfg.h > 0, 'RED: first bg_cfg h explicit number')
            assert(math.abs(first_bg_cfg.x - bgx) < .05, 'RED: first bg_cfg x equals actual bg x')
            assert(math.abs(first_bg_cfg.y - bgy) < .05, 'RED: first bg_cfg y equals actual bg y')
            assert(math.abs(first_bg_cfg.w - bgw) < .05, 'RED: first bg_cfg w equals actual bg w')
            assert(math.abs(first_bg_cfg.h - bgh) < .05, 'RED: first bg_cfg h equals actual bg h')

            assert(#captured_cut_polys >= 1, 'RED: cut polygon factory captured')
            assert(#captured_cut_cfgs >= 1, 'RED: cut polygon cfg captured')
            local cut = RT._local_bg_cut
            assert(cut == captured_cut_polys[1], 'RED: captured cut is RT cut')
            assert(math.abs(cut:x() - 0) < .05, 'RED: cut polygon constructor x=0')
            assert(math.abs(cut:y() - 0) < .05, 'RED: cut polygon constructor y=0')
            assert(math.abs(cut:w() - bgw) < .05, 'RED: cut polygon constructor w=bgw')
            assert(math.abs(cut:h() - bgh) < .05, 'RED: cut polygon constructor h=bgh')

            local first_cut_cfg = captured_cut_cfgs[1]
            assert(type(first_cut_cfg.x) == 'number' and first_cut_cfg.x == first_cut_cfg.x, 'RED: first cut_cfg x explicit number')
            assert(type(first_cut_cfg.y) == 'number' and first_cut_cfg.y == first_cut_cfg.y, 'RED: first cut_cfg y explicit number')
            assert(type(first_cut_cfg.w) == 'number' and first_cut_cfg.w == first_cut_cfg.w and first_cut_cfg.w > 0, 'RED: first cut_cfg w explicit number')
            assert(type(first_cut_cfg.h) == 'number' and first_cut_cfg.h == first_cut_cfg.h and first_cut_cfg.h > 0, 'RED: first cut_cfg h explicit number')
            assert(math.abs(first_cut_cfg.x - 0) < .05, 'RED: first cut_cfg x equals 0')
            assert(math.abs(first_cut_cfg.y - 0) < .05, 'RED: first cut_cfg y equals 0')
            assert(math.abs(first_cut_cfg.w - bgw) < .05, 'RED: first cut_cfg w equals bgw')
            assert(math.abs(first_cut_cfg.h - bgh) < .05, 'RED: first cut_cfg h equals bgh')

            local poly_count_before = #captured_cut_polys
            local cfg_count_before = #captured_cut_cfgs

            RT._parent_panel:set_shape(0, 0, 1680, 1050)
            kyohud.settings.hud_scale = 1.0
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 2, .06)

            assert(#captured_cut_polys > poly_count_before, 'RED: cut polygon recreated after resize')
            assert(#captured_cut_cfgs > cfg_count_before, 'RED: cut polygon cfg recreated after resize')
            local new_cut = captured_cut_polys[#captured_cut_polys]
            local new_bg = RT._local_bg_panel
            local new_bgw = new_bg:w()
            local new_bgh = new_bg:h()
            assert(new_cut ~= cut, 'RED: new cut is different object after resize')
            assert(math.abs(new_cut:x() - 0) < .05, 'RED: new cut polygon constructor x=0')
            assert(math.abs(new_cut:y() - 0) < .05, 'RED: new cut polygon constructor y=0')
            assert(math.abs(new_cut:w() - new_bgw) < .05, 'RED: new cut polygon constructor w matches new bgw')
            assert(math.abs(new_cut:h() - new_bgh) < .05, 'RED: new cut polygon constructor h matches new bgh')

            local last_cut_cfg = captured_cut_cfgs[#captured_cut_cfgs]
            assert(math.abs(last_cut_cfg.x - 0) < .05, 'RED: last cut_cfg x equals 0')
            assert(math.abs(last_cut_cfg.y - 0) < .05, 'RED: last cut_cfg y equals 0')
            assert(math.abs(last_cut_cfg.w - new_bgw) < .05, 'RED: last cut_cfg w equals new bgw')
            assert(math.abs(last_cut_cfg.h - new_bgh) < .05, 'RED: last cut_cfg h equals new bgh')
        ''')

    def test_backdrop_margin_and_content_origin_alignment(self):
        for width, height in ((1920, 1080), (1680, 1050), (1280, 720)):
            for scale in (.95, 1, 1.05):
                with self.subTest(width=width, height=height, scale=scale):
                    lua = mounted()
                    lua.globals().pw = width
                    lua.globals().ph = height
                    lua.globals().requested_scale = scale
                    lua.execute(r'''
                        RT._parent_panel:set_shape(0, 0, pw, ph)
                        kyohud.settings.hud_scale = requested_scale
                        RT:refresh_settings(managers.hud)
                        RT:update(managers.hud, 2, .06)
                        local e = math.min(pw / 1920, ph / 1080) * requested_scale
                        local bg = RT._local_bg_panel
                        local W_root = W._root
                        local P_root = P._root
                        local gauge = P._gauge
                        assert(bg ~= nil, 'RED: shared backdrop exists')
                        assert(W_root ~= nil and P_root ~= nil, 'RED: W and P roots exist')
                        assert(P:verify(), 'RED: P verify')
                        assert(W:verify(), 'RED: W verify')
                        assert(math.abs(bg:x() - W_root:x()) < .05,
                            'RED: bg x == W root x, got bg_x=' .. bg:x() .. ' W_x=' .. W_root:x())
                        assert(math.abs(bg:w() - (W_root:w() + 2 * e)) < .05,
                            'RED: bg w == W root w + 2e, got bg_w=' .. bg:w() .. ' W_w=' .. W_root:w() .. ' 2e=' .. 2 * e)
                        assert(math.abs(gauge.root:w() - 300 * e) < .05, 'RED: gauge w300e')
                        local avbg = gauge._armor_value_bg
                        assert(avbg ~= nil, 'RED: armor value bg exists')
                        local armor_cell_world_right = P_root:x() + gauge.root:x() + avbg:x() + avbg:w()
                        local function world_x(p)
                            local s = 0
                            while p do
                                s = s + p:x()
                                p = p:parent()
                            end
                            return s
                        end
                        local bg_world_right = world_x(bg) + bg:w()
                        local W_world_right = world_x(W_root) + W_root:w()
                        local margin = bg_world_right - W_world_right
                        assert(margin >= 2 * e - .05,
                            'RED: backdrop margin >= 2e, got ' .. margin .. ' expected >= ' .. 2 * e)
                        assert(math.abs(bg_world_right - (W_world_right + 2 * e)) < .05,
                            'RED: bg world right == W world right + 2e, got ' .. bg_world_right .. ' expected ' .. (W_world_right + 2 * e))
                    ''')


if __name__ == '__main__':
    unittest.main()

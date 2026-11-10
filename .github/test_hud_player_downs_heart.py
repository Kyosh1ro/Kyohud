"""Slice C -- player downs heart icon with chico specialization texture.

Tests the downs icon (heart) using guis/dlcs/chico/textures/pd2/specialization/icons_atlas
with crop {64,0,64,64} from hudlist_catalog line 446 (passive_health_regen perk_icon(1,0,chico)).

Owned P._downs_icon Bitmap; current _downs_bg retained but HIDDEN, number retained native fitting.
Heart geometry: x=24*rootw, y=22*rootw+16*ge-8*rootw, size=16*rootw where rootw=player_root_w/380, ge=(360/440)*rootw.
Downs number at x=42*rootw, w=32*rootw, same font size 24*ge center preserved.

Both resource APIs Bitmap:texture_name/set_image actual. Native getter texture_rect unavailable,
use fixture observations only.
"""
import unittest
from test_hud_final_integration import _crew_lua


def mounted_with_heart_texture():
    """Build fixture with DB texture available BEFORE SETUP mounting."""
    lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
    if not (crew_ok and weapons_ok and equipment_ok):
        return lua, False

    # Enable heart texture in DB before mounting
    lua.execute(r'''
        -- Set up DB with actual DB.has and Idstring
        DB = {
            _textures = {
                ["guis/dlcs/chico/textures/pd2/specialization/icons_atlas"] = true
            },
            has = function(self, kind, id)
                return self._textures[tostring(id)] == true
            end
        }
        Idstring = function(s) return s end

        -- Helper to set DB has ID string
        function setDBhasIdString(id, available)
            DB._textures[id] = available
        end
    ''')
    return lua, True


SETUP = r'''
kyohud.settings.enable_hud_foundation=true
kyohud.settings.enable_player=true
kyohud.settings.enable_weapons=false
kyohud.settings.enable_equipment=false
kyohud.settings.enable_crew=false
kyohud.settings.player_value_mode=1
kyohud.settings.hud_scale=1.0

managers.player.current_state=function() return 'standard' end
RT=kyohud.hud.runtime
RT:refresh_settings(managers.hud)
RT:update(managers.hud,1,.06)
'''


class DownsHeartIconTests(unittest.TestCase):
    def test_heart_bitmap_resource_and_crop_constructor_retained(self):
        """Heart icon created with correct texture and crop from fixture _texture_rect."""
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")
        lua.execute(SETUP)
        lua.execute(r'''
            local P=kyohud.hud.player
            assert(P._downs_icon, 'RED: P._downs_icon Bitmap must exist')
            
            -- Verify texture_name() returns the chico specialization path
            local tex = P._downs_icon:texture_name()
            assert(tex == "guis/dlcs/chico/textures/pd2/specialization/icons_atlas",
                'RED: heart texture must be chico specialization icons_atlas')
            
            -- Verify _texture_rect is {64,0,64,64} from fixture observation
            local rect = P._downs_icon._texture_rect
            assert(rect ~= nil, 'RED: _texture_rect must be set')
            assert(rect[1] == 64 and rect[2] == 0 and rect[3] == 64 and rect[4] == 64,
                'RED: heart crop must be {64,0,64,64}')
            
            -- Verify set_image was called with correct args
            assert(P._downs_icon._texture == "guis/dlcs/chico/textures/pd2/specialization/icons_atlas")
        ''')

    def test_heart_count_visible_bg_not_visible(self):
        """Heart icon and count visible, _downs_bg retained but HIDDEN."""
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")
        lua.execute(SETUP)
        lua.execute(r'''
            local P=kyohud.hud.player
            
            -- Render known value 3
            P:render({downs=3, health={valid=false}, armor={valid=false}}, 10)
            
            -- Heart icon must be visible
            assert(P._downs_icon:visible(), 'RED: heart icon must be visible')
            
            -- Count text must be visible
            assert(P._downs_text:visible(), 'RED: downs count must be visible')
            assert(P._downs_text:text() == '3', 'RED: count must be 3')
            
            -- _downs_bg must be retained but HIDDEN
            assert(P._downs_bg ~= nil, 'RED: _downs_bg must be retained')
            assert(not P._downs_bg:visible(), 'RED: _downs_bg must be HIDDEN')
        ''')

    def test_heart_geometry_scalar_snapshots(self):
        """Heart geometry x=24*rootw, y=22*rootw+16*ge-8*rootw, size=16*rootw preserves gauge font colors."""
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")
        lua.execute(SETUP)
        lua.execute(r'''
            local P=kyohud.hud.player
            local root_w = P._root:w()
            local rootw = root_w / 380
            local ge = (360/440) * rootw
            
            -- Expected heart geometry
            local exp_x = 24 * rootw
            local exp_y = 192 * rootw + 16 * ge - 8 * rootw
            local exp_size = 16 * rootw
            
            -- Verify heart icon geometry
            local hx = P._downs_icon:x()
            local hy = P._downs_icon:y()
            local hw = P._downs_icon:w()
            local hh = P._downs_icon:h()
            
            assert(math.abs(hx - exp_x) < 0.05, 'RED: heart x must be 24*rootw')
            assert(math.abs(hy - exp_y) < 0.05, 'RED: heart y must be 22*rootw+16*ge-8*rootw')
            assert(math.abs(hw - exp_size) < 0.05, 'RED: heart w must be 16*rootw')
            assert(math.abs(hh - exp_size) < 0.05, 'RED: heart h must be 16*rootw')
            
            -- Verify downs number geometry: x=42*rootw, w=32*rootw
            local nx = P._downs_text:x()
            local nw = P._downs_text:w()
            assert(math.abs(nx - 42*rootw) < 0.05, 'RED: number x must be 42*rootw')
            assert(math.abs(nw - 32*rootw) < 0.05, 'RED: number w must be 32*rootw')
            
            -- Verify font size 24*ge preserved
            local fs = P._downs_text:font_size()
            assert(math.abs(fs - 24*ge) < 0.01, 'RED: font size must be 24*ge')
        ''')

    def test_known_values_zero_three_unknown_dash(self):
        """Known 0/3 unknown-- via P:render scalar snapshots preserve gauge font colors."""
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")
        lua.execute(SETUP)
        lua.execute(r'''
            local P=kyohud.hud.player
            local gauge_fs = P._gauge.health_text:font_size()
            
            -- Test 0
            P:render({downs=0, health={valid=false}, armor={valid=false}}, 10)
            assert(P._downs_text:text() == '0', 'RED: 0 downs must show "0"')
            assert(P._gauge.health_text:font_size() == gauge_fs, 'RED: gauge font color preserved')
            assert(P:verify(), 'RED: verify must pass for 0')
            
            -- Test 3
            P:render({downs=3, health={valid=false}, armor={valid=false}}, 10)
            assert(P._downs_text:text() == '3', 'RED: 3 downs must show "3"')
            assert(P:verify(), 'RED: verify must pass for 3')
            
            -- Test unknown (no downs field)
            P:render({health={valid=false}, armor={valid=false}}, 10)
            assert(P._downs_text:text() == '--', 'RED: unknown must show "--"')
            assert(P:verify(), 'RED: verify must pass for unknown')
        ''')

    def test_heart_geometry_corruption_verify_false_recover(self):
        """Second actual RT: update after heart geometry corruption verify false and retained primitive recover."""
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")
        lua.execute(SETUP)
        lua.execute(r'''
            local P=kyohud.hud.player
            local icon = P._downs_icon
            
            -- Corrupt heart geometry
            icon:set_shape(-100, -100, 1, 1)
            
            -- Verify must fail
            assert(not P:verify(), 'RED: verify must fail after heart geometry corruption')
            
            -- Update should recover
            RT:update(managers.hud, 2.0, .06)
            
            -- Verify must pass again with retained primitive
            assert(P:verify(), 'RED: verify must pass after recovery')
            assert(P._downs_icon == icon, 'RED: must retain same heart primitive')
        ''')

    def test_missing_texture_gracefully_retain_count(self):
        """Missing texture gracefully retain count (fixture environment DB false then fresh mount)."""
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")

        # Disable texture in DB
        lua.execute(r'''
            setDBhasIdString("guis/dlcs/chico/textures/pd2/specialization/icons_atlas", false)
        ''')

        lua.execute(SETUP)
        lua.execute(r'''
            local P=kyohud.hud.player
            
            -- Render with count 3
            P:render({downs=3, health={valid=false}, armor={valid=false}}, 10)
            
            -- Heart icon must not be visible (texture missing)
            assert(not P._downs_icon or not P._downs_icon:visible(),
                'RED: heart icon must not be visible when texture missing')
            
            -- Count must be retained and visible even if texture missing
            assert(P._downs_text:visible(), 'RED: downs count must be visible')
            assert(P._downs_text:text() == '3', 'RED: count must be retained')
            
            -- Verify must pass
            assert(P:verify(), 'RED: verify must pass with missing texture')
        ''')

    def test_lifecycle_off_on(self):
        """Lifecycle off/on preserves heart icon and count."""
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")
        lua.execute(SETUP)
        lua.execute(r'''
            local P=kyohud.hud.player
            
            -- Render count 3
            P:render({downs=3, health={valid=false}, armor={valid=false}}, 10)
            local icon_before = P._downs_icon
            assert(P:verify(), 'RED: verify before off')
            
            -- Turn off
            kyohud.settings.enable_player=false
            RT:refresh_settings(managers.hud)
            assert(not P._root, 'RED: root must be nil after off')
            
            -- Turn on
            kyohud.settings.enable_player=true
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 2.0, .06)
            
            -- Must remount with heart icon
            assert(P._root, 'RED: root must exist after on')
            assert(P._downs_icon, 'RED: heart icon must exist after on')
            assert(P._downs_text, 'RED: downs text must exist after on')
            assert(P._downs_text:text() ~= nil, 'RED: downs text must be present')
            assert(P:verify(), 'RED: verify after on')
        ''')

    def test_fit_downs_text_coverage_standalone(self):
        """Keep _fit_downs_text coverage standalone not modify old."""
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")
        lua.execute(SETUP)
        lua.execute(r'''
            local P=kyohud.hud.player
            
            -- _fit_downs_text is called by render, verify it works
            P:render({downs=5, health={valid=false}, armor={valid=false}}, 10)
            
            -- Measure must be valid
            assert(P._downs_measure_valid == true, 'RED: _fit_downs_text must set measure valid')
            
            -- Verify must pass
            assert(P:verify(), 'RED: verify must pass after _fit_downs_text')
        ''')


    def test_callable_table_idstring_engine_real_type(self):
        """Engine Idstring is a callable table not a function; production check_texture_available rejects table type (RED)."""
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")
        lua.execute(r'''
            Idstring = setmetatable({}, {__call = function(_, s) return s end})
        ''')
        lua.execute(SETUP)
        lua.execute(r'''
            local P = kyohud.hud.player
            assert(P._downs_icon, 'RED: P._downs_icon must exist')
            assert(P._downs_icon:visible(), 'RED: heart icon must be visible')
            assert(P:verify(), 'RED: verify must pass')
        ''')

    def test_userdata_write_crash_regression(self):
        """REGRESSION: player.lua:169 writes prim._texture on userdata causes engine crash.

        Wraps shared Panel metatable BEFORE SETUP to intercept bitmap factory.
        For cfg.name == 'kyohud_player_downs_icon' returns proxy with backing bitmap.
        Proxy __newindex increments attempts and errors for ANY write (simulating userdata).
        SETUP must not throw; icon retained after RT update; zero arbitrary write attempts.
        """
        lua, ok = mounted_with_heart_texture()
        self.assertTrue(ok, "crew+weapons+equipment must load")

        # BEFORE SETUP: wrap shared Panel metatable to intercept bitmap factory
        lua.execute(r'''
            local Panel_mt = getmetatable(panel_double)
            local orig_bitmap = Panel_mt.__index.bitmap

            -- Captured cfg for assertions
            _captured_cfg = nil
            _write_attempts = 0
            _write_errors = 0

            Panel_mt.__index.bitmap = function(self, cfg)
                local backing = orig_bitmap(self, cfg)
                if cfg.name == "kyohud_player_downs_icon" then
                    _captured_cfg = cfg
                    local proxy = newproxy(true)
                    local mt = getmetatable(proxy)
                    mt.__index = function(_, k)
                        local value = backing[k]
                        if type(value) == "function" then
                            return function(_, ...)
                                return value(backing, ...)
                            end
                        end
                        return value
                    end
                    mt.__newindex = function(_, k, v)
                        _write_attempts = _write_attempts + 1
                        _write_errors = _write_errors + 1
                        error("ENGINE CRASH: cannot write to userdata field '" .. tostring(k) .. "'")
                    end
                    self._children[cfg.name] = proxy
                    return proxy
                end
                return backing
            end
        ''')

        # Execute SETUP - must not throw despite proxy intercepting writes
        lua.execute(SETUP)

        # Verify icon exists and is userdata-like (proxy), visible, verify passes
        lua.execute(r'''
            local P = kyohud.hud.player
            local Picon = P._downs_icon
            assert(Picon, 'RED: P._downs_icon must exist')
            assert(type(Picon) == 'userdata', 'RED: Picon must be userdata')
            assert(Picon:visible(), 'RED: heart icon must be visible')
            assert(P:verify(), 'RED: verify must pass')

            -- Count must be visible
            assert(P._downs_text:visible(), 'RED: downs count must be visible')

            -- RT update 2 retains icon and verify passes
            RT:update(managers.hud, 2.0, .06)
            assert(P._downs_icon == Picon, 'RED: must retain same icon after RT update')
            assert(P:verify(), 'RED: verify must pass after RT update')

            -- Assert zero arbitrary write attempts (proxy __newindex never called by production)
            assert(_write_attempts == 0, 'RED: production must not write to proxy (got ' .. _write_attempts .. ' attempts)')

            -- Assert same constructor resource via texture_name and captured cfg
            assert(Picon:texture_name() == "guis/dlcs/chico/textures/pd2/specialization/icons_atlas",
                'RED: texture_name must match constructor')
            assert(_captured_cfg ~= nil, 'RED: cfg must be captured')
            assert(_captured_cfg.texture_rect[1] == 64 and _captured_cfg.texture_rect[2] == 0
                and _captured_cfg.texture_rect[3] == 64 and _captured_cfg.texture_rect[4] == 64,
                'RED: captured cfg crop must be {64,0,64,64}')
        ''')


if __name__ == '__main__':
    unittest.main()

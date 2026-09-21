"""Tests for ky_killfeed_render.lua extraction.

Validates:
- Module loads correctly in production order
- Core does NOT contain extracted functions
- Module contains extracted functions
- KH:render_killfeed is exposed and callable
- mod.txt declares the module exactly once in the correct context and order
- Extraction is idempotent
- Wrong-context guard (module must NOT install interface outside hudmanagerpd2)
- Killfeed measurement and rendering behavior
- Regression: alpha parameter vs settings.opacity divergence
- Regression: chevron cache keyed by size_key (w:h) then dir_key, not by style.count
- Regression: oldest kill on the left, newest on the right (via positions)
"""
from pathlib import Path
import json
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


# ─────────────────────────────────────────────────────────────────────
# Production-order harness
# ─────────────────────────────────────────────────────────────────────

def _make_lua():
    """Return a LuaRuntime pre-loaded with PD2 stubs."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
    lua.execute('''
        Hooks = {callbacks = {}}
        function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
        function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
        function Hooks:Add(...) end
        HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
        function Vector3(...) return {...} end
        function log(...) end
        function alive(x) return x ~= nil end
        function Idstring(s) return s end
        DB = { has = function() return false end }
        local function color(r, g, b)
            local c = {r = r or 0, g = g or 0, b = b or 0}
            function c:with_alpha(a) return self end
            return c
        end
        Color = setmetatable({white = color(1,1,1), black = color(0,0,0)}, {
            __call = function(_, ...) return color(...) end
        })
        tweak_data.menu = {pd2_small_font = "test_font", pd2_large_font = "test_font_large", pd2_medium_font = "test_font_medium"}
        game_t = 100
        TimerManager = {game = function() return {time = function() return game_t end} end}
        PlayerBase = {PLAYER_INFO_HUD_PD2 = "pd2", PLAYER_INFO_HUD_FULLSCREEN_PD2 = "fs"}
    ''')
    return lua


def _load_production_chunks(lua):
    """Load chunks in the production order declared in mod.txt for hudmanagerpd2."""
    for name in [
        "hudlist.lua",
        "core.lua",
        "ky_buff_render.lua",
        "ky_combat_medals.lua",
        "ky_heist_score.lua",
        "ky_hud_banners.lua",
        "ky_killfeed_render.lua",
    ]:
        lua.execute((ROOT / "lua" / name).read_text(encoding="utf-8-sig"))


def _make_full_panel(lua):
    """Install a panel mock that records every draw primitive into kyohud._panel_*."""
    lua.execute('''
        local panel = {
            gradients = {}, rects = {}, texts = {}, bitmaps = {}, polygons = {},
            _children = {},
        }
        function panel:w() return 800 end
        function panel:h() return 600 end
        function panel:child() return nil end
        function panel:panel(params) self._children[#self._children+1] = params; return self end
        function panel:gradient(params)
            self.gradients[#self.gradients + 1] = params
            return params
        end
        function panel:rect(params)
            self.rects[#self.rects + 1] = params
            return params
        end
        function panel:text(params)
            self.texts[#self.texts + 1] = params
            return {
                set_text = function() end,
                text_rect = function() return 0, 0, 15, 10 end,
            }
        end
        function panel:bitmap(params)
            self.bitmaps[#self.bitmaps + 1] = params
            return {set_color = function() end, set_alpha = function() end, set_rotation = function() end}
        end
        function panel:polygon(params)
            self.polygons[#self.polygons + 1] = params
            return params
        end
        function panel:remove() end
        function panel:clear()
            self.gradients = {}; self.rects = {}; self.texts = {}
            self.bitmaps = {}; self.polygons = {}
        end
        kyohud._panel = panel
        kyohud._panel_record = panel
    ''')


class KillfeedRenderExtractionTests(unittest.TestCase):
    def setUp(self):
        self.core_source = (ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig")
        self.module_source = (ROOT / "lua" / "ky_killfeed_render.lua").read_text(
            encoding="utf-8-sig"
        )
        self.mod_source = (ROOT / "mod.txt").read_text(encoding="utf-8-sig")

    # ─────────────────────────────────────────────────────────────
    # Static (source) checks
    # ─────────────────────────────────────────────────────────────

    def test_module_does_not_contain_core_state(self):
        self.assertNotIn("KH._kills = {}", self.module_source)
        self.assertNotIn("KH._buffs = {}", self.module_source)
        self.assertNotIn("KH._heist_score_total = 0", self.module_source)

    def test_module_contains_extracted_functions(self):
        self.assertIn("function KH:render_killfeed(panel, w, h, size, alpha, radius)", self.module_source)
        self.assertIn(
            "local function measure_killfeed_entries(panel, kills, first_kill, count, font, font_size)",
            self.module_source,
        )
        self.assertIn("local function combo_color(count)", self.module_source)
        self.assertIn("local function special_enemy_color(kind)", self.module_source)
        self.assertIn("local function multikill_chevron_fill(count)", self.module_source)
        self.assertIn(
            "local function draw_multikill_chevrons(panel, x, y, direction, color, alpha, layer, filled)",
            self.module_source,
        )
        self.assertIn(
            "local function draw_chevrons(panel, x, y, direction, color, alpha, layer, style)",
            self.module_source,
        )
        self.assertIn(
            "local function draw_killfeed_card_frame(panel, x, y, w, h, color, alpha, layer)",
            self.module_source,
        )
        self.assertIn(
            "local function draw_glowing_text(panel, label, font, font_size, color, x, y, w, h, alpha, layer)",
            self.module_source,
        )

    def test_core_does_not_contain_extracted_functions(self):
        self.assertNotIn("function KH:render_killfeed(", self.core_source)
        self.assertNotIn("local function combo_color(count)", self.core_source)
        self.assertNotIn("local function special_enemy_color(kind)", self.core_source)
        self.assertNotIn("local function multikill_chevron_fill(count)", self.core_source)
        self.assertNotIn("local function draw_multikill_chevrons(", self.core_source)
        self.assertNotIn("local function draw_chevrons(", self.core_source)
        self.assertNotIn("local function draw_killfeed_card_frame(", self.core_source)
        self.assertNotIn("local function draw_glowing_text(", self.core_source)

    def test_core_does_not_duplicate_render_constants(self):
        # KILL_SCROLL_TIME and KILLFEED_FRAME_CLEARANCE must live only in the module.
        self.assertNotIn("KILL_SCROLL_TIME", self.core_source)
        self.assertNotIn("KILLFEED_FRAME_CLEARANCE", self.core_source)

    def test_module_uses_alpha_not_s_opacity_for_inner_alphas(self):
        # The render_killfeed signature takes `alpha` explicitly; inner alphas
        # (score_alpha, banner_alpha, medal_alpha, item_alpha) must derive from
        # that parameter, not from self.settings.opacity.
        self.assertNotIn("s.opacity * score_intro", self.module_source)
        self.assertNotIn("s.opacity * fade_out", self.module_source)
        self.assertIn("alpha * score_intro", self.module_source)
        self.assertIn("alpha * fade_out", self.module_source)
        self.assertIn("alpha * (0.25 + 0.75 * life)", self.module_source)

    def test_module_uses_parent_chevron_cache_semantics(self):
        # Parent used `local count = SPECIAL_CHEVRON_SLOTS`, `size_key = w..":"..h`,
        # bucket by size_key, triangles by dir_key (1 or -1). Module must match.
        self.assertIn('local count = C.SPECIAL_CHEVRON_SLOTS', self.module_source)
        self.assertIn('local dir_key = direction > 0 and 1 or -1', self.module_source)
        self.assertIn('local size_key = arrow_w .. ":" .. arrow_h', self.module_source)
        # The old module variant indexed by arrow_w alone and honored style.count;
        # both must be gone.
        self.assertNotIn('RENDER_CACHES.chevrons[arrow_w]', self.module_source)
        # style.count must not influence the iteration count.
        self.assertNotIn('style.count', self.module_source)

    def test_core_delegates_to_module(self):
        self.assertIn(
            "KH:render_killfeed(self._panel, w, h, size, alpha, radius)",
            self.core_source,
        )
        self.assertIn(
            "-- Killfeed rendering delegated to ky_killfeed_render.lua",
            self.core_source,
        )

    def test_core_exports_required_constants(self):
        for token in [
            "KH.HUD_ACCENT_COLOR",
            "KH.KILLFEED_SCORE_COLOR",
            "KH.KILLFEED_SCORE_PENALTY_COLOR",
            "KH.KILL_COMBO_WINDOW",
            "KH.SPECIAL_KILL_BANNER_DURATION",
            "KH.RENDER_CACHES",
            "KH.now",
            "KH.clamp",
            "KH.approximate_text_width",
            "KH.format_kill_score",
            "KH.killfeed_size",
            "KH.combo_label",
            "KH.SPECIAL_ENEMY_DEFINITIONS",
        ]:
            self.assertIn(token, self.core_source, f"core.lua must export {token}")

    def test_mod_txt_declares_module_exactly_once(self):
        mod = json.loads(self.mod_source)
        matches = [
            h for h in mod["hooks"]
            if h.get("script_path") == "lua/ky_killfeed_render.lua"
        ]
        self.assertEqual(len(matches), 1, "module must appear exactly once in mod.txt hooks")
        self.assertEqual(
            matches[0]["hook_id"],
            "lib/managers/hudmanagerpd2",
            "module must be declared under the hudmanagerpd2 context",
        )

    def test_mod_txt_loads_module_after_dependencies(self):
        mod = json.loads(self.mod_source)
        hud_context_scripts = [
            h["script_path"] for h in mod["hooks"]
            if h["hook_id"] == "lib/managers/hudmanagerpd2"
        ]
        for required in [
            "lua/core.lua",
            "lua/ky_combat_medals.lua",
            "lua/ky_heist_score.lua",
            "lua/ky_hud_banners.lua",
        ]:
            self.assertIn(required, hud_context_scripts, f"{required} must be declared in hudmanagerpd2 context")
        module_idx = hud_context_scripts.index("lua/ky_killfeed_render.lua")
        for dep in [
            "lua/core.lua",
            "lua/ky_combat_medals.lua",
            "lua/ky_heist_score.lua",
            "lua/ky_hud_banners.lua",
        ]:
            self.assertLess(
                hud_context_scripts.index(dep),
                module_idx,
                f"ky_killfeed_render.lua must load after {dep} within hudmanagerpd2",
            )

    # ─────────────────────────────────────────────────────────────
    # Runtime checks
    # ─────────────────────────────────────────────────────────────

    def test_module_is_idempotent(self):
        lua = _make_lua()
        _load_production_chunks(lua)
        first_load = lua.globals().kyohud._killfeed_render_initialized
        # Reload module a second time
        lua.execute((ROOT / "lua" / "ky_killfeed_render.lua").read_text(encoding="utf-8-sig"))
        second_load = lua.globals().kyohud._killfeed_render_initialized
        self.assertTrue(first_load)
        self.assertTrue(second_load)
        lua.execute("assert(type(kyohud.render_killfeed) == 'function')")

    def test_module_wrong_context_installs_nothing(self):
        """When RequiredScript is not hudmanagerpd2, the module must not set
        any flag nor install render_killfeed."""
        lua = _make_lua()
        lua.globals().RequiredScript = "lib/units/weapons/newraycastweaponbase"
        _load_production_chunks(lua)
        flag = lua.eval("kyohud._killfeed_render_initialized")
        self.assertIsNone(flag, "module must not initialize outside hudmanagerpd2")
        # render_killfeed must not be installed on KH either
        fn_type = lua.eval("type(kyohud.render_killfeed)")
        self.assertEqual(fn_type, "nil", "render_killfeed must not exist outside hudmanagerpd2")

    def test_module_exposes_render_killfeed(self):
        lua = _make_lua()
        _load_production_chunks(lua)
        lua.execute("assert(type(kyohud.render_killfeed) == 'function')")

    def test_extracted_measurement_works(self):
        lua = _make_lua()
        _load_production_chunks(lua)
        _make_full_panel(lua)
        lua.execute('''
            kyohud._kills = {{
                name = "Test Enemy",
                display_text = "Test Enemy",
                score_text = "+100",
                start_t = 99,
                t_end = 104,
                _measure_font_size = nil,
            }}
            kyohud._killfeed_score_total = 100
            kyohud._killfeed_score_has_value = true
            kyohud.settings = {
                enable_killfeed = true,
                icon_size = 32,
                opacity = 0.9,
                killfeed_size = 5,
                circle_radius = 250,
            }
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.9, 250)
            assert(#kyohud._panel.texts > 0, "render_killfeed should produce text elements")
        ''')

    def test_extracted_rendering_produces_elements(self):
        lua = _make_lua()
        _load_production_chunks(lua)
        _make_full_panel(lua)
        lua.execute('''
            kyohud._kills = {{
                name = "Test Enemy",
                display_text = "Test Enemy",
                score_text = "+100",
                start_t = 99,
                t_end = 104,
                _measure_font_size = nil,
            }}
            kyohud._killfeed_score_total = 100
            kyohud._killfeed_score_has_value = true
            kyohud.settings = {
                enable_killfeed = true,
                icon_size = 32,
                opacity = 0.9,
                killfeed_size = 5,
                circle_radius = 250,
            }
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.9, 250)
            assert(#kyohud._panel.gradients > 0, "render_killfeed should produce gradients")
            assert(#kyohud._panel.texts > 0, "render_killfeed should produce texts")
        ''')

    # ─────────────────────────────────────────────────────────────
    # Regression: alpha vs settings.opacity
    # ─────────────────────────────────────────────────────────────

    def test_alpha_parameter_diverges_from_settings_opacity(self):
        """The parent used `alpha` (passed from KH:draw) for score_alpha,
        banner_alpha, medal_alpha and item_alpha — never `s.opacity`.
        When `alpha` differs from `settings.opacity`, each produced alpha
        must derive from `alpha`, not from the settings value."""
        lua = _make_lua()
        _load_production_chunks(lua)
        _make_full_panel(lua)
        # Force settings.opacity to a value that diverges from the alpha argument.
        # Then exercise each path that produces a distinct alpha channel:
        #   score path      -> score_alpha = alpha * score_intro
        #   banner path     -> banner_alpha = alpha * fade_out (special banner)
        #   medal path      -> medal_alpha = alpha * fade_out
        #   item path       -> item_alpha = alpha * (0.25 + 0.75 * life)
        lua.execute('''
            -- Freeze time at t=100. Choose kill start_t far enough in the past
            -- so score_intro = 1 and scroll = 1 (KILL_SCROLL_TIME = 0.2).
            game_t = 100

            kyohud._kills = {{
                name = "Target",
                display_text = "Target",
                score_text = "+10",
                -- start_t 0.3s before now -> score_intro = clamp(0.3/0.2,0,1) = 1
                -- life at t=100, t_end=200 -> clamp(1 - 30/200, 0, 1) = 0.85
                -- item_alpha = alpha * (0.25 + 0.75*0.85) = alpha * 0.8875
                -- scroll = 1 (newest, past KILL_SCROLL_TIME)
                start_t = 99.7,
                t_end = 200,
            }}
            kyohud._killfeed_score_total = 10
            kyohud._killfeed_score_has_value = true

            -- Special banner visible: banner_alpha = alpha * fade_out = alpha * 1
            kyohud._special_kill_banner = {
                preview = true,
                started_t = 100,
                t_end = 200,
                label = "BOSS ELIMINATED",
                color = Color(1, 0.5, 0),
            }

            -- Medal card visible: medal_alpha = alpha * fade_out = alpha * 1
            kyohud._medal_card = {
                preview = true,
                started_t = 100,
                t_end = 200,
                label = "STREAK",
                color = Color(0.5, 1, 0.5),
                kind = "default",
            }

            -- s.opacity deliberately far from alpha_arg to expose any confusion.
            kyohud.settings = {
                enable_killfeed = true,
                icon_size = 32,
                opacity = 0.1,
                killfeed_size = 5,
                circle_radius = 250,
            }

            local alpha_arg = 0.8
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, alpha_arg, 250)

            -- Helper: observed alpha must be much closer to alpha_arg than to
            -- s.opacity (0.1). A 0.5 threshold cleanly discriminates.
            local function assert_from_alpha(label, observed)
                assert(observed ~= nil, label .. " was not observed")
                assert(observed > 0.5,
                    label .. " must derive from alpha_arg (" .. tostring(alpha_arg)
                    .. "), not s.opacity (0.1); got " .. tostring(observed))
            end

            -- Score text alpha: score_alpha = alpha_arg * score_intro (1.0) = 0.8
            local score_alpha = nil
            for _, t in ipairs(kyohud._panel.texts) do
                if t.text == "+10" and t.layer == 103
                        and t.font_size and t.font_size <= 18 then
                    score_alpha = t.alpha; break
                end
            end
            -- Two +10 texts are emitted (score total at layer 103 and kill
            -- score at layer 103). Both are bounded below by alpha_arg * 0.88,
            -- since life*0.75+0.25>=0.88 for this setup.
            assert(score_alpha ~= nil, "score text must be emitted")
            assert_from_alpha("score_alpha", score_alpha)

            -- Banner text: the top text from draw_glowing_text is emitted at layer+1
            -- (107) with alpha = banner_alpha = alpha_arg.
            local banner_text_alpha = nil
            for _, t in ipairs(kyohud._panel.texts) do
                if t.layer == 107 and t.text == "BOSS ELIMINATED"
                        and math.abs(t.alpha - alpha_arg) < 1e-6 then
                    banner_text_alpha = t.alpha; break
                end
            end
            assert(banner_text_alpha ~= nil, "banner top text at layer 107 with alpha_arg must be emitted")
            assert(math.abs(banner_text_alpha - alpha_arg) < 1e-6,
                "banner text alpha must equal alpha_arg; got "
                .. tostring(banner_text_alpha))

            -- Medal text: the top text is at layer+1 (105) with alpha = medal_alpha = alpha_arg.
            local medal_text_alpha = nil
            for _, t in ipairs(kyohud._panel.texts) do
                if t.layer == 105 and t.text == "STREAK"
                        and math.abs(t.alpha - alpha_arg) < 1e-6 then
                    medal_text_alpha = t.alpha; break
                end
            end
            assert(medal_text_alpha ~= nil, "medal top text at layer 105 with alpha_arg must be emitted")
            assert(math.abs(medal_text_alpha - alpha_arg) < 1e-6,
                "medal text alpha must equal alpha_arg; got "
                .. tostring(medal_text_alpha))

            -- Item kill name at layer 102: item_alpha = alpha_arg * (0.25 + 0.75 * life)
            -- With the current setup, life ≈ 0.997, so item_alpha ≈ 0.798
            local item_alpha = nil
            for _, t in ipairs(kyohud._panel.texts) do
                if t.layer == 102 and t.text == "Target" then
                    item_alpha = t.alpha; break
                end
            end
            assert(item_alpha ~= nil, "item text must be emitted")
            assert_from_alpha("item_alpha", item_alpha)
            -- Verify it's derived from alpha_arg (0.8), not s.opacity (0.1)
            assert(item_alpha > 0.7, "item_alpha must be derived from alpha_arg, not s.opacity")
        ''')

    # ─────────────────────────────────────────────────────────────
    # Regression: chevron cache keyed by size, not style.count
    # ─────────────────────────────────────────────────────────────

    def test_chevron_cache_uses_size_key_and_dir_key(self):
        """The parent indexed RENDER_CACHES.chevrons by `size_key = w..":"..h`,
        then by `dir_key = direction > 0 and 1 or -1`. Two calls with the
        same width but different heights must produce two distinct buckets.
        The iteration count must remain SPECIAL_CHEVRON_SLOTS regardless of
        any `style.count` field the caller might pass."""
        lua = _make_lua()
        _load_production_chunks(lua)
        _make_full_panel(lua)
        lua.execute('''
            -- Reset the cache to observe fresh entries
            kyohud.RENDER_CACHES.chevrons = {}
            local panel = kyohud._panel

            -- Reach into the module's draw_chevrons by rendering two medal cards
            -- with different chevron geometry. The module only invokes draw_chevrons
            -- directly for the special banner (fixed geometry) and for the medal
            -- row with KH.MEDAL_CHEVRON_STYLE (possibly different w/h). We exercise
            -- the cache by calling render_killfeed twice under two setups: one
            -- with a special banner (uses SPECIAL geometry), one with a medal card
            -- of kind weapon_streak (uses KH.MEDAL_CHEVRON_STYLE).
            kyohud._kills = {}
            kyohud._killfeed_score_total = 0
            kyohud._killfeed_score_has_value = false
            kyohud.settings = {
                enable_killfeed = true,
                icon_size = 32,
                opacity = 0.9,
                killfeed_size = 5,
                circle_radius = 250,
            }

            -- First pass: special banner forces the SPECIAL geometry (w=7, h=12)
            kyohud._special_kill_banner = {
                preview = true,
                started_t = 100,
                t_end = 200,
                label = "BOSS",
                color = Color(1, 0.5, 0),
            }
            kyohud._medal_card = nil
            kyohud:render_killfeed(panel, 800, 600, 32, 0.9, 250)

            -- Second pass: medal card of kind weapon_streak uses KH.MEDAL_CHEVRON_STYLE
            kyohud._special_kill_banner = nil
            kyohud._medal_card = {
                preview = true,
                started_t = 100,
                t_end = 200,
                label = "STREAK",
                color = Color(0.5, 1, 0.5),
                kind = kyohud.MEDAL_KIND_WEAPON_STREAK,
            }
            kyohud:render_killfeed(panel, 800, 600, 32, 0.9, 250)

            -- Both geometries must be cached under distinct size_keys
            local chevrons = kyohud.RENDER_CACHES.chevrons
            local keys = {}
            for k in pairs(chevrons) do keys[#keys+1] = k end
            table.sort(keys)
            -- SPECIAL => "7:12"; MEDAL_CHEVRON_STYLE => "6:9"
            -- Both must be present to prove two distinct size_keys were cached
            assert(#keys >= 2, "chevron cache must contain at least TWO distinct size_keys; got " .. tostring(#keys))
            -- And each bucket has exactly two entries (dir_key 1 and -1)
            for _, k in ipairs(keys) do
                local bucket = chevrons[k]
                local n = 0
                for _ in pairs(bucket) do n = n + 1 end
                assert(n == 2, "each size_key bucket must hold exactly 2 dir_keys (1,-1); key="..k.." had "..tostring(n))
                assert(bucket[1] ~= nil, "dir_key +1 must exist under "..k)
                assert(bucket[-1] ~= nil, "dir_key -1 must exist under "..k)
            end
            -- The "7:12" bucket must be present (special banner geometry)
            assert(chevrons["7:12"] ~= nil, "SPECIAL_CHEVRON bucket must be keyed by '7:12'")
            -- The "6:9" bucket must be present (medal chevron geometry)
            assert(chevrons["6:9"] ~= nil, "MEDAL_CHEVRON bucket must be keyed by '6:9'")
        ''')

    # ─────────────────────────────────────────────────────────────
    # Regression: oldest kill left, newest right
    # ─────────────────────────────────────────────────────────────

    def test_oldest_kill_left_newest_right(self):
        """Chronological order: the oldest kill is drawn on the left,
        the newest on the right. We verify by comparing the x coordinates
        of two consecutive card frames produced for two kills with
        distinct names."""
        lua = _make_lua()
        _load_production_chunks(lua)
        _make_full_panel(lua)
        lua.execute('''
            game_t = 100
            kyohud._kills = {
                {
                    name = "Alpha", display_text = "Alpha",
                    score_text = nil,
                    start_t = 95, t_end = 200,
                },
                {
                    name = "Bravo", display_text = "Bravo",
                    score_text = nil,
                    start_t = 100, t_end = 200,
                },
            }
            kyohud._killfeed_score_total = 0
            kyohud._killfeed_score_has_value = false
            kyohud._special_kill_banner = nil
            kyohud._medal_card = nil
            kyohud.settings = {
                enable_killfeed = true,
                icon_size = 32,
                opacity = 0.9,
                killfeed_size = 5,
                circle_radius = 250,
            }
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.9, 250)

            -- Each card emits a gradient at layer 101; the first rect after that
            -- gradient sits at (x, y+2, w=2, h=item_h-4). We locate cards by the
            -- position of the name text emitted for each kill (layer 102).
            local pos = {}
            for _, t in ipairs(kyohud._panel.texts) do
                if t.layer == 102 and (t.text == "Alpha" or t.text == "Bravo") then
                    pos[t.text] = t.x
                end
            end
            assert(pos.Alpha ~= nil and pos.Bravo ~= nil,
                "both kill name texts must be emitted")
            assert(pos.Alpha < pos.Bravo,
                "oldest kill (Alpha) must be on the LEFT of the newest (Bravo); got Alpha@x="
                .. tostring(pos.Alpha) .. " Bravo@x=" .. tostring(pos.Bravo))
        ''')

    # ─────────────────────────────────────────────────────────────
    # Regression: special_enemy_color fallback parity
    # ─────────────────────────────────────────────────────────────

    def test_special_enemy_color_unknown_kind_falls_back_to_accent(self):
        """An unknown special_kind must resolve to HUD_ACCENT_COLOR (the parent
        returns nil from special_enemy_definition(kind) and the render path
        then picks `feed_color` = HUD_ACCENT_COLOR)."""
        lua = _make_lua()
        _load_production_chunks(lua)
        _make_full_panel(lua)
        lua.execute('''
            game_t = 100
            kyohud._kills = {{
                name = "Unknown", display_text = "Unknown",
                score_text = "+1",
                special_kind = "not_a_real_kind",
                start_t = 100, t_end = 200,
            }}
            kyohud._killfeed_score_total = 1
            kyohud._killfeed_score_has_value = true
            kyohud.settings = {
                enable_killfeed = true, icon_size = 32, opacity = 0.9,
                killfeed_size = 5, circle_radius = 250,
            }
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.9, 250)
            -- Find the card rect for the item; its `color` must equal HUD_ACCENT_COLOR.
            local accent = kyohud.HUD_ACCENT_COLOR
            local found = false
            for _, r in ipairs(kyohud._panel.rects) do
                if r.layer == 102 and r.color and r.color.r == accent.r and r.color.g == accent.g then
                    found = true; break
                end
            end
            assert(found, "unknown special_kind must fall back to HUD_ACCENT_COLOR")
        ''')

    # ─────────────────────────────────────────────────────────────
    # Regression: size and radius parameters, not settings
    # ─────────────────────────────────────────────────────────────

    def test_render_killfeed_uses_size_and_radius_parameters(self):
        """render_killfeed must use the `size` and `radius` parameters for
        geometry calculations (banner_h, preferred_top, fonts), not
        s.icon_size, s.circle_radius, panel:w(), or panel:h()."""
        lua = _make_lua()
        _load_production_chunks(lua)
        _make_full_panel(lua)
        lua.execute('''
            game_t = 100
            -- Deliberately set s.icon_size to a value far from the size arg,
            -- and s.circle_radius to a value far from the radius arg.
            kyohud.settings = {
                enable_killfeed = true,
                icon_size = 32,  -- will be ignored
                opacity = 0.9,
                killfeed_size = 5,
                circle_radius = 250,  -- will be ignored
            }
            kyohud._kills = {{
                name = "Target", display_text = "Target",
                score_text = "+10",
                start_t = 100, t_end = 200,
            }}
            kyohud._killfeed_score_total = 10
            kyohud._killfeed_score_has_value = true
            kyohud._special_kill_banner = nil
            kyohud._medal_card = nil

            -- Pass size=40 (different from s.icon_size=32) and radius=180
            -- (different from s.circle_radius=250).
            local size_arg = 40
            local radius_arg = 180
            kyohud:render_killfeed(kyohud._panel, 800, 600, size_arg, 0.9, radius_arg)

            -- banner_h = math.max(38, size + 8) => max(38, 48) = 48
            -- preferred_top = h * 0.5 + clamp(radius * 0.55, 70, 160)
            --               = 300 + clamp(99, 70, 160) = 300 + 99 = 399
            -- If the module used s.icon_size=32 instead: banner_h = 40
            -- If the module used s.circle_radius=250: preferred_top = 300 + 137.5 = 437.5
            -- We can detect these differences by checking the card frame positions.

            -- Find the kill card frame: the gradient at layer 101 has
            -- h = item_h - 2 (the frame trims 2px top/bottom).
            -- For size=40: item_h = 34.8, gradient h = 32.8
            -- For size=32: item_h = 29.04, gradient h = 27.04
            local item_h_from_gradient = nil
            for _, g in ipairs(kyohud._panel.gradients) do
                if g.layer == 101 and g.h and g.h > 26 and g.h < 40 then
                    item_h_from_gradient = g.h
                    break
                end
            end
            assert(item_h_from_gradient ~= nil, "must find a killfeed card gradient")
            -- With size=40: gradient h = 32.8. With size=32: gradient h = 27.04
            assert(math.abs(item_h_from_gradient - 32.8) < 0.1,
                "item_h must use size parameter (40), got gradient h=" .. tostring(item_h_from_gradient)
                .. " (expected 32.8 = 34.8 - 2)")

            -- Check kill_font_size = clamp(size * 0.42, 13, 18)
            -- For size=40: clamp(16.8, 13, 18) = 16.8
            -- For size=32: clamp(13.44, 13, 18) = 13.44
            local kill_font_size = nil
            for _, t in ipairs(kyohud._panel.texts) do
                if t.layer == 102 and t.text == "Target" then
                    kill_font_size = t.font_size
                    break
                end
            end
            assert(kill_font_size ~= nil, "kill name text must be emitted")
            assert(math.abs(kill_font_size - 16.8) < 0.1,
                "kill_font_size must use size parameter (40); expected 16.8, got "
                .. tostring(kill_font_size))

            -- Check banner font_size = clamp(size * 0.65, 17, 27) with a banner
            kyohud._special_kill_banner = {
                preview = true,
                started_t = 100,
                t_end = 200,
                label = "BOSS",
                color = Color(1, 0.5, 0),
            }
            kyohud._panel.texts = {}
            kyohud:render_killfeed(kyohud._panel, 800, 600, size_arg, 0.9, radius_arg)
            -- banner_h = max(38, 40+8) = 48
            local banner_font_size = nil
            for _, t in ipairs(kyohud._panel.texts) do
                if t.text == "BOSS" then
                    banner_font_size = t.font_size
                    break
                end
            end
            assert(banner_font_size ~= nil, "banner text must be emitted")
            -- clamp(40 * 0.65, 17, 27) = clamp(26, 17, 27) = 26
            -- clamp(32 * 0.65, 17, 27) = clamp(20.8, 17, 27) = 20.8
            assert(math.abs(banner_font_size - 26) < 0.1,
                "banner font_size must use size parameter (40); expected 26, got "
                .. tostring(banner_font_size))
        ''')

    # ─────────────────────────────────────────────────────────────
    # Static: render-only symbols absent from core, present in module
    # ─────────────────────────────────────────────────────────────

    def test_core_does_not_contain_chevron_geometry(self):
        """All render-only chevron symbols must be removed from core.lua."""
        for token in [
            "SPECIAL_CHEVRON_SLOTS",
            "SPECIAL_CHEVRON_W",
            "SPECIAL_CHEVRON_H",
            "SPECIAL_CHEVRON_GAP",
            "SPECIAL_CHEVRON_GROUP_W",
            "SPECIAL_CHEVRON_MARGIN",
            "MULTIKILL_CHEVRON_SLOTS",
            "MULTIKILL_CHEVRON_W",
            "MULTIKILL_CHEVRON_H",
            "MULTIKILL_CHEVRON_GAP",
            "MULTIKILL_CHEVRON_GROUP_W",
            "MULTIKILL_CHEVRON_MARGIN",
            "BANNER_CHEVRON_TEXT_GAP",
            "MULTIKILL_CHEVRON_GLOW_W",
            "MULTIKILL_CHEVRON_GLOW_H",
            "MULTIKILL_CHEVRON_GLOW_DX",
            "MULTIKILL_CHEVRON_HOLE_INSET",
            "MULTIKILL_CHEVRON_OUTLINE_ALPHA",
            "MULTIKILL_CHEVRON_HOLE_ALPHA",
            "MULTIKILL_CHEVRON_GLOW_ALPHA",
            "chevron_triangles",
            "inset_chevron_triangles",
            "MULTIKILL_CHEVRON_SHAPES",
            "TEXT_GLOW_OFFSETS",
        ]:
            self.assertNotIn(token, self.core_source,
                f"core.lua must not contain render-only symbol '{token}'")

    def test_module_contains_chevron_geometry_as_private(self):
        """All chevron geometry must be in the module's C table as private."""
        self.assertIn("C.MULTIKILL_CHEVRON_SHAPES", self.module_source)
        self.assertIn("C.TEXT_GLOW_OFFSETS", self.module_source)
        self.assertIn("BANNER_CHEVRON_TEXT_GAP", self.module_source)
        # chevron_triangles and inset_chevron_triangles must exist as local helpers
        self.assertIn("local function chevron_triangles(w, h, direction)", self.module_source)
        self.assertIn("local function inset_chevron_triangles(w, h, direction, inset)", self.module_source)
        # They must NOT be on KH (private to the module)
        self.assertNotIn("KH.chevron_triangles", self.module_source)
        self.assertNotIn("KH.inset_chevron_triangles", self.module_source)

    def test_core_first_line_has_no_bom(self):
        """The first line of core.lua must not start with a BOM."""
        raw = (ROOT / "lua" / "core.lua").read_bytes()
        self.assertFalse(raw.startswith(b'\xef\xbb\xbf'),
            "core.lua must not start with a UTF-8 BOM")
        self.assertTrue(raw.startswith(b'-- core.lua'),
            "core.lua must start with '-- core.lua'")


if __name__ == "__main__":
    unittest.main()

"""Exhaustive visual coverage regressions for the autonomous HUDList catalog."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class HUDListIconCoverageTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/hudmanagerpd2"
            Hooks = {}
            Application = {time = function() return 100 end}
        ''')
        self.lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))

    def test_every_productible_id_has_explicit_visual_metadata(self):
        self.lua.execute('''
            local catalog = kyohud.hudlist_catalog
            local seen = {}

            local function visit(value)
                if type(value) == "string" then
                    seen[catalog:resolve_alias(value)] = true
                elseif type(value) == "table" and type(value.id) == "string" then
                    visit(value.id)
                elseif type(value) == "table" then
                    for _, nested in pairs(value) do visit(nested) end
                end
            end

            visit(catalog.mappings)
            for id in pairs(catalog.direct_ids.literals) do visit(id) end
            for _, targets in pairs(catalog.routes) do visit(targets) end

            for id in pairs(seen) do
                local definition = catalog.definitions[id]
                assert(definition, "missing definition: " .. id)
                assert(definition.icon_provenance,
                    "missing icon provenance: " .. id)
                local has_icon = definition.skill_id or definition.skills_new or definition.skills
                    or definition.perks or definition.hud_tweak or definition.texture
                assert(has_icon, "missing icon descriptor: " .. id)
                if definition.hud_tweak == "pd2_generic_tickbox" then
                    assert(definition.intentional_fallback == true,
                        "unreviewed generic icon: " .. id)
                    assert(type(definition.fallback_reason) == "string"
                        and definition.fallback_reason ~= "",
                        "undocumented generic icon: " .. id)
                end
            end
        ''')

    def test_aliases_and_routes_resolve_to_defined_visual_targets(self):
        self.lua.execute('''
            local catalog = kyohud.hudlist_catalog
            for alias, target in pairs(catalog.aliases) do
                assert(catalog.definitions[target],
                    "alias target has no definition: " .. alias .. " -> " .. target)
            end
            for source, targets in pairs(catalog.routes) do
                assert(type(source) == "string" and #targets > 0,
                    "invalid route: " .. tostring(source))
                for _, target in ipairs(targets) do
                    assert(catalog.definitions[catalog:resolve_alias(target)],
                        "route target has no definition: " .. source .. " -> " .. target)
                end
            end
        ''')

    def test_runtime_catalog_does_not_expose_debug_showcase(self):
        source = (ROOT / "lua" / "hudlist_catalog.lua").read_text(encoding="utf-8-sig")
        menu = (ROOT / "menu" / "menu.json").read_text(encoding="utf-8-sig")
        self.assertNotIn("Showcase Everything", source)
        self.assertNotIn("Showcase Everything", menu)

    def test_headless_preview_resolves_every_catalog_icon_without_hud_timer(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/hudmanagerpd2"
            Hooks = {callbacks = {}}
            function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:Add(...) end
            HUDManager = {}; PlayerManager = {}; managers = {}
            function Vector3(...) return {...} end
            function log(...) end
            function alive(value) return value ~= nil end
            function Idstring(value) return value end
            DB = {has = function() return true end}
            local function color() return {with_alpha = function(self) return self end} end
            Color = setmetatable({white = color(), black = color()}, {
                __call = function(...) return color() end,
            })
            TimerManager = {game = function()
                return {time = function() return 100 end}
            end}
            Application = {time = function() return 100 end}
            local skills = setmetatable({}, {__index = function(table, id)
                local skill = {icon_xy = {1, 1}}
                rawset(table, id, skill)
                return skill
            end})
            tweak_data = {
                skilltree = {skills = skills},
                hud_icons = {get_icon_data = function(self, id)
                    return "native/" .. id, {0, 0, 32, 32}
                end},
            }
        ''')
        lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
        lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        lua.execute((ROOT / "lua" / "ky_buff_render.lua").read_text(encoding="utf-8-sig"))
        lua.execute('''
            kyohud.settings = {enable_buffs = true}
            local catalog = kyohud.hudlist_catalog
            for id, definition in pairs(catalog.definitions) do
                if not definition.ignore then
                    kyohud:add_buff(id, nil, 5, nil, false, false, nil, nil)
                    local card = kyohud._buffs[id]
                    assert(card and card.icon and card.icon.texture,
                        "headless preview failed: " .. id)
                    assert(card.icon.texture ~= "guis/textures/pd2/hud_timer",
                        "unexpected hud_timer fallback: " .. id)
                    kyohud:remove_buff(id)
                end
            end
        ''')


if __name__ == "__main__":
    unittest.main()
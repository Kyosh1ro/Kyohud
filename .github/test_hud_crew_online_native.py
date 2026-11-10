"""Human native leaves: represented channels only, reversible and source-qualified."""
import unittest
from test_hud_crew_online_ammo import _crew_lua, RENDER_SETUP, ACTORS_PATH


def online_runtime():
    lua, ok = _crew_lua()
    assert ok
    lua.execute(RENDER_SETUP)
    # The base fixture records hooks; RENDER_SETUP wraps only later installs.
    # Reinstall this one real callback through that wrapper, not a no-op setter.
    lua.execute('kyohud.hud._installed_hooks.KyohHUD_Actors_Revives=nil')
    for context in ('lib/managers/playermanager', 'lib/managers/hudmanagerpd2'):
        lua.globals().RequiredScript = context
        lua.execute(ACTORS_PATH.read_text(encoding='utf-8-sig'))
    lua.execute(r'''
        kyohud.settings.enable_hud_foundation=true
        kyohud.settings.enable_crew=true
        panel_double:set_shape(0,0,1920,1080)
        A=kyohud.hud.actors; R=kyohud.hud.runtime; C=kyohud.hud.crew
        A:refresh_crew(managers.hud,0)
        managers.player:set_synced_ammo_info(2,1,30,7,67,120)
        managers.player:set_synced_ammo_info(2,2,40,12,95,160)
        local ep=panel_double:panel({name='native_crew'})
        ep:set_shape(0,0,432,120)
        managers.hud._teammate_panels[2]._panel=ep
        local player=ep:panel({name='player'})
        player:set_shape(0,0,432,120)
        local weapons=player:panel({name='weapons_panel'})
        targets={}; parents={ep,player,weapons}
        local function leaves(p,names)
            for _,name in ipairs(names) do
                local leaf=p:bitmap({name=name})
                leaf:set_shape(0,0,10,10); leaf:set_alpha(.7)
                targets[#targets+1]=leaf
            end
        end
        for _,name in ipairs({'secondary_weapon_panel','primary_weapon_panel'}) do
            local p=weapons:panel({name=name}); parents[#parents+1]=p
            leaves(p,{'bg','ammo_clip','ammo_total'})
            local sel=p:panel({name='weapon_selection'}); parents[#parents+1]=sel
            leaves(sel,{'weapon_selection'})
        end
        local dep=player:panel({name='deployable_equipment_panel'}); parents[#parents+1]=dep
        leaves(dep,{'bg','equipment','amount'})
        local ties=player:panel({name='cable_ties_panel'}); parents[#parents+1]=ties
        leaves(ties,{'bg','cable_ties','amount'})
        local rev=player:panel({name='revive_panel'}); parents[#parents+1]=rev
        leaves(rev,{'revive_bg','revive_amount','revive_arrow'})
        unique=player:bitmap({name='grenades_radial'}); unique:set_alpha(.6)
        _parent_writes=0
        for _,p in ipairs(parents) do
            local set=p.set_alpha
            p.set_alpha=function(self,v) _parent_writes=_parent_writes+1; return set(self,v) end
        end
        -- Complete the native owner before publishing its accepted event.
        managers.hud:set_teammate_revives(2,4)
        assert(A:get_crew_snapshot()[2].downs==3,'qualified downs before mount')
        R:mount(managers.hud); R:update(managers.hud,1,.05)
        assert(C:_verify_render(),'positive real human card')
        assert(C._cards[2]._inactive_ammo_text:text()=='012/083','positive inactive presentation')
    ''')
    return lua


class CrewOnlineNativeTests(unittest.TestCase):
    def test_known_channels_hide_only_leaves_and_restore_on_failure(self):
        lua = online_runtime()
        lua.execute(r'''
            _masked=true
            for _,p in ipairs(targets) do if p:alpha()~=0 then _masked=false end end
            _unique=unique:alpha()
            local card=C._cards[2]
            local setter=card._inactive_ammo_text.set_text
            card._inactive_ammo_text:set_text('corrupt')
            card._inactive_ammo_text.set_text=function() end
            -- Approved compromise: 1.01 is a throttled crew presentation frame, so
            -- detection is deferred to the next meta frame (1.2, at most 0.05 s later).
            R:update(managers.hud,1.01,.001)
            R:update(managers.hud,1.2,.05)
            _restored=true
            for _,p in ipairs(targets) do if p:alpha()~=.7 then _restored=false end end
            card._inactive_ammo_text.set_text=setter
            R:update(managers.hud,1.3,.05)
            _recovered=C:_verify_render() and C._cards[2]==card
            _remasked=true
            for _,p in ipairs(targets) do if p:alpha()~=0 then _remasked=false end end
        ''')
        g=lua.globals()
        self.assertIs(g._masked, True)
        self.assertIs(g._restored, True)
        self.assertIs(g._recovered, True)
        self.assertIs(g._remasked, True)
        self.assertEqual(g._unique, .6)
        self.assertEqual(g._parent_writes, 0)

    def test_readonly_native_pass_does_not_deepcopy_public_snapshots(self):
        lua = online_runtime()
        lua.execute(r'''
            local get=A.get_crew_snapshot
            _copies=0
            A.get_crew_snapshot=function(self) _copies=_copies+1; return get(self) end
            for i=1,10 do R:_coordinate_h5_native_duplicates() end
        ''')
        self.assertEqual(lua.globals()._copies, 0)

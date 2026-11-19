"""get_snapshot must reuse static detached parts and keep cooldown fresh.

RED today: every get_snapshot call deep-copies deployables, cables and the
projectile into brand-new tables. The contract cached here is that the static
detached copy is reused while self._snapshot keeps its identity, that the copy
never aliases the internal tables, that cooldown stays fresh per call, and that
refresh() rebuilds the cached copy.
"""
import unittest

from test_hud_equipment_presentation import presentation


class EquipmentSnapshotStaticCacheTests(unittest.TestCase):
    def test_static_parts_reused_dynamic_cooldown_fresh_and_refresh_rebuilds(self):
        l = presentation()
        l.execute(r'''
            snap1=E:get_snapshot()
            snap2=E:get_snapshot()
            static_same=(snap1.deployables==snap2.deployables
                and snap1.cables==snap2.cables
                and snap1.projectile==snap2.projectile)
            detached_from_internal=(snap1.deployables~=E._snapshot.deployables
                and snap1.cables~=E._snapshot.cables
                and snap1.projectile~=E._snapshot.projectile)
            cooldown_dynamic=(snap1.cooldown~=snap2.cooldown)
            E:refresh(managers.hud)
            snap3=E:get_snapshot()
            rebuilt_after_refresh=(snap3.projectile~=snap1.projectile
                and snap3.deployables~=snap1.deployables)
        ''')
        g = l.globals()
        self.assertIs(g.static_same, True,
            'static detached parts must be reused while _snapshot is unchanged')
        self.assertIs(g.detached_from_internal, True,
            'returned static parts must stay detached copies of internals')
        self.assertIs(g.cooldown_dynamic, True,
            'cooldown must stay a fresh table on every get_snapshot call')
        self.assertIs(g.rebuilt_after_refresh, True,
            'refresh() must rebuild the cached static detached copy')


if __name__ == '__main__': unittest.main()

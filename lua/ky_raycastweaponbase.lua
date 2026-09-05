-- ky_raycastweaponbase.lua — Médailles locales agrégées par tir

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

Hooks:PostHook(
    RaycastWeaponBase,
    "_check_kill_achievements",
    "KH_RaycastKillMedals",
    function(self, cop_kill_count, unit_base, unit_type, is_civilian, hit_through_wall, hit_through_shield)
        -- Cette méthode est appelée une fois pour chaque mort du rayon. Le
        -- compteur passe par 2 une seule fois : tester `== 2` garantit donc une
        -- seule carte pour tout tir ayant tué au moins deux ennemis.
        if cop_kill_count == 2 and KH.ShowEventMedal then
            KH:ShowEventMedal("one_shot_two_kills")
        end

        if hit_through_shield == true and not is_civilian
                and KH.GetSpecialEnemyKind
                and KH:GetSpecialEnemyKind(unit_type) == "shield"
                and KH.ShowEventMedal then
            KH:ShowEventMedal("through_shield")
        end
    end
)

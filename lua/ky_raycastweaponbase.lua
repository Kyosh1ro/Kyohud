-- ky_raycastweaponbase.lua — Médailles locales agrégées par tir

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

Hooks:PostHook(
    RaycastWeaponBase,
    "_check_kill_achievements",
    "KH_RaycastKillMedals",
    function(self, cop_kill_count, unit_base, unit_type, is_civilian, hit_through_wall, hit_through_shield)
        -- `cop_kill_count` repart à 1 au premier ennemi tué par chaque tir. Une
        -- victime civile peut répéter la valeur courante, elle ne doit donc pas
        -- être prise pour le début d'un nouveau tir.
        if not is_civilian and cop_kill_count == 1 then
            self._kyohud_wall_bang_card = nil
        end

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

        -- `hit_through_wall` est cumulatif pendant le rayon. La première victime
        -- derrière le mur crée une carte ; les suivantes du même tir mettent à
        -- jour cette même table jusqu'à « Wallbang xN ». `cop_kill_count` est le
        -- total natif d'ennemis tués par ce tir, sans les civils. Aucun kill ni
        -- score n'est rejoué ici : les morts passent déjà par le chemin dédupliqué.
        if hit_through_wall == true and not is_civilian and KH.ShowEventMedal then
            local card = self._kyohud_wall_bang_card
            if card and KH.UpdateEventMedalCount then
                KH:UpdateEventMedalCount(card, cop_kill_count)
            else
                self._kyohud_wall_bang_card = KH:ShowEventMedal(
                    "wall_bang", cop_kill_count
                )
            end
        end
    end
)

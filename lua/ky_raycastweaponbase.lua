-- ky_raycastweaponbase.lua — Local medals aggregated per shot

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

Hooks:PostHook(
    RaycastWeaponBase,
    "_check_kill_achievements",
    "KH_RaycastKillMedals",
    function(self, cop_kill_count, unit_base, unit_type, is_civilian, hit_through_wall, hit_through_shield)
        -- `cop_kill_count` resets to 1 on the first enemy killed per shot. A civilian victim can repeat the current value, so it must not be taken as the start of a new shot.
        if not is_civilian and cop_kill_count == 1 then
            self._kyohud_wall_bang_card = nil
            self._kyohud_collateral_emitted = nil
        end

        -- This method is called once for each kill along the ray. Civilians do not advance `cop_kill_count` and can therefore repeat the value 2.
        -- The filter and lock guarantee a single Collateral card per shot.
        if not is_civilian and cop_kill_count == 2
                and not self._kyohud_collateral_emitted
                and KH.ShowEventMedal then
            self._kyohud_collateral_emitted = true
            KH:ShowEventMedal("one_shot_two_kills")
        end

        if hit_through_shield == true and not is_civilian
                and KH.GetSpecialEnemyKind
                and KH:GetSpecialEnemyKind(unit_type) == "shield"
                and KH.ShowEventMedal then
            KH:ShowEventMedal("through_shield")
        end

        -- `hit_through_wall` is cumulative during the ray. The first victim behind the wall creates a card; subsequent ones from the same shot update this same table up to « Wallbang xN ». `cop_kill_count` is the native total of enemies killed by this shot, excluding civilians. No kill or score is replayed here: deaths already pass through the deduplicated path.
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

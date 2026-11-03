"""Native-shaped owned rectangle and text measurement support for HUD tests."""

PRESENTATION_DIESEL = r'''
Color = setmetatable({}, {__call = function(_, a, r, g, b)
    if b == nil then return {1,a,r,g,a=1, r=a, g=r, b=g} end
    return {a,r,g,b,a=a, r=r, g=g, b=b}
end})
local original_make_panel = _make_panel
function _make_panel(name)
    local p = original_make_panel(name)
    if type(p.x) ~= "function" then function p:x() return self._x or 0 end end
    if type(p.y) ~= "function" then function p:y() return self._y or 0 end end
    function p:rect(opts)
        local r = self:panel(opts)
        r:set_shape(opts.x or 0, opts.y or 0, opts.w or self:w(), opts.h or self:h())
        r._color = opts.color or Color(1, 1, 1)
        r._alpha = opts.alpha or r._color.a or 1
        r._visible = opts.visible ~= false
        function r:color() return self._color end
        function r:set_color(c) self._color = c; self._alpha = c.a end
        return r
    end
    local original_text = p.text
    function p:text(opts)
        local t = original_text(self, opts)
        t:set_shape(opts.x or 0, opts.y or 0, opts.w or self:w(), opts.h or self:h())
        if opts.font_size ~= nil then t._font_size = opts.font_size end
        if type(t.font_size) ~= "function" then
            function t:font_size() return self._font_size end
            function t:set_font_size(v) self._font_size = v end
        end
        t._color = opts.color or Color(1, 1, 1)
        if type(t.color) ~= "function" then
            function t:color() return self._color end
            function t:set_color(c) self._color = c; self._alpha = c.a end
        end
        if type(t.text_rect) ~= "function" then
            function t:text_rect() return 0, 0, #self:text() * self:font_size() * 0.5, self:font_size() end
        end
        return t
    end
    return p
end
'''

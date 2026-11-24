import datetime
import math

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import (
    Color,
    Ellipse,
    Line,
    Mesh,
    PopMatrix,
    PushMatrix,
    Rectangle,
    Rotate,
    RoundedRectangle,
)
from kivy.uix.widget import Widget


def _solid_hand_vertices(cx: float, cy: float, length: float, tail: float, half_width: float):
    """
    Returns vertices and indices for a filled tapered hand in local unrotated coordinates
    pointing along +Y (12 o'clock). Format: [x, y, u, v] per vertex.
    """
    pts = [
        (cx, cy + length),                          # 0: tip
        (cx + half_width, cy + length * 0.15),      # 1: right shoulder
        (cx + half_width * 0.72, cy - tail),        # 2: right tail
        (cx - half_width * 0.72, cy - tail),        # 3: left tail
        (cx - half_width, cy + length * 0.15),      # 4: left shoulder
    ]
    vertices = []
    for x, y in pts:
        vertices.extend([x, y, 0.0, 0.0])

    # Convex pentagon fan from vertex 0
    indices = [0, 1, 2, 0, 2, 3, 0, 3, 4]
    outline_coords = []
    for x, y in pts:
        outline_coords.extend([x, y])
    return vertices, indices, outline_coords


class AnalogClockWidget(Widget):
    def __init__(self, smooth_seconds: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.smooth_seconds = smooth_seconds

        # Palette
        self.bg_color = (0.071, 0.086, 0.122, 1.0)          # #12161F
        self.bezel_color = (0.220, 0.271, 0.361, 1.0)       # #38455C
        self.dial_color = (0.106, 0.129, 0.180, 1.0)        # #1B212E
        self.dial_rim = (0.196, 0.239, 0.322, 1.0)          # #323D52
        self.major_tick_color = (0.922, 0.945, 0.980, 1.0)  # #EBF1FA
        self.minor_tick_color = (0.400, 0.455, 0.553, 1.0)  # #66748D
        self.numeral_color = (0.890, 0.918, 0.961, 1.0)     # #E3EAF5
        self.subdial_bg = (0.145, 0.180, 0.247, 1.0)        # #252E3F
        self.subdial_border = (0.345, 0.549, 0.788, 1.0)    # #588CC9
        self.hour_hand_color = (0.965, 0.976, 0.992, 1.0)   # #F6F9FD
        self.minute_hand_color = (0.820, 0.867, 0.933, 1.0) # #D1DDED
        self.second_hand_color = (1.0, 0.353, 0.373, 1.0)   # #FF5A5F
        self.accent_color = (0.345, 0.710, 0.949, 1.0)      # #58B5F2
        self.dark_outline = (0.047, 0.059, 0.082, 1.0)      # #0C0F15

        self._text_cache = {}

        self.bind(size=self._redraw, pos=self._redraw)
        interval = (1.0 / 60.0) if self.smooth_seconds else 0.2
        self.event = Clock.schedule_interval(self._redraw, interval)

    def _get_text_texture(self, text: str, font_size: int, color: tuple):
        key = (text, font_size, tuple(round(c, 3) for c in color))
        if key not in self._text_cache:
            lbl = CoreLabel(text=text, font_size=font_size, color=color, bold=True)
            lbl.refresh()
            self._text_cache[key] = lbl.texture
        return self._text_cache[key]

    def _draw_solid_hand(
        self,
        cx: float,
        cy: float,
        angle_cw_deg: float,
        length: float,
        tail: float,
        half_width: float,
        fill_color: tuple,
        outline_color: tuple,
    ):
        kivy_angle = -angle_cw_deg
        verts, indices, outline_pts = _solid_hand_vertices(cx, cy, length, tail, half_width)

        with self.canvas:
            # Drop shadow
            PushMatrix()
            Rotate(angle=kivy_angle, origin=(cx + 2.5, cy - 3.0))
            Color(0.0, 0.0, 0.0, 0.42)
            Mesh(vertices=verts, indices=indices, mode="triangles")
            PopMatrix()

            # Solid hand fill + crisp edge
            PushMatrix()
            Rotate(angle=kivy_angle, origin=(cx, cy))
            Color(*fill_color)
            Mesh(vertices=verts, indices=indices, mode="triangles")
            Color(*outline_color)
            Line(points=outline_pts, close=True, width=1.2)
            PopMatrix()

    def _redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return

        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        radius = min(self.width, self.height) * 0.44

        with self.canvas:
            # Background
            Color(*self.bg_color)
            Rectangle(pos=self.pos, size=self.size)

            # Bezel and dial
            Color(*self.bezel_color)
            Line(circle=(cx, cy, radius * 1.05), width=max(2.5, radius * 0.035))

            Color(*self.dial_color)
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))

            Color(*self.dial_rim)
            Line(circle=(cx, cy, radius), width=1.6)

            # 60 ticks and 12 hour numerals
            numeral_font_px = max(14, int(radius * 0.155))
            for i in range(60):
                deg_cw = i * 6.0
                rad = math.radians(deg_cw)
                dx = math.sin(rad)
                dy = math.cos(rad)

                is_hour = (i % 5 == 0)
                is_quarter = (i % 15 == 0)

                if is_hour:
                    outer_r = radius * 0.94
                    inner_r = radius * (0.80 if is_quarter else 0.83)
                    tick_w = max(2.0, radius * (0.032 if is_quarter else 0.024))
                    Color(*self.major_tick_color)
                else:
                    outer_r = radius * 0.94
                    inner_r = radius * 0.89
                    tick_w = max(1.1, radius * 0.012)
                    Color(*self.minor_tick_color)

                Line(
                    points=[
                        cx + inner_r * dx,
                        cy + inner_r * dy,
                        cx + outer_r * dx,
                        cy + outer_r * dy,
                    ],
                    width=tick_w,
                    cap="round",
                )

                if is_hour:
                    hour_val = 12 if i == 0 else i // 5
                    num_r = radius * 0.67
                    tx = cx + num_r * dx
                    ty = cy + num_r * dy
                    n_color = self.accent_color if is_quarter else self.numeral_color
                    tex = self._get_text_texture(str(hour_val), numeral_font_px, n_color)
                    Rectangle(
                        texture=tex,
                        pos=(tx - tex.width / 2.0, ty - tex.height / 2.0),
                        size=tex.size,
                    )

            # High-visibility Day / Date badge at 3 o'clock
            today = datetime.date.today()
            day_str = today.strftime("%a").upper()
            date_str = today.strftime("%d")

            box_w = max(68.0, radius * 0.42)
            box_h = max(28.0, radius * 0.22)
            box_x = cx + radius * 0.22
            box_y = cy - box_h / 2.0

            Color(*self.subdial_bg)
            RoundedRectangle(pos=(box_x, box_y), size=(box_w, box_h), radius=[6])

            Color(*self.subdial_border)
            Line(rounded_rectangle=(box_x, box_y, box_w, box_h, 6), width=1.5)

            split_x = box_x + box_w * 0.50
            Line(points=[split_x, box_y + 3, split_x, box_y + box_h - 3], width=1.2)

            badge_font_px = max(12, int(box_h * 0.48))
            day_tex = self._get_text_texture(day_str, badge_font_px, self.accent_color)
            Rectangle(
                texture=day_tex,
                pos=(
                    box_x + (split_x - box_x - day_tex.width) / 2.0,
                    box_y + (box_h - day_tex.height) / 2.0,
                ),
                size=day_tex.size,
            )

            date_tex = self._get_text_texture(date_str, badge_font_px, self.major_tick_color)
            Rectangle(
                texture=date_tex,
                pos=(
                    split_x + (box_x + box_w - split_x - date_tex.width) / 2.0,
                    box_y + (box_h - date_tex.height) / 2.0,
                ),
                size=date_tex.size,
            )

            # Current time & hand angles
            now = datetime.datetime.now()
            if self.smooth_seconds:
                exact_sec = now.second + now.microsecond / 1_000_000.0
            else:
                exact_sec = float(now.second)

            exact_min = now.minute + exact_sec / 60.0
            exact_hour = (now.hour % 12) + exact_min / 60.0

            hour_angle = exact_hour * 30.0
            minute_angle = exact_min * 6.0
            second_angle = exact_sec * 6.0

            # Solid Hour Hand
            self._draw_solid_hand(
                cx,
                cy,
                angle_cw_deg=hour_angle,
                length=radius * 0.50,
                tail=radius * 0.12,
                half_width=max(4.5, radius * 0.048),
                fill_color=self.hour_hand_color,
                outline_color=self.dark_outline,
            )

            # Solid Minute Hand
            self._draw_solid_hand(
                cx,
                cy,
                angle_cw_deg=minute_angle,
                length=radius * 0.73,
                tail=radius * 0.15,
                half_width=max(3.5, radius * 0.034),
                fill_color=self.minute_hand_color,
                outline_color=self.dark_outline,
            )

            # Second Hand + Counterweight
            PushMatrix()
            Rotate(angle=-second_angle, origin=(cx, cy))
            Color(*self.second_hand_color)
            Line(
                points=[cx, cy - radius * 0.19, cx, cy + radius * 0.82],
                width=max(1.6, radius * 0.018),
                cap="round",
            )
            counter_r = max(3.5, radius * 0.036)
            Ellipse(
                pos=(cx - counter_r, cy - radius * 0.12 - counter_r),
                size=(counter_r * 2, counter_r * 2),
            )
            PopMatrix()

            # Center Cap
            outer_cap_r = max(5.5, radius * 0.060)
            inner_cap_r = max(2.2, radius * 0.025)
            Color(*self.dial_rim)
            Ellipse(pos=(cx - outer_cap_r, cy - outer_cap_r), size=(outer_cap_r * 2, outer_cap_r * 2))
            Color(*self.dark_outline)
            Line(circle=(cx, cy, outer_cap_r), width=1.3)
            Color(*self.second_hand_color)
            Ellipse(pos=(cx - inner_cap_r, cy - inner_cap_r), size=(inner_cap_r * 2, inner_cap_r * 2))


class AnalogClockApp(App):
    def build(self):
        Window.clearcolor = (0.071, 0.086, 0.122, 1.0)
        Window.maxfps = 60
        # Set smooth_seconds=False if you prefer crisp 1-second ticks over sweep
        return AnalogClockWidget(smooth_seconds=True)


if __name__ == "__main__":
    AnalogClockApp().run()

import math
import os
import tkinter as tk

import config
from adsb import load_aircraft
from projection import TILE_SIZE, latlon_to_world, world_to_latlon
from tilemanager import TileManager


class MapScreen(tk.Frame):
    MIN_ZOOM = 6
    MAX_ZOOM = 15

    def __init__(self, parent, show_dashboard):
        super().__init__(parent, bg=config.BACKGROUND, cursor="none")
        self.show_dashboard = show_dashboard
        self.zoom = getattr(config, "MAP_ZOOM", 10)
        self.center_lat = config.HOME_LAT
        self.center_lon = config.HOME_LON
        self.tile_images = {}
        self.tile_items = {}
        self.aircraft_hitboxes = []
        self.selected_hex = None
        self.drag_start = None
        self.drag_center_world = None
        self.redraw_pending = False

        self.tile_manager = TileManager(
            getattr(config, "MAP_CACHE_DIR", "~/.cache/falcondeck/tiles"),
            self._tile_downloaded,
        )

        self._build_header()
        self._build_canvas()
        self.after(150, self.redraw)
        self.after(config.REFRESH_MS, self._refresh_aircraft)

    def _build_header(self):
        header = tk.Frame(self, bg=config.PANEL, height=48, cursor="none")
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Button(
            header, text="HOME", command=self.show_dashboard,
            bg=config.PANEL_LIGHT, fg=config.TEXT,
            activebackground=config.ACCENT, activeforeground="#000000",
            relief="flat", bd=0, font=("DejaVu Sans", 10, "bold"),
            padx=14, pady=5, cursor="none",
        ).pack(side="left", padx=7, pady=7)

        tk.Label(
            header, text="MOVING MAP", bg=config.PANEL, fg=config.ACCENT,
            font=("DejaVu Sans", 15, "bold"), cursor="none",
        ).pack(side="left", padx=8)

        self.status_label = tk.Label(
            header, text="LOADING MAP", bg=config.PANEL, fg=config.DIM_TEXT,
            font=("DejaVu Sans", 10, "bold"), cursor="none",
        )
        self.status_label.pack(side="left", padx=6)

        tk.Button(
            header, text="+", command=lambda: self.change_zoom(1),
            bg=config.PANEL_LIGHT, fg=config.TEXT, relief="flat", bd=0,
            font=("DejaVu Sans", 15, "bold"), width=3, cursor="none",
        ).pack(side="right", padx=(2, 7), pady=7)

        tk.Button(
            header, text="−", command=lambda: self.change_zoom(-1),
            bg=config.PANEL_LIGHT, fg=config.TEXT, relief="flat", bd=0,
            font=("DejaVu Sans", 15, "bold"), width=3, cursor="none",
        ).pack(side="right", padx=2, pady=7)

        tk.Button(
            header, text="CENTRE", command=self.centre_home,
            bg=config.PANEL_LIGHT, fg=config.TEXT, relief="flat", bd=0,
            font=("DejaVu Sans", 9, "bold"), padx=10, cursor="none",
        ).pack(side="right", padx=4, pady=7)

    def _build_canvas(self):
        self.canvas = tk.Canvas(
            self, bg="#101820", highlightthickness=0, cursor="none"
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda event: self.schedule_redraw())
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Button-4>", lambda event: self.change_zoom(1))
        self.canvas.bind("<Button-5>", lambda event: self.change_zoom(-1))

    def centre_home(self):
        self.center_lat = config.HOME_LAT
        self.center_lon = config.HOME_LON
        self.selected_hex = None
        self.redraw()

    def change_zoom(self, amount):
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom + amount))
        if new_zoom != self.zoom:
            self.zoom = new_zoom
            self.redraw()

    def _wheel(self, event):
        self.change_zoom(1 if event.delta > 0 else -1)

    def _press(self, event):
        self.drag_start = (event.x, event.y)
        self.drag_center_world = latlon_to_world(
            self.center_lat, self.center_lon, self.zoom
        )

    def _drag(self, event):
        if not self.drag_start or not self.drag_center_world:
            return
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        world_x = self.drag_center_world[0] - dx
        world_y = self.drag_center_world[1] - dy
        self.center_lat, self.center_lon = world_to_latlon(world_x, world_y, self.zoom)
        self.redraw()

    def _release(self, event):
        moved = False
        if self.drag_start:
            moved = abs(event.x - self.drag_start[0]) > 7 or abs(event.y - self.drag_start[1]) > 7
        if not moved:
            self._select_aircraft(event.x, event.y)
        self.drag_start = None
        self.drag_center_world = None

    def _select_aircraft(self, x, y):
        for x1, y1, x2, y2, aircraft_hex in reversed(self.aircraft_hitboxes):
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.selected_hex = aircraft_hex
                self.redraw()
                return
        self.selected_hex = None
        self.redraw()

    def schedule_redraw(self):
        if not self.redraw_pending:
            self.redraw_pending = True
            self.after_idle(self.redraw)

    def redraw(self):
        self.redraw_pending = False
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        self.canvas.delete("all")
        self.tile_items.clear()
        self.aircraft_hitboxes.clear()

        centre_x, centre_y = latlon_to_world(self.center_lat, self.center_lon, self.zoom)
        left = centre_x - width / 2
        top = centre_y - height / 2
        first_tile_x = math.floor(left / TILE_SIZE)
        first_tile_y = math.floor(top / TILE_SIZE)
        last_tile_x = math.floor((left + width) / TILE_SIZE)
        last_tile_y = math.floor((top + height) / TILE_SIZE)

        loaded = 0
        requested = 0
        for tile_y in range(first_tile_y, last_tile_y + 1):
            for tile_x in range(first_tile_x, last_tile_x + 1):
                screen_x = tile_x * TILE_SIZE - left
                screen_y = tile_y * TILE_SIZE - top
                max_tile = 1 << self.zoom
                wrapped_x = tile_x % max_tile
                path = self.tile_manager.request(self.zoom, wrapped_x, tile_y)
                requested += 1
                if path:
                    image = self._load_tile(path)
                    if image:
                        self.canvas.create_image(screen_x, screen_y, image=image, anchor="nw")
                        loaded += 1
                    else:
                        self._draw_tile_placeholder(screen_x, screen_y)
                else:
                    self._draw_tile_placeholder(screen_x, screen_y)

        self._draw_home(left, top)
        self._draw_range_rings(left, top)
        aircraft = self._draw_aircraft(left, top)
        self._draw_attribution(width, height)
        self.status_label.config(
            text=f"Z{self.zoom}  {aircraft} AIRCRAFT  {loaded}/{requested} TILES"
        )

    def _load_tile(self, path):
        try:
            mtime = os.path.getmtime(path)
            cached = self.tile_images.get(path)
            if cached and cached[0] == mtime:
                return cached[1]
            image = tk.PhotoImage(file=path)
            self.tile_images[path] = (mtime, image)
            if len(self.tile_images) > 80:
                self.tile_images.pop(next(iter(self.tile_images)))
            return image
        except (tk.TclError, OSError):
            return None

    def _draw_tile_placeholder(self, x, y):
        self.canvas.create_rectangle(
            x, y, x + TILE_SIZE, y + TILE_SIZE,
            fill="#10202c", outline="#173747"
        )

    def _tile_downloaded(self, z, x, y, path):
        try:
            self.after(0, self.schedule_redraw)
        except tk.TclError:
            pass

    def _screen_position(self, latitude, longitude, left, top):
        world_x, world_y = latlon_to_world(latitude, longitude, self.zoom)
        return world_x - left, world_y - top
def _draw_range_rings(self, left, top):
    import math

    cx, cy = self._screen_position(
        config.HOME_LAT,
        config.HOME_LON,
        left,
        top,
    )

    # Pixels per nautical mile at the current latitude/zoom
    world_x1, _ = latlon_to_world(config.HOME_LAT, config.HOME_LON, self.zoom)
    world_x2, _ = latlon_to_world(
        config.HOME_LAT,
        config.HOME_LON + (1 / (60 * math.cos(math.radians(config.HOME_LAT)))),
        self.zoom,
    )

    pixels_per_nm = abs(world_x2 - world_x1)

    rings = [10, 25, 50, 100]

    for nm in rings:
        radius = nm * pixels_per_nm

        self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline="#2d6b86",
            width=1,
        )

        self.canvas.create_text(
            cx,
            cy - radius - 8,
            text=f"{nm} nm",
            fill="#5fc9ff",
            font=("DejaVu Sans", 8, "bold"),
        )
    def _draw_home(self, left, top):
        x, y = self._screen_position(config.HOME_LAT, config.HOME_LON, left, top)
        self.canvas.create_oval(x - 7, y - 7, x + 7, y + 7,
                                fill=config.ACCENT, outline="white", width=2)
        self.canvas.create_text(x, y + 16, text="HOME", fill="white",
                                font=("DejaVu Sans", 10, "bold"))

    def _draw_aircraft(self, left, top):
        try:
            aircraft_list = [a for a in load_aircraft() if a.has_position]
        except Exception:
            aircraft_list = []

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        visible = 0
        selected = None
        for aircraft in aircraft_list:
            x, y = self._screen_position(aircraft.latitude, aircraft.longitude, left, top)
            if x < -40 or y < -40 or x > width + 40 or y > height + 40:
                continue
            visible += 1
            is_selected = aircraft.hex == self.selected_hex
            squawk = str(aircraft.squawk or "")
            if squawk in ("7500", "7600", "7700"):
                colour = "#ff3030"
            elif is_selected:
                colour = "#ffb000"
            else:
                colour = "#00eaff"
            points = self._aircraft_shape(x, y, aircraft.heading or 0, 34 if is_selected else 28)
            self.canvas.create_polygon(points, fill=colour, outline="black", width=3)
            label = aircraft.callsign or aircraft.hex.upper()
            self.canvas.create_text(x + 12, y - 11, text=label, anchor="w",
                                    fill="white", font=("DejaVu Sans", 10, "bold"))
            self.aircraft_hitboxes.append((x - 18, y - 18, x + 70, y + 18, aircraft.hex))
            if is_selected:
                selected = aircraft

        if selected:
            self._draw_details(selected)
        return visible

    @staticmethod
    def _aircraft_shape(x, y, heading, size):
        base = [(0, -size), (3, -2), (size, 4), (size, 7),
                (3, 5), (2, size), (0, size - 2), (-2, size),
                (-3, 5), (-size, 7), (-size, 4), (-3, -2)]
        angle = math.radians(heading)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        points = []
        for px, py in base:
            points.extend((x + px * cos_a - py * sin_a,
                           y + px * sin_a + py * cos_a))
        return points

    @staticmethod
    def _altitude_colour(altitude):
        if not isinstance(altitude, (int, float)):
            return "#FFFFFF"
        if altitude < 5000:
            return "#59FF6A"
        if altitude < 15000:
            return "#00E5FF"
        if altitude < 30000:
            return "#FFD54F"
        return "#FF8A65"

    def _draw_details(self, aircraft):
        width = self.canvas.winfo_width()
        panel_width = 250
        x1 = width - panel_width - 8
        self.canvas.create_rectangle(x1, 8, width - 8, 111,
                                     fill="#101820", outline=config.ACCENT, width=2)
        callsign = aircraft.callsign or aircraft.hex.upper()
        altitude = f"{aircraft.altitude:,} ft" if isinstance(aircraft.altitude, (int, float)) else "--"
        speed = f"{aircraft.speed:.0f} kt" if isinstance(aircraft.speed, (int, float)) else "--"
        heading = f"{aircraft.heading:.0f}°" if isinstance(aircraft.heading, (int, float)) else "--"
        text = (f"{callsign}\nALT {altitude}   SPD {speed}\n"
                f"HDG {heading}   SQK {aircraft.squawk or '--'}\nHEX {aircraft.hex.upper()}")
        self.canvas.create_text(x1 + 10, 16, text=text, anchor="nw",
                                fill="white", font=("DejaVu Sans", 10, "bold"),
                                justify="left")

    def _draw_attribution(self, width, height):
        self.canvas.create_rectangle(width - 170, height - 21, width, height,
                                     fill="#101820", outline="")
        self.canvas.create_text(width - 6, height - 10,
                                text="© OpenStreetMap contributors",
                                anchor="e", fill="#D0D7DE",
                                font=("DejaVu Sans", 7))

    def _refresh_aircraft(self):
        if self.winfo_ismapped():
            self.redraw()
        self.after(config.REFRESH_MS, self._refresh_aircraft)

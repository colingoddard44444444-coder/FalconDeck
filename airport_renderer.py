from airports import AIRPORTS


def draw_airports(canvas, screen_position, zoom):
    width = canvas.winfo_width()
    height = canvas.winfo_height()

    for airport in AIRPORTS:

        # Hide regional airports until zoomed in
        if airport["size"] == "regional" and zoom < 10:
            continue

        x, y = screen_position(
            airport["lat"],
            airport["lon"]
        )

        if not (-20 <= x <= width + 20 and -20 <= y <= height + 20):
            continue

        # Airport symbol
        canvas.create_polygon(
            x, y - 6,
            x + 6, y,
            x, y + 6,
            x - 6, y,
            fill="#00ff66",
            outline="white",
            width=2,
        )

        canvas.create_text(
            x,
            y - 12,
            text=airport["icao"],
            fill="#00ff66",
            font=("DejaVu Sans", 9, "bold"),
        )

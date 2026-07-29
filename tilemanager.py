import os
import queue
import threading
import urllib.request


class TileManager:
    """Download OpenStreetMap PNG tiles in the background and cache them."""

    TILE_SIZE = 256
    URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

    def __init__(self, cache_dir, on_tile_ready):
        self.cache_dir = os.path.expanduser(cache_dir)
        self.on_tile_ready = on_tile_ready
        self.requests = queue.Queue()
        self.pending = set()
        self.running = True
        os.makedirs(self.cache_dir, exist_ok=True)
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

    def tile_path(self, z, x, y):
        return os.path.join(self.cache_dir, str(z), str(x), f"{y}.png")

    def request(self, z, x, y):
        max_tile = 1 << z
        if y < 0 or y >= max_tile:
            return None
        x %= max_tile
        path = self.tile_path(z, x, y)
        if os.path.exists(path) and os.path.getsize(path) > 100:
            return path
        key = (z, x, y)
        if key not in self.pending:
            self.pending.add(key)
            self.requests.put(key)
        return None

    def stop(self):
        self.running = False
        self.requests.put(None)

    def _worker(self):
        while self.running:
            item = self.requests.get()
            if item is None:
                return
            z, x, y = item
            path = self.tile_path(z, x, y)
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                req = urllib.request.Request(
                    self.URL.format(z=z, x=x, y=y),
                    headers={
                        "User-Agent": "FalconDeck/1.1 Raspberry-Pi ADS-B moving map"
                    },
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = response.read()
                if data.startswith(b"\x89PNG"):
                    temp_path = path + ".part"
                    with open(temp_path, "wb") as output:
                        output.write(data)
                    os.replace(temp_path, path)
                    self.on_tile_ready(z, x, y, path)
            except Exception:
                pass
            finally:
                self.pending.discard((z, x, y))

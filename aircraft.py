from dataclasses import dataclass


@dataclass
class Aircraft:
    hex: str
    callsign: str = ""
    latitude: float | None = None
    longitude: float | None = None
    altitude: int | None = None
    speed: float | None = None
    heading: float | None = None
    squawk: str = ""
    aircraft_type: str = ""
    registration: str = ""

    @property
    def has_position(self):
        return (
            self.latitude is not None
            and self.longitude is not None
        )

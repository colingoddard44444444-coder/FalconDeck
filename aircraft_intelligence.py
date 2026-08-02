from dataclasses import dataclass
from typing import Any, Optional


EMERGENCY_SQUAWKS = {
    "7500": "UNLAWFUL INTERFERENCE",
    "7600": "RADIO FAILURE",
    "7700": "GENERAL EMERGENCY",
}


@dataclass
class AircraftInsight:
    aircraft: Any
    identity: str
    hex_code: str
    altitude_ft: Optional[float]
    speed_kt: Optional[float]
    heading_deg: Optional[float]
    vertical_rate_fpm: Optional[float]
    distance_nm: Optional[float]
    bearing_deg: Optional[float]
    flight_phase: str
    priority: int
    priority_reason: str
    airport_icao: Optional[str]
    airport_name: Optional[str]
    airport_distance_nm: Optional[float]
    radio_service: Optional[str]
    radio_frequency: Optional[float]
    squawk: Optional[str]

    @property
    def is_emergency(self):
        return self.squawk in EMERGENCY_SQUAWKS

    @property
    def radio_text(self):
        if (
            self.radio_service is None
            or self.radio_frequency is None
        ):
            return "NO RADIO SUGGESTION"

        return (
            f"{self.radio_service} "
            f"{self.radio_frequency:.3f} MHz"
        )


class AircraftIntelligence:
    def __init__(
        self,
        home_lat,
        home_lon,
        distance_function,
        bearing_function,
        airport_value_function,
        nearest_airport_function,
        airport_frequencies_function,
    ):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.distance_nm = distance_function
        self.bearing_degrees = bearing_function
        self.airport_value = airport_value_function
        self.nearest_airport = nearest_airport_function
        self.airport_frequencies = airport_frequencies_function

    @staticmethod
    def number(value):
        return value if isinstance(value, (int, float)) else None

    @staticmethod
    def identity(aircraft):
        return (
            getattr(aircraft, "callsign", None)
            or getattr(aircraft, "registration", None)
            or str(
                getattr(aircraft, "hex", "UNKNOWN")
            ).upper()
        )

    @staticmethod
    def estimate_flight_phase(
        altitude,
        speed,
        vertical_rate,
        airport_distance,
    ):
        if speed is not None and speed < 45:
            return "TAXI / GROUND"

        if altitude is not None and altitude < 1500:
            if vertical_rate is not None and vertical_rate > 500:
                return "INITIAL CLIMB"

            if (
                airport_distance is not None
                and airport_distance < 4
                and vertical_rate is not None
                and vertical_rate < -250
            ):
                return "FINAL APPROACH"

            if airport_distance is not None and airport_distance < 6:
                return "AIRPORT CIRCUIT"

        if altitude is not None and altitude < 12000:
            if vertical_rate is not None and vertical_rate > 400:
                return "CLIMBING"

            if vertical_rate is not None and vertical_rate < -400:
                if (
                    airport_distance is not None
                    and airport_distance < 20
                ):
                    return "APPROACH"

                return "DESCENDING"

            return "LEVEL FLIGHT"

        if altitude is not None and altitude >= 12000:
            if vertical_rate is not None and vertical_rate > 500:
                return "CLIMBING"

            if vertical_rate is not None and vertical_rate < -500:
                return "DESCENDING"

            return "CRUISE"

        return "UNKNOWN"

    @staticmethod
    def priority_for(
        squawk,
        altitude,
        distance,
        flight_phase,
    ):
        if squawk in EMERGENCY_SQUAWKS:
            return 100, f"EMERGENCY SQUAWK {squawk}"

        if flight_phase == "FINAL APPROACH":
            return 75, "FINAL APPROACH"

        if altitude is not None and altitude <= 2000:
            return 65, "LOW ALTITUDE"

        if distance is not None and distance <= 5:
            return 55, "VERY CLOSE"

        if flight_phase == "APPROACH":
            return 45, "APPROACH"

        return 20, "NORMAL TRAFFIC"

    def suggest_frequency(
        self,
        airport,
        altitude,
        vertical_rate,
    ):
        if airport is None:
            return None, None

        icao = self.airport_value(
            airport,
            "icao",
            "ident",
            "code",
        )

        frequencies = self.airport_frequencies(icao)

        if not frequencies:
            return None, None

        available = {
            str(service).upper(): frequency
            for service, frequency in frequencies
        }

        if altitude is None:
            preferred = ("APPROACH", "TOWER", "GROUND", "ATIS")
        elif altitude <= 1500:
            preferred = ("GROUND", "TOWER", "APPROACH", "ATIS")
        elif altitude <= 3500:
            preferred = ("TOWER", "APPROACH", "GROUND", "ATIS")
        else:
            preferred = ("APPROACH", "TOWER", "ATIS", "GROUND")

        if (
            vertical_rate is not None
            and vertical_rate < -200
            and altitude is not None
            and altitude <= 12000
        ):
            preferred = ("APPROACH", "TOWER", "ATIS", "GROUND")

        for service in preferred:
            if service in available:
                return service, available[service]

        return frequencies[0]

    def analyse(self, aircraft):
        latitude = self.number(
            getattr(aircraft, "latitude", None)
        )
        longitude = self.number(
            getattr(aircraft, "longitude", None)
        )
        altitude = self.number(
            getattr(aircraft, "altitude", None)
        )
        speed = self.number(
            getattr(aircraft, "speed", None)
        )
        heading = self.number(
            getattr(aircraft, "heading", None)
        )
        vertical_rate = self.number(
            getattr(aircraft, "vertical_rate", None)
        )

        distance = None
        bearing = None
        airport = None
        airport_distance = None

        if latitude is not None and longitude is not None:
            distance = self.distance_nm(
                self.home_lat,
                self.home_lon,
                latitude,
                longitude,
            )

            bearing = self.bearing_degrees(
                self.home_lat,
                self.home_lon,
                latitude,
                longitude,
            )

            airport, airport_distance = self.nearest_airport(
                latitude,
                longitude,
            )

        flight_phase = self.estimate_flight_phase(
            altitude,
            speed,
            vertical_rate,
            airport_distance,
        )

        squawk_value = getattr(aircraft, "squawk", None)
        squawk = (
            str(squawk_value).strip()
            if squawk_value not in (None, "")
            else None
        )

        priority, priority_reason = self.priority_for(
            squawk,
            altitude,
            distance,
            flight_phase,
        )

        service, frequency = self.suggest_frequency(
            airport,
            altitude,
            vertical_rate,
        )

        airport_icao = None
        airport_name = None

        if airport is not None:
            airport_icao = self.airport_value(
                airport,
                "icao",
                "ident",
                "code",
            )
            airport_name = self.airport_value(
                airport,
                "name",
                "airport",
                "title",
            )

        return AircraftInsight(
            aircraft=aircraft,
            identity=self.identity(aircraft),
            hex_code=str(
                getattr(aircraft, "hex", "")
            ).upper(),
            altitude_ft=altitude,
            speed_kt=speed,
            heading_deg=heading,
            vertical_rate_fpm=vertical_rate,
            distance_nm=distance,
            bearing_deg=bearing,
            flight_phase=flight_phase,
            priority=priority,
            priority_reason=priority_reason,
            airport_icao=airport_icao,
            airport_name=airport_name,
            airport_distance_nm=airport_distance,
            radio_service=service,
            radio_frequency=frequency,
            squawk=squawk,
        )

    def choose_spotlight(self, aircraft_list):
        insights = [
            self.analyse(aircraft)
            for aircraft in aircraft_list
        ]

        if not insights:
            return None

        insights.sort(
            key=lambda insight: (
                insight.priority,
                -(
                    insight.distance_nm
                    if insight.distance_nm is not None
                    else 99999
                ),
            ),
            reverse=True,
        )

        return insights[0]

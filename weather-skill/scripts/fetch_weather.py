#!/usr/bin/env python3
"""Fetch daily weather from open-meteo.com and format a compact report."""

import argparse
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

API = "https://api.open-meteo.com/v1/forecast"
WEATHER_LABELS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class DailyForecast(BaseModel):
    date: str
    temp_max: Annotated[float, Field(default=0.0)]
    temp_min: Annotated[float, Field(default=0.0)]
    rain_chance: Annotated[int, Field(default=0)]
    weather_code: Annotated[int, Field(default=-1, ge=-1)]
    wind_speed: Annotated[float, Field(default=0.0)]
    humidity: Annotated[float, Field(default=0.0)]

    @property
    def label(self) -> str:
        return WEATHER_LABELS.get(self.weather_code, "Unknown")

    @property
    def short_date(self) -> str:
        parsed = datetime.strptime(self.date, "%Y-%m-%d").date()
        return f"{parsed:%a} {parsed:%d/%m}"


class DailySeries(BaseModel):
    time: Annotated[list[str], Field(default_factory=list)]
    temperature_2m_max: Annotated[list[float] | None, Field(default=None)]
    temperature_2m_min: Annotated[list[float] | None, Field(default=None)]
    precipitation_probability_max: Annotated[list[float] | None, Field(default=None)]
    weather_code: Annotated[list[float] | None, Field(default=None)]
    wind_speed_10m_max: Annotated[list[float] | None, Field(default=None)]
    relative_humidity_2m_mean: Annotated[list[float] | None, Field(default=None)]


class WeatherReport(BaseModel):
    latitude: Annotated[float, Field(default=0.0)]
    longitude: Annotated[float, Field(default=0.0)]
    timezone_abbreviation: Annotated[str, Field(default="")]
    daily: Annotated[DailySeries, Field(default_factory=DailySeries)]

    @property
    def timezone(self) -> str:
        return self.timezone_abbreviation

    @property
    def heading(self) -> str:
        return f"{self.latitude:.3f},{self.longitude:.3f}"

    @property
    def forecasts(self) -> list[DailyForecast]:
        series = self.daily
        lengths = {len(getattr(series, field) or []) for field in DailySeries.model_fields if field != "time"}
        longest = max(lengths | {len(series.time)})

        def read(series: list[float] | None, index: int, default: float) -> float:
            return series[index] if series and index < len(series) else default

        return [
            DailyForecast(
                date=series.time[index] if index < len(series.time) else "",
                temp_max=read(series.temperature_2m_max, index, 0.0),
                temp_min=read(series.temperature_2m_min, index, 0.0),
                rain_chance=int(read(series.precipitation_probability_max, index, 0.0)),
                weather_code=int(read(series.weather_code, index, -1.0)),
                wind_speed=read(series.wind_speed_10m_max, index, 0.0),
                humidity=read(series.relative_humidity_2m_mean, index, 0.0),
            )
            for index in range(longest)
        ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--lon", required=True, type=float)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--label", default=None)
    return parser.parse_args()


def fetch(lat: float, lon: float, days: int) -> WeatherReport:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "weather_code",
                "wind_speed_10m_max",
                "relative_humidity_2m_mean",
            ]
        ),
        "timezone": "auto",
        "forecast_days": days,
    }
    url = f"{API}?{urllib.parse.urlencode(query=params)}"
    with urllib.request.urlopen(url=url, timeout=30) as response:
        return WeatherReport.model_validate_json(response.read())


def format_report(report: WeatherReport, label: str | None) -> str:
    heading = label or report.heading
    lines = [f"Weather for {heading} ({report.timezone}):", ""]
    for forecast in report.forecasts:
        lines.append(
            f"{forecast.short_date}: {round(forecast.temp_max)}°C / {round(forecast.temp_min)}°C, "
            + f"rain {forecast.rain_chance}%, wind {round(forecast.wind_speed)} km/h, "
            + f"humidity {round(forecast.humidity)}%, {forecast.label}"
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    report = fetch(lat=args.lat, lon=args.lon, days=args.days)
    print(format_report(report=report, label=args.label))


if __name__ == "__main__":
    main()


from __future__ import annotations

from abc import ABC, abstractmethod

from .models import GeoPoint, GeocodedLocation, MatrixResult, RouteResult


class GeocodingProvider(ABC):

    name = "unknown"

    @abstractmethod
    def geocode(self, query: str) -> GeocodedLocation:
        raise NotImplementedError

    @abstractmethod
    def reverse_geocode(self, point: GeoPoint) -> GeocodedLocation:
        raise NotImplementedError


class RoutingProvider(ABC):

    name = "unknown"

    @abstractmethod
    def route(self, points: list[GeoPoint]) -> RouteResult:
        raise NotImplementedError

    @abstractmethod
    def matrix(self, points: list[GeoPoint]) -> MatrixResult:
        raise NotImplementedError

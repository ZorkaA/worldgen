"""Pydantic schemas for terrain, zones, buildings, roads, and world manifest."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    size: Optional[List[float]] = None
    dimensions: Optional[List[float]] = None
    center: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    min: Optional[List[float]] = None
    max: Optional[List[float]] = None
    radius: Optional[float] = None
    ground_level_offset: Optional[float] = None


class BuildingPlacement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    zone_id: str
    prefab_name: str
    category: Optional[str] = "building"
    position: List[float]
    rotation: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_euler: Optional[List[float]] = None
    rotation_quaternion: Optional[List[float]] = None
    scale: List[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])
    bounding_box: BoundingBox
    faction: Optional[str] = "A"
    destruction: Optional[Union[str, int]] = "01"


class Zone(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    type: Optional[str] = "military_base"
    faction: str = "A"
    destruction: Union[str, int] = "01"
    density: str = "medium"
    center: List[float]
    radius: float
    footprint_points: Optional[List[List[float]]] = None
    footprint_polygon: Optional[List[List[float]]] = None


class RoadSegment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_zone: str
    to_zone: str
    width: float = 6.0
    waypoints: List[List[float]]


class TerrainManifest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resolution: Union[int, List[int]] = 513
    world_size: List[float] = Field(default_factory=lambda: [1000.0, 150.0, 1000.0])
    heightmap: Optional[List[List[float]]] = None
    cell_size: Optional[float] = None
    height_scale: Optional[float] = None
    heightmap_encoding: Optional[str] = "float32_array"
    heightmap_url: Optional[str] = None
    heightmap_data: Optional[List[float]] = None


class ManifestMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version: str = "1.0.0"
    seed: int
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    generator: str = "FastAPI Procedural WorldGen v1.0"
    world_size_meters: Optional[float] = 1000.0
    max_elevation_meters: Optional[float] = 150.0
    zone_count: Optional[int] = 0
    building_count: Optional[int] = 0
    road_segment_count: Optional[int] = 0


class WorldManifest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_url: Optional[str] = Field(
        default="https://json-schema.org/draft/2020-12/schema",
        alias="$schema",
    )
    metadata: ManifestMetadata
    terrain: TerrainManifest
    zones: List[Zone]
    buildings: List[BuildingPlacement]
    roads: List[RoadSegment]


# Configuration models for Generation
class TerrainConfig(BaseModel):
    resolution: int = Field(513, ge=33, le=2049)
    scale: float = Field(256.0, ge=16.0, le=2048.0)
    octaves: int = Field(6, ge=1, le=12)
    persistence: float = Field(0.5, ge=0.05, le=0.95)
    lacunarity: float = Field(2.0, ge=1.1, le=4.0)
    domain_warp_strength: float = Field(35.0, ge=0.0, le=200.0)
    erosion_droplets: int = Field(50000, ge=0, le=500000)
    height_scale: float = Field(100.0, ge=5.0, le=500.0)
    world_size: List[float] = Field(default_factory=lambda: [1000.0, 150.0, 1000.0])
    power_redistribution: float = Field(1.3, ge=0.5, le=3.0)


class ZoneConfig(BaseModel):
    min_zone_distance: float = Field(120.0, ge=30.0, le=600.0)
    zone_count_target: Optional[int] = Field(None, ge=1, le=50)
    default_factions: List[str] = Field(default_factory=lambda: ["A", "B", "C"])
    max_destruction: int = Field(4, ge=1, le=4)
    min_radius: float = Field(35.0, ge=15.0, le=100.0)
    max_radius: float = Field(75.0, ge=30.0, le=150.0)


class GenerateWorldRequest(BaseModel):
    seed: Optional[int] = None
    terrain: Optional[TerrainConfig] = None
    zones: Optional[ZoneConfig] = None


class GenerateWorldResponse(BaseModel):
    success: bool
    seed: int
    execution_time_seconds: float
    summary: Dict[str, Any]
    manifest: WorldManifest


class HealthStatus(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    generator: str = "FastAPI Procedural WorldGen v1.0"
    catalog_available: bool = False
    catalog_asset_count: int = 0

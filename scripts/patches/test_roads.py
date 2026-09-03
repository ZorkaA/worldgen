import numpy as np
from backend.app.generator.roads import _find_slope_aware_astar_path
from backend.app.core.schemas import TerrainConfig

hmap = np.zeros((129, 129))
config = TerrainConfig(world_size=[2000.0, 1000.0, 2000.0])
path = _find_slope_aware_astar_path(hmap, (100.0, 100.0), (1900.0, 1900.0), config)
print("Path points:", len(path))

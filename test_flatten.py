import numpy as np
from app.generator.zones import flatten_zone_footprints
from app.core.schemas import Zone, TerrainConfig

hmap = np.zeros((20, 20))
for i in range(20): hmap[i, :] = i * 2.0

zone = Zone(id="z1", name="z1", zone_type="base", center=[100.0, 100.0, 100.0], radius=40.0, faction="A", destruction=1, density=1.0)
config = TerrainConfig(world_size=[200.0, 200.0, 200.0], resolution=20)

flat = flatten_zone_footprints(hmap, [zone], None, config)

print("Original:")
print(np.round(hmap[5:15, 5:15], 1))
print("Flat:")
print(np.round(flat[5:15, 5:15], 1))

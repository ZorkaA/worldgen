import numpy as np

D = np.array([0, 10, 20, 30, 40, 50, 60])

max_slope = 0.25

curvature_old = 0.003
drop_old = D * max_slope + (D ** 2) * curvature_old

curvature_new = 0.02
drop_new = D * max_slope + (D ** 2) * curvature_new

print("D:       ", D)
print("Old drop:", drop_old)
print("New drop:", drop_new)

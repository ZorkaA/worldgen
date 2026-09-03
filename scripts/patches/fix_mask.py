with open("backend/app/generator/zones.py", "r") as f:
    content = f.read()

replacement = """    # Create an edge mask: 1.0 near edge (D < 10), 0.0 far away
    # D is distance outside the zone (0 inside)
    edge_mask_out = np.exp(-(D ** 2) / (2.0 * 8.0 ** 2))
    
    # D_in is distance inside the zone (0 outside)
    D_in = scipy.ndimage.distance_transform_edt(is_flat_mask, sampling=[cell_l, cell_w])
    edge_mask_in = np.exp(-(D_in ** 2) / (2.0 * 6.0 ** 2))
    
    # We only want edge_mask_in to apply INSIDE the zone, and edge_mask_out OUTSIDE.
    # Since D=0 inside, edge_mask_out=1 inside. Since D_in=0 outside, edge_mask_in=1 outside.
    # We mask them so they only apply to their respective domains!
    edge_mask = np.where(is_flat_mask, edge_mask_in, edge_mask_out)
    
    final_terrain = flattened * (1.0 - edge_mask) + smoothed * edge_mask"""

content = content.replace("""    # Let's create an edge mask: 1.0 near edge (D < 10), 0.0 far away
    edge_mask = np.exp(-(D ** 2) / (2.0 * 8.0 ** 2)) 
    # Add inner edge smoothing too (inside the zone, D is 0, so edge_mask is 1.0)
    # We need inner distance
    D_in = scipy.ndimage.distance_transform_edt(is_flat_mask, sampling=[cell_l, cell_w])
    inner_edge_mask = np.exp(-(D_in ** 2) / (2.0 * 6.0 ** 2))
    
    total_edge_mask = np.maximum(edge_mask, inner_edge_mask)
    
    final_terrain = flattened * (1.0 - total_edge_mask) + smoothed * total_edge_mask""", replacement)

with open("backend/app/generator/zones.py", "w") as f:
    f.write(content)
print("Fixed edge mask logic")

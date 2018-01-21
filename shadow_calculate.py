import numpy as np


def is_shadowed(probe_building, main_building):

    probe_x, probe_y = probe_building.centroid
    main_x, main_y = main_building.centroid
    main_height =  main_building.max_height
    probe_height = probe_building.max_height
    if probe_y < main_y: return False

    distance_x = abs(probe_x - main_x)
    distance_y = abs(probe_y - main_y)
    d = np.array([distance_x,distance_y])
    distance = np.linalg.norm(d)
    if distance > main_height*5:return False

    shadow_height = main_height - distance/5
    if probe_height> shadow_height:return False


    return True


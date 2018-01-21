from pyproj import Proj

points = [[ 296784.077, 5041677.421],
 [ 296784.944, 5041662.611],
 [ 296803.522, 5041663.699],
 [ 296802.655, 5041678.509]]


projector = Proj(init='epsg:2950')
# x=296444.40
# y=5041273.03
# x=296523.16
# y=5041350.38

for p in points:
    x, y = p
    lon,lat = projector(x,y,inverse=True)
    print('{:9.9f},{:9.9f}'.format(lat,lon))


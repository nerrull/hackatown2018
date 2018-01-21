#!/usr/bin/python
# -*- coding: utf-8 -*-

# The MIT License (MIT)

# This code is part of the Solar3Dcity package

# Copyright (c) 2015
# Filip Biljecki
# Delft University of Technology
# fbiljecki@gmail.com

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import polygon3dmodule
import markup3dmodule
from lxml import etree
import irr
import argparse
import glob
import os
import pickle
import numpy as np
from os.path import join, exists
import json
from pyproj import Proj
from modelExtraction import Building
from os import mkdir
from shadow_calculate import is_shadowed
from calculateCost import calculate_max_number_of_panels

def remove_in_list(my_arr, list_arrays):
    for index, element in enumerate(list_arrays):
        if np.array_equal(np.sort(element.flat), np.sort(my_arr.flat)):
            break
    list_arrays.pop(index)
    return list_arrays


def getNextVertex(vert, edges, vert_list):
    if len(edges) == 0:
        return vert_list
    for edge in edges:
        if np.array_equal(edge[0], vert):
            break
    if not np.array_equal(edge[0]       , vert):
        print "fuck me"
    edges = remove_in_list(edge, edges)
    vert_list.append(edge[1])
    return getNextVertex(edge[1], edges, vert_list)

def get_ordered_vertex( edge_list):
    ordered_verts=  []
    v0 = edge_list[0][0]
    v1= edge_list[0][1]
    edge_list.pop(0)
    ordered_verts.append(v0)
    ordered_verts.append(v1)
    return getNextVertex(v1, edge_list, ordered_verts)

#-- Name spaces
ns_citygml = "http://www.opengis.net/citygml/1.0"

ns_gml = "http://www.opengis.net/gml"
ns_bldg = "http://www.opengis.net/citygml/building/1.0"
ns_xsi = "http://www.w3.org/2001/XMLSchema-instance"
ns_xAL = "urn:oasis:names:tc:ciq:xsdschema:xAL:1.0"
ns_xlink = "http://www.w3.org/1999/xlink"
ns_dem = "http://www.opengis.net/citygml/relief/1.0"

nsmap = {
    None : ns_citygml,
    'gml': ns_gml,
    'bldg': ns_bldg,
    'xsi' : ns_xsi,
    'xAL' : ns_xAL,
    'xlink' : ns_xlink,
    'dem' : ns_dem
}



#-- ARGUMENTS
# -i -- input directory (it will read ALL CityGML files in a directory)
# -o -- output directory (it will output the enriched CityGMLs in that directory with the naming convention Delft.gml becomes Delft-solar.gml)
# -f -- factors (precomputed tilt-orientation-factors)
PARSER = argparse.ArgumentParser(description='Calculate the yearly solar irradiation of roof surfaces.')
PARSER.add_argument('-i', '--directory',
    help='Directory containing CityGML file(s).', required=True)
PARSER.add_argument('-o', '--results',
    help='Directory where the enriched "solar" CityGML file(s) should be written.', required=True)
PARSER.add_argument('-f', '--factors',
    help='Load the TOF if previously precomputed', required=False)
ARGS = vars(PARSER.parse_args())
DIRECTORY = ARGS['directory']
RESULT = ARGS['results']
FACTORS = ARGS['factors']
#-- Load the pre-computed dictionary
if not FACTORS:
    loadDict = False
else:
    loadDict = True





print "I am Solar3Dcity. Let me search for your CityGML files..."

#-- Find all CityGML files in the directory
os.chdir(DIRECTORY)
db_path = join(DIRECTORY, "db")
projector = Proj(init='epsg:2950')
buildinginstances = []
max_score = 0

for f in glob.glob("*.gml"):
    FILENAME = f[:f.rfind('.')]
    FULLPATH = DIRECTORY + f

    CITYGML = etree.parse(FULLPATH)
    root = CITYGML.getroot()
    cityObjects = []
    buildings = []

    listofxmlroofsurfaces = []
    roofsurfacedata = {}

    #-- Find all instances of cityObjectMember and put them in a list
    for obj in root.getiterator('{%s}cityObjectMember'% ns_citygml):
        cityObjects.append(obj)

    print FILENAME
    print "\tThere are", len(cityObjects), "cityObject(s) in this CityGML file"

    for cityObject in cityObjects:
        for child in cityObject.getchildren():
            if child.tag == '{%s}Building' %ns_bldg:
                buildings.append(child)

    #-- Store the buildings as classes
    numbuildings = len(buildings)
    buildings_dict = {}
    for i,b in enumerate(buildings):
        print("{}/{}".format(i,numbuildings))
        id = b.attrib['{%s}id' %ns_gml]
        building = Building(b, id)
        buildinginstances.append(building)

        usable_area = building.usable_roof_area
        quality = building.quality
        ease = building.ease_of_installation
        area = building.roof_area
        if area >0.:
            score = quality * usable_area/area * ease
        else: score = 0.0
        max_score = max(score, max_score)

number_of_buildings = len(buildinginstances)
buildinginstances = sorted(buildinginstances)
numshadowed = 0
print(max_score)
for index, building in enumerate(buildinginstances):
    print("{}/{}".format(index, number_of_buildings))

    if building.mutiple_buildings == True:
        print("Skipped")
        continue

    other_building_list = buildinginstances[:]
    other_building_list.pop(index)
    for other in other_building_list:
        if other.shadowed:
            continue
        other.shadowed = is_shadowed(other, building)

    bounds = building.border_poly
    centroid = building.centroid
    height = building.max_height
    complexity = building.roof_complexity
    shadowed = building.shadowed
    area = building.roof_area
    usable_area = building.usable_roof_area
    quality = building.quality
    ease = building.ease_of_installation
    score = quality * usable_area/area * ease/max_score
    numpanels = calculate_max_number_of_panels(usable_area)

    if shadowed:
        numshadowed += 1
    coords = []
    for b in bounds:
        x, y = projector(b[0], b[1], inverse=True)
        coords.append([y, x])

    x, y = projector(centroid[0], centroid[1], inverse=True)
    center = [y, x]
    id = building.id
    buildings_dict[id] = {"height": height,
                          "centroid_meters": centroid,
                          "centroid_coordinates": center,
                          "bounds_meters": bounds.tolist(),
                          "bounds_coordinates": coords,
                          "complexity": complexity,
                          "shadowed": shadowed,
                          "total_area": area,
                          "usable_area": usable_area,
                          "quality": quality,
                          "ease_of_installation": ease,
                          "score": score,
                          "max_panels": numpanels}
    print("Height: {} \nCentroid: {} \nShadowed {}\nArea {} \nUsable area {} \nQuality {}\nEase {} \nScore {}\n".format(height,
                                                                                                              centroid,
                                                                                                              shadowed,
                                                                                                              area,
                                                                                                              usable_area,
                                                                                                              quality,
                                                                                                              ease, score))

print ("{}/{} shadowed".format(numshadowed, len(buildinginstances)))
json_string = json.dumps(buildings_dict)
if not exists(db_path):
    mkdir(db_path)
outfile = join(db_path, FILENAME + ".json")
with open(outfile, 'w') as out:
    json.dump(buildings_dict, out)


print "All done."
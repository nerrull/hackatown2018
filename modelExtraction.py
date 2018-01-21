from scipy import interpolate
import math
import collections
from scipy.spatial import ConvexHull
from scipy.sparse import csgraph
import networkx as nx
import polygon3dmodule
import markup3dmodule
from lxml import etree
import irr
import numpy as np

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

def squareVerts(a,t,res):
    """Get the vertices of the interpolation square."""
    invRes = 1/res
    aB = math.trunc(a*invRes)/invRes
    aT = math.ceil(a*invRes)/invRes
    if aT == aB:
        aT += res#1.0
    tB = math.trunc(t*invRes)/invRes
    tT = math.ceil(t*invRes)/invRes
    if tT == tB:
        tT += res#1.0
    return [[aB, aT], [tB, tT]]


def bilinear_interpolation(x, y, points):
    # Function taken from http://stackoverflow.com/a/8662355/4443114
    '''Interpolate (x,y) from values associated with four points.

    The four points are a list of four triplets:  (x, y, value).
    The four points can be in any order.  They should form a rectangle.

        >>> bilinear_interpolation(12, 5.5,
        ...                        [(10, 4, 100),
        ...                         (20, 4, 200),
        ...                         (10, 6, 150),
        ...                         (20, 6, 300)])
        165.0

    '''
    # See formula at:  http://en.wikipedia.org/wiki/Bilinear_interpolation

    points = sorted(points)               # order points by x, then by y
    (x1, y1, q11), (_x1, y2, q12), (x2, _y1, q21), (_x2, _y2, q22) = points

    if x1 != _x1 or x2 != _x2 or y1 != _y1 or y2 != _y2:
        raise ValueError('points do not form a rectangle')
    if not x1 <= x <= x2 or not y1 <= y <= y2:
        raise ValueError('(x, y) not within the rectangle')

    return (q11 * (x2 - x) * (y2 - y) +
            q21 * (x - x1) * (y2 - y) +
            q12 * (x2 - x) * (y - y1) +
            q22 * (x - x1) * (y - y1)
           ) / ((x2 - x1) * (y2 - y1) + 0.0)





class Building(object):
    def __init__(self, xml, id):
        #-- ID of the building
        self.id = id
        #-- XML tree of the building
        self.xml = xml
        self.mutiple_buildings = False
        self.shadowed = False
        #-- Data for each roof surface required for the computation of the solar stuff
        self.roofdata = {}
        #-- List of IDs of openings, not to mess with usable roof surfaces
        self.listOfOpenings = []
        #-- Compute the total areas of surfaces per semantic class (not really required; reserved for future use)
        #-- RoofSurface
        self.roof_area = 0.0
        self.usable_roof_area = 0.0
        self.quality = 0.0
        self.ease_of_installation = 0.0
        self.getRelevantStatistics()


    def __lt__(self, other):
        self.max_height > other.max_height

    def getRelevantStatistics(self):
        self.get_roof_bounds()
        if not self.mutiple_buildings:
            self.roof_area, self.usable_roof_area, self.quality, self.ease_of_installation= self.roofarea()

    def get_roof_bounds(self):
        self.roofs = []
        roofsurfaces = []
        all_2d_vertices = []
        maxHeight = 0
        for child in self.xml.getiterator():
            if child.tag == '{%s}RoofSurface' % ns_bldg:
                self.roofs.append(child)

        for surface in self.roofs:
            for w in surface.findall('.//{%s}Polygon' % ns_gml):
                roofsurfaces.append(w)

        edges = []

        for surface in roofsurfaces:
            e, i = markup3dmodule.polydecomposer(surface)
            if len(i)>0:
                print("Wtf")

            vertices = np.array(markup3dmodule.GMLpoints(e[0]))
            vertices2D = vertices[:,0:2]

            height = np.max(vertices[:,2])
            if height > maxHeight:
                maxHeight=height
            if len(vertices2D)<3:
                print "Bad paly smaller than 3"
                continue
            if len(vertices2D)>3:
                vertices2D = vertices2D[0:3]

            for vertex in vertices2D:
                all_2d_vertices.append(vertex)
            # # roofpolys.append(vertices2D)
            # # edge1 = (tuple(vertices2D[0]), tuple(vertices2D[1]))
            # # edge2 = (tuple(vertices2D[1]), tuple(vertices2D[2]))
            # # edge3 = (tuple(vertices2D[2]), tuple(vertices2D[0]))
            edge1 = np.array([vertices2D[0], vertices2D[1]])
            edge2 = np.array([vertices2D[1], vertices2D[2]])
            edge3 = np.array([vertices2D[2], vertices2D[0]])
            edges.append(edge1)
            edges.append(edge2)
            edges.append(edge3)

        unique_vertices = np.unique(all_2d_vertices,axis=0)
        num_verts = len(unique_vertices)
        connectivity_graph = np.zeros([num_verts, num_verts])

        for edge in edges:
            v1_index =np.where(np.all(unique_vertices==edge[0],axis=1))[0][0]
            v2_index =np.where(np.all(unique_vertices==edge[1],axis=1))[0][0]
            connectivity_graph[v1_index,v2_index]=1
            connectivity_graph[v2_index,v1_index]=1

        graph = nx.from_numpy_matrix(connectivity_graph)
        connections = nx.connected_components(graph)
        c = []
        for connection in connections:
            c.append(connection)
        if len(c) >1:
            print "Multiple nignogs detected"
            self.mutiple_buildings =True

        hull = ConvexHull(all_2d_vertices)

        cx = np.mean(hull.points[hull.vertices, 0])
        cy = np.mean(hull.points[hull.vertices, 1])
        self.roof_complexity =len(hull.vertices)
        self.max_height = maxHeight
        self.border_poly =  hull.points[hull.vertices]
        self.centroid = (cx,cy)


    def roofarea(self):
        """The total area of RoofSurface."""
        self.roofs = []
        self.roofsurfaces = []
        roofarea = 0.0
        total_quality =0.0
        usable_roof_area =0.0
        total_tilt =0.0
        for child in self.xml.getiterator():
            if child.tag == '{%s}RoofSurface' %ns_bldg:
                self.roofs.append(child)
        for surface in self.roofs:
            for w in surface.findall('.//{%s}Polygon' %ns_gml):
                self.roofsurfaces.append(w)
        for roofsurface in self.roofsurfaces:
            area, angles=  polygon3dmodule.getAreaAndAnglesOfGML(roofsurface, True)

            azimuth = angles [0]
            tilt = angles [1]

            if tilt>89:
                continue

            roofarea += area


            #Panels under 1 degree will be considered flat
            if tilt < 1:
                usable_roof_area +=area
                total_quality +=area
                continue

            #Viable panels are under 30 degress inclination
            if tilt<30:
                if azimuth >90 and azimuth<270:
                    weighted_tilt = tilt * area
                    total_tilt += weighted_tilt

                    usable_roof_area +=area
                    az_weight = azimuth - 180 #-90 to 90
                    az_weight = abs(az_weight/90) #-1 to 0 to 1
                    az_weight = 1-az_weight #0 to 1 to 0
                    az_weight = (az_weight +0.3)/1.3
                    total_quality +=area *az_weight


        #Get average tilt of usable roof
        if usable_roof_area >0:
            average_tilt = total_tilt/usable_roof_area
            #We only consider those between 0 and 30 so normalize to divide by 30
            average_tilt = average_tilt /30
            ease_of_installation = 1-average_tilt

            quality = total_quality/roofarea
        else  :
            ease_of_installation= 0
            quality=0
        return roofarea, usable_roof_area, quality, ease_of_installation

    def wallarea(self):
        """The total area of WallSurfaces."""
        self.walls = []
        self.wallsurfaces = []
        wallarea = 0.0
        openings = 0.0
        #-- Account for openings
        for child in self.xml.getiterator():
            if child.tag == '{%s}WallSurface' %ns_bldg:
                self.walls.append(child)
                openings += oparea(child)
        for surface in self.walls:
            for w in surface.findall('.//{%s}Polygon' %ns_gml):
                self.wallsurfaces.append(w)
        for wallsurface in self.wallsurfaces:
            wallarea += polygon3dmodule.getAreaAndAnglesOfGML(wallsurface, True)
        return wallarea - openings

    def groundarea(self):
        """The total area of GroundSurfaces."""
        self.grounds = []
        groundarea = 0.0
        for child in self.xml.getiterator():
            if child.tag == '{%s}GroundSurface' %ns_bldg:
                self.grounds.append(child)
        self.count = 0
        for groundsurface in self.grounds:
            self.count += 1
            groundarea += polygon3dmodule.getAreaAndAnglesOfGML(groundsurface, True)
        return groundarea

    def openingarea(self):
        """The total area of Openings."""
        matching = []
        self.openings = []
        openingarea = 0.0
        for child in self.xml.getiterator():
            if child.tag == '{%s}opening' %ns_bldg:
                matching.append(child)
                #-- Store the list of openings
                for o in child.findall('.//{%s}Polygon' %ns_gml):
                    self.listOfOpenings.append(o.attrib['{%s}id' %ns_gml])
        for match in matching:
            for child in match.getiterator():
                if child.tag == '{%s}surfaceMember' %ns_gml:
                    self.openings.append(child)
        self.count = 0
        for openingsurface in self.openings:
            self.count += 1
            openingarea += polygon3dmodule.getAreaAndAnglesOfGML(openingsurface, True)
        return openingarea

    def allarea(self):
        """The total area of all surfaces."""
        self.allareas = []
        allarea = 0.0
        # for child in self.xml.getiterator():
        #   if child.tag == '{%s}surfaceMember' %ns_gml:
        #       self.allareas.append(child)
        self.allareas = self.xml.findall('.//{%s}Polygon' %ns_gml)
        self.count = 0
        for poly in self.allareas:
            self.count += 1
            allarea += polygon3dmodule.getAreaAndAnglesOfGML(poly, True)
        return allarea

def oparea(xmlelement):
    """The total area of Openings in the XML tree."""
    matching = []
    openings = []
    openingarea = 0.0
    for child in xmlelement.getiterator():
        if child.tag == '{%s}opening' %ns_bldg:
            #print 'opening'
            matching.append(child)
    for match in matching:
        for child in match.getiterator():
            if child.tag == '{%s}surfaceMember' %ns_gml:
                openings.append(child)
    for openingsurface in openings:
        openingarea += polygon3dmodule.getAreaAndAnglesOfGML(openingsurface, True)
    return openingarea
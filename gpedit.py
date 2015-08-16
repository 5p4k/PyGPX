#!/usr/bin/env python
import xml.dom.minidom as DOM
import sys
import os
from elevation import GoogleElevationAPI as Elevation

API_KEY = 'YOUR_API_KEY'

def dom_track_point_to_coordinates(trkpt):
	lat = float(trkpt.getAttribute('lat'))
	lon = float(trkpt.getAttribute('lon'))
	ele = None
	elevations = trkpt.getElementsByTagName('ele')
	if len(elevations) > 0:
		if elevations[0].hasChildNodes():
			ele = float(elevations[0].firstChild.nodeValue)
	return (lat, lon, ele)

def dom_set_elevation(trkpt, elevation, dom):
	ele = None
	elevations = trkpt.getElementsByTagName('ele')
	if len(elevations) > 0:
		ele = elevations[0]
	else:
		ele = dom.createElement('ele')
		trkpt.appendChild(ele)

	while ele.hasChildNodes():
		ele.removeChild(ele.firstChild)

	ele.appendChild(dom.createTextNode('%0.2f' % elevation))

def main(filename):
	dom = DOM.parse(filename)
	points = dom.getElementsByTagName('trkpt')
	elevapi = Elevation(API_KEY)
	for trkpt in points:
		lat, lon, _ = dom_track_point_to_coordinates(trkpt)
		elevapi.add_location(lat, lon)
	result = elevapi.run()
	if not result:
		print('Error. Google API returned: %s.' % elevapi.status)
	for i in xrange(0, len(points)):
		if len(elevapi.locations[i]) < 3:
			print('Not all elevations retrieved.')
			answer = None
			while answer is None:
				answer = raw_input('Proceed anyway? [y/N] ').lower()
				if answer in ['y', 'n']:
					if answer == 'y':
						answer = True
					else:
						answer = False
				else:
					answer = None
			if answer:
				break
			else:
				return
		else:
			dom_set_elevation(points[i], elevapi.locations[i][2], dom)
	
	os.rename(filename, filename + '.bak')
	with open(filename, 'w') as writer:
		dom.writexml(writer, '', '  ', '')

if __name__ == '__main__':
	if len(sys.argv) <= 1:
		print('Usage: %s <file.gpx>' % sys.argv[0])
	else:
		main(sys.argv[1])
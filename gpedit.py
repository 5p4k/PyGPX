#!/usr/bin/env python
import xml.dom.minidom as DOM
import sys
import os
from gpx import TrackPoints
from elevation import GoogleElevationAPI as Elevation

API_KEY = 'AIzaSyDAFDq-dUpqRk9EywJVGTb5o4yXQSG7dlU'

def main(filename):
	dom = DOM.parse(filename)
	points = TrackPoints(dom)
	elevapi = Elevation(API_KEY)
	if not elevapi.run(points):
		print('Not all elevations retrieved.')
		answer = None
		while answer is None:
			answer = raw_input('Proceed anyway? [y/N] ').lower()
			if answer in ['y', 'n']:
				answer = answer == 'y'
			else:
				answer = None
		if not answer:
			return

	os.rename(filename, filename + '.bak')
	with open(filename, 'w') as writer:
		dom.writexml(writer)

if __name__ == '__main__':
	if len(sys.argv) <= 1:
		print('Usage: %s <file.gpx>' % sys.argv[0])
	else:
		main(sys.argv[1])
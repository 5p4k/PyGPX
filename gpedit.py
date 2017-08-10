#!/usr/bin/env python3
import xml.dom.minidom as DOM
import sys
import os
from gpx import TrackPoints
from elevation import GoogleElevationAPI as Elevation
import argparse

def main(elevapi, filename):
    dom = DOM.parse(filename)
    points = TrackPoints(dom)
    if not elevapi.run(points):
        print('(W) Not all elevations retrieved.')
        answer = None
        while answer is None:
            answer = input('Proceed anyway? [y/N] ').lower()
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
    parser = argparse.ArgumentParser(description='Add elevation information to a pre-existing GPX track.')
    parser.add_argument('gpx', nargs='+', help='GPX file(s) to modify (a backup will be made).')
    parser.add_argument('-k', '--key', required=True, help='Google API key.')
    args = parser.parse_args()
    elevapi = Elevation(args.key)
    for filename in args.gpx:
        print('Processing %s...' % filename)
        if not os.path.isfile(filename):
            print('(E) Not a readable file.')
        else:
            try:
                main(elevapi, filename)
            except Exception as e:
                print(e)

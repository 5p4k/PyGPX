#!/usr/bin/env python3.4
from gpx import *
import xml.dom.minidom as DOM
import sys

def main(filenames):
    # load all tracks
    tracks = []
    for filename in filenames:
        print('Loading %s...' % filename)
        try:
            dom = DOM.parse(filename)
            tracks.append(TrackPoints(dom))
        except Exception as e:
            print(str(e))
    print('Loaded %d tracks.' % len(tracks))

if __name__ == '__main__':
    main(sys.argv[1:])
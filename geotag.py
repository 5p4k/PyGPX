#!/usr/bin/env python3.4
from gpx import *
import xml.dom.minidom as DOM
import sys
import os

def main(gpxs, imgs):
    # load all tracks
    tracks = []
    for filename in gpxs:
        print('Loading %s...' % filename)
        try:
            dom = DOM.parse(filename)
            tracks.append(TrackPoints(dom))
        except Exception as e:
            print(str(e))
    print('Loaded %d tracks.' % len(tracks))



if __name__ == '__main__':
    gpx = []
    img = []
    for x in sys.argv[1:]:
        if not os.path.isfile(x):
            print('%s is not a valid file.' % x)
            continue
        if x.lower().endswith('gpx'):
            gpx.append(x)
        else:
            img.append(x)
    main(gpx, img)
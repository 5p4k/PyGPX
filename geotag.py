#!/usr/bin/env python3.4
from gpx import *
import xml.dom.minidom as DOM
import sys
import os
import gi
gi.require_version('GExiv2', '0.10')
from gi.repository import GExiv2
from elevation import GoogleElevationAPI as Elevation

API_KEY = 'AIzaSyBepE88vxFrjwZqKLl_cMAj5W01sjBnVnE'

class GooglePt(object):
    def apiformat(self):
        return '%0.6f,%0.6f' % (self.latitude, self.longitude)

    def __setattr__(self, key, value):
        if key == 'elevation':
            self._elevation = value
            self.exif.set_gps_info(self.longitude, self.latitude, self._elevation)
            print('Found altitude for %s: (%f, %f, %f)' % (os.path.basename(self.path), self.latitude, self.longitude, self._elevation))
            self.exif.save_file()
        else:
            return super(GooglePt, self).__setattr__(key, value)

    def __getattribute__(self, key):
        if key == 'elevation':
            return self._elevation
        else:
            return super(GooglePt, self).__getattribute__(key)

    def __init__(self, img, exif, lat, lon):
        self.path = img
        self.exif = exif
        self.latitude = lat
        self.longitude = lon
        self._elevation = None


def main(gpxs, imgs):
    # load all tracks
    batch = []
    tracks = []
    for filename in gpxs:
        print('Loading %s...' % filename)
        try:
            dom = DOM.parse(filename)
            tracks.append(GeotagQuery(TrackPoints(dom)))
        except Exception as e:
            print(str(e))
    print('Loaded %d tracks.' % len(tracks))
    for img in imgs:
        try:
            exif = GExiv2.Metadata(img)
            if tuple(exif.get_gps_info()) != (0., 0., 0.):
                continue

            print('No GPS info for %s... ' % os.path.basename(img), end='')
            candidates = []
            time = exif.get_date_time()
            for track in tracks:
                result = track(time)
                if result is not None:
                    candidates.append(result)
            assert(len(candidates) <= 1)
            if len(candidates) == 0:
                print('Not found.')
                continue
            candidate = candidates[0]
            if candidate[2] is not None:
                print(str(candidate))
                exif.set_gps_info(candidate[1], candidate[0], candidate[2])
                exif.save_file()
            else:
                print('(!) %f, %f' % (candidate[0], candidate[1]))
                batch.append(GooglePt(img, exif, candidate[0], candidate[1]))
        except Exception as e:
            raise e
            # print(str(e))
    print('Missing %d altitude queries.' % len(batch))
    elevapi = Elevation(API_KEY)
    elevapi.run(batch)


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
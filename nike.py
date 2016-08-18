from datetime import datetime, timedelta
import dateutil.parser
from pytz import timezone
import re
from math import floor, ceil, radians, sin, cos, atan2, sqrt

def haversine(lat1, lon1, lat2, lon2):
    R = 6367444.7
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)
    sin_delta_p = sin(delta_phi / 2.)
    sin_delta_l = sin(delta_lambda / 2.)
    a = sin_delta_p * sin_delta_p + cos(phi1) * cos(phi2) * sin_delta_l * sin_delta_l
    c = 2. * atan2(sqrt(a), sqrt(1. - a));
    return R * c;

def camel_case_to_py(txt):
    retval = ''
    for c in txt:
        if c.isupper():
            retval += '_%s' % c.lower()
        else:
            retval += c
    return retval

def attributes_to_fields(fields, obj, data, remap = None):
    for field in fields:
        k = camel_case_to_py(field)
        if remap is None:
            setattr(obj, k, data[field])
        else:
            setattr(obj, k, remap(data[field]))

def parse_timedelta(txt):
    RGX = re.compile('^((?P<hours>\d+):)?((?P<minutes>\d+):)?(?P<seconds>\d+(\.\d+)?)')
    match = RGX.match(txt)
    if not match:
        return None
    parms = {'hours': 0, 'minutes': 0, 'seconds': 0.0}
    for key, val in match.groupdict().items():
        if val and key in parms:
            parms[key] = float(val)
    return timedelta(**parms)


class ActivityTags(object):
    TERRAIN_TRAIL = 'TRAIL'
    EMOTION_UNSTOPPABLE = 'UNSTOPPABLE'
    WEATHER_PARTLY_SUNNY = 'PARTLY_SUNNY'

    def load(self, json_data):
        d = {}
        for item in json_data:
            d[item['tagType'].lower()] = item['tagValue']

        attributes_to_fields(['terrain', 'emotion', 'weather'], self, d)
        attributes_to_fields(['temperature'], self, d, int)

    def __init__(self):
        super(ActivityTags, self).__init__()
        self.temperature = None
        self.terrain = None
        self.emotion = None
        self.weather = None

class ActivityMetricsSummary(object):
    def load(self, json_data):
        attributes_to_fields(['calories', 'fuel', 'steps'], self, json_data, int)
        attributes_to_fields(['distance'], self, json_data, float)
        attributes_to_fields(['duration'], self, json_data, parse_timedelta)

    def __init__(self):
        super(ActivityMetricsSummary, self).__init__()
        self.calories = None
        self.fuel = None
        self.distance = None
        self.steps = None
        self.duration = None
        self.elevation_loss = None
        self.elevation_gain = None
        self.elevation_max = None
        self.elevation_min = None

class ActivityMetric(object):
    # Other metric types: https://developer.nike.com/documentation/api-docs/reference/interval-and-summary-metric-types.html
    METRIC_GPS = '__GPS__' # Not defined by Nike+
    METRIC_TIME = '__TIME__' # Not defined by Nike+
    METRIC_DISTANCE = 'DISTANCE'
    METRIC_SPEED = 'SPEED'
    METRIC_GPSSIGNALSTRENGTH = 'GPSSIGNALSTRENGTH'
    METRIC_HEARTRATE = 'HEARTRATE'
    METRIC_FUEL = 'FUEL'
    UNIT_SEC = 'SEC'
    UNIT_MIN = 'MIN'

    @classmethod
    def interpolate(cls, alpha, zero, one):
        return (1. - alpha) * zero + alpha * one

    def load(self, json_data):
        attributes_to_fields(['intervalUnit', 'metricType'], self, json_data)
        self.interval = int(json_data['intervalMetric'])
        if self.interval_unit == ActivityMetric.UNIT_MIN:
            self.interval *= 60
            self.interval_unit = ActivityMetric.UNIT_SEC

        self.values = list(map(float, json_data['values']))

    def sample(self, idx):
        if idx < 0:
            return self.values[0]
        elif idx >= len(self.values) - 1:
            return self.values[-1]
        elif float(int(idx)) == idx:
            return self.values[int(idx)]
        else:
            val_prev = self.values[int(floor(idx))]
            val_next = self.values[int(ceil(idx))]
            alpha = idx - floor(idx)
            return self.__class__.interpolate(alpha, val_prev, val_next)

    def resample_uniform(self, new_interval):
        unit = new_interval / self.interval
        new_values = []
        x = 0.
        while x <= len(self.values) - 1:
            new_values.append(self.sample(x))
            x += unit
        self.values = new_values
        self.interval = new_interval

    def resample(self, idxs, new_interval_secs):
        new_values = []
        for i in idxs:
            new_values.append(self.sample(i))
        self.values = new_values
        self.interval = new_interval_secs

    def __init__(self):
        super(ActivityMetric, self).__init__()
        self.metric_type = None
        self.interval_unit = None
        self.interval = None
        self.values = None

class ActivityMetricGPS(ActivityMetric):
    @classmethod
    def interpolate(cls, alpha, zero, one):
        return {
            'latitude': (1. - alpha) * zero['latitude'] + alpha * one['latitude'],
            'longitude': (1. - alpha) * zero['longitude'] + alpha * one['longitude'],
            'elevation': (1. - alpha) * zero['elevation'] + alpha * one['elevation']
        }

    def compute_distance(self, max_dist):
        self.values[0]['distance'] = 0.0
        prev_lat = self.values[0]['latitude']
        prev_lon = self.values[0]['longitude']
        prev_dist = 0.0
        for i in range(1, len(self.values)):
            lat = self.values[i]['latitude']
            lon = self.values[i]['longitude']
            prev_dist += haversine(prev_lat, prev_lon, lat, lon) / 1000.
            self.values[i]['distance'] = prev_dist
            prev_lat, prev_lon = lat, lon
        last_dist = self.values[-1]['distance']
        scale_factor = max_dist / last_dist
        for i in range(0, len(self.values)):
            self.values[i]['distance'] *= scale_factor
        return last_dist - max_dist

    def map_dist_to_indices(self, metric_dist):
        retval = []
        mdist_i = 0
        prev_mdist = 0.
        n_mdist = len(metric_dist.values)
        for item in self.values:
            dist = item['distance']
            while mdist_i < n_mdist and metric_dist.values[mdist_i] < dist:
                prev_mdist = metric_dist.values[mdist_i]
                mdist_i += 1
            if mdist_i >= n_mdist:
                retval.append(n_mdist - 1)
            if metric_dist.values[mdist_i] == dist:
                retval.append(mdist_i)
                continue
            # interpolate
            assert(mdist_i > 0 and prev_mdist == metric_dist.values[mdist_i - 1])
            assert(dist >= prev_mdist)
            alpha = (dist - prev_mdist) / (metric_dist.values[mdist_i] - prev_mdist)
            retval.append(float(mdist_i) - 1. + alpha)
            assert(abs(metric_dist.sample(retval[-1]) - dist) < 0.001)
        return retval


    def load(self, json_data):
        attributes_to_fields(['elevationLoss', 'elevationGain', 'elevationMax', 'elevationMin'], self, json_data, float)
        attributes_to_fields(['intervalUnit'], self, json_data)
        self.interval = int(json_data['intervalMetric'])
        self.values = json_data['waypoints']

    def __init__(self):
        super(ActivityMetricGPS, self).__init__()
        self.elevation_loss = None
        self.elevation_gain = None
        self.elevation_min = None
        self.elevation_max = None


class ActivityMetrics(object):
    def load(self, json_data):
        for json_metric in json_data:
            metric = ActivityMetric()
            metric.load(json_metric)
            self.all_metrics[metric.metric_type] = metric

    def synchronize_to_distance(self):
        assert(self.distance is not None)
        target_len = len(self.distance.values)
        for k in self.all_metrics:
            if k == ActivityMetric.METRIC_GPS or k == ActivityMetric.METRIC_DISTANCE:
                continue
            metric = self.all_metrics[k]
            metric.resample_uniform(float(self.distance.interval))
            if len(metric.values) > target_len:
                del metric.values[target_len:]
            else:
                metric.values += [metric.values[-1]] * (target_len - len(metric.values))

    def synchronize_to_gps(self):
        assert(self.gps is not None and self.distance is not None)
        self.gps.compute_distance(self.distance.values[-1])
        idxs = self.gps.map_dist_to_indices(self.distance)
        assert(len(idxs) == len(self.gps.values))
        for k in self.all_metrics:
            if k == ActivityMetric.METRIC_GPS or k == ActivityMetric.METRIC_DISTANCE:
                continue
            metric = self.all_metrics[k]
            if len(metric.values) != len(self.distance.values):
                metric.resample_uniform(float(self.distance.interval))
            metric.resample(idxs, self.gps.interval)
        self.distance.resample(idxs, self.gps.interval)

    def pack(self, metrics = None):
        if metrics is None:
            metrics = self.all_metrics.keys()

        # Make sure all the metrics are in sync
        any_metric = self.gps if self.gps is not None else self.all_metrics[metrics[0]]
        assert(any_metric.interval_unit == ActivityMetric.UNIT_SEC)
        for k in metrics:
            assert(len(self.all_metrics[k].values) == len(any_metric.values))
            assert(self.all_metrics[k].interval == any_metric.interval)
            assert(self.all_metrics[k].interval_unit == any_metric.interval_unit)

        packed_values = []
        for i in range(0, len(any_metric.values)):
            packed_values.append({})
            for k in metrics:
                packed_values[-1][k] = self.all_metrics[k].values[i]
                packed_values[-1][ActivityMetric.METRIC_TIME] = timedelta(
                    seconds=float(any_metric.interval) * float(i))
        return packed_values


    def __getattribute__(self, key):
        if key == 'distance':
            return self.all_metrics.get(ActivityMetric.METRIC_DISTANCE)
        elif key == 'speed':
            return self.all_metrics.get(ActivityMetric.METRIC_SPEED)
        elif key == 'gps_signal_strength':
            return self.all_metrics.get(ActivityMetric.METRIC_GPSSIGNALSTRENGTH)
        elif key == 'heart_rate':
            return self.all_metrics.get(ActivityMetric.METRIC_HEARTRATE)
        elif key == 'fuel':
            return self.all_metrics.get(ActivityMetric.METRIC_FUEL)
        elif key == 'gps':
            return self.all_metrics.get(ActivityMetric.METRIC_GPS)
        else:
            return super(ActivityMetrics, self).__getattribute__(key)

    def __init__(self):
        super(ActivityMetrics, self).__init__()
        self.all_metrics = {}


class ActivityData(object):
    # The remaining activity types: https://developer.nike.com/documentation/api-docs/reference/activity-types.html
    ACTIVITY_TYPE_RUN = 'RUN'
    STATUS_COMPLETE = 'COMPLETE'
    # The remaining device types: https://developer.nike.com/documentation/api-docs/reference/device-types.html
    DEVICE_TYPE_IPHONE = 'IPHONE'

    def load(self, json_data, gps_data = None):
        # Import trivial attributes
        attributes_to_fields(['activityId', 'activityType', 'status', 'deviceType'], self, json_data)
        attributes_to_fields(['isGpsActivity'], self, json_data, bool)
        self.metrics_summary.load(json_data['metricSummary'])
        self.tags.load(json_data['tags'])
        self.metrics.load(json_data['metrics'])
        # Cast time with the correct timezone
        tz = timezone(json_data['activityTimeZone'])
        self.start_time = tz.localize(dateutil.parser.parse(json_data['startTime'], ignoretz=True))
        if gps_data is not None:
            self.load_gps_data(gps_data)

    def load_gps_data(self, gps_data):
        gps = ActivityMetricGPS()
        gps.load(gps_data)
        self.metrics.all_metrics[ActivityMetric.METRIC_GPS] = gps
        self.metrics_summary.elevation_max = gps.elevation_max
        self.metrics_summary.elevation_min = gps.elevation_min
        self.metrics_summary.elevation_gain = gps.elevation_gain
        self.metrics_summary.elevation_loss = gps.elevation_loss

    def __init__(self):
        super(ActivityData, self).__init__()
        self.activity_id = None
        self.activity_type = None
        self.start_time = None
        self.status = None
        self.device_type = None
        self.is_gps_activity = None
        self.metrics_summary = ActivityMetricsSummary()
        self.metrics = ActivityMetrics()
        self.tags = ActivityTags()


if __name__ == '__main__':
    import simplejson
    import xml.dom.minidom as DOM

    with open('/Users/Spak/Desktop/last.json', 'r') as fs:
        gpsdata = simplejson.load(fs)
    with open('/Users/Spak/Desktop/last2.json', 'r') as fs:
        actdata = simplejson.load(fs)
    a = ActivityData()
    a.load(actdata, gpsdata)
    # diff = a.metrics.gps.compute_distance(a.metrics_summary.distance)
    # print('Difference between estimated length and computed length: %f m' % diff)
    # a.metrics.synchronize_to_distance()
    # # TEST
    # for k in a.metrics.all_metrics:
    #     if k == ActivityMetric.METRIC_GPS:
    #         continue
    #     assert(len(a.metrics.all_metrics[k].values) == len(a.metrics.distance.values))
    # # ----
    # idxs = a.metrics.gps.map_dist_to_indices(a.metrics.distance)
    # # TEST
    # for i, j in enumerate(idxs):
    #     assert(abs(a.metrics.distance.sample(j) - a.metrics.gps.values[i]['distance']) < 0.1)
    # # ----
    a.metrics.synchronize_to_gps()
    trackpoints = a.metrics.pack()

    # Convert to xml
    doc = DOM.Document()
    xml_trkseg = doc.createElement('trkseg')
    for tp in trackpoints:
        xml_tp = doc.createElement('trkpt')
        xml_tp.setAttribute('lat', str(tp[ActivityMetric.METRIC_GPS]['latitude']))
        xml_tp.setAttribute('lon', str(tp[ActivityMetric.METRIC_GPS]['longitude']))
        ele_tp = doc.createElement('ele')
        ele_tp.appendChild(doc.createTextNode(str(tp[ActivityMetric.METRIC_GPS]['elevation'])))
        xml_tp.appendChild(ele_tp)
        time_tp = doc.createElement('time')
        real_time = a.start_time + tp[ActivityMetric.METRIC_TIME]
        time_tp.appendChild(doc.createTextNode(real_time.isoformat()))
        xml_tp.appendChild(time_tp)
        ext_tp = doc.createElement('extensions')
        xml_tp.appendChild(ext_tp)
        heart_tp = doc.createElement('hr')
        heart_tp.appendChild(doc.createTextNode(str(int(tp[ActivityMetric.METRIC_HEARTRATE]))))
        ext_tp.appendChild(heart_tp)
        xml_trkseg.appendChild(xml_tp)
    xml_trk = doc.createElement('trk')
    xml_trk.appendChild(xml_trkseg)
    xml_gpx = doc.createElement('gpx')
    xml_gpx.setAttribute('version', '1.1')
    xml_gpx.setAttribute('creator', 'PyGPX')
    xml_gpx.appendChild(xml_trk)
    print("<?xml version=\"1.0\" ?>")
    print(xml_gpx.toprettyxml())
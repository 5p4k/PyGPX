import requests

class GoogleElevationAPI(requests.Session):
	ELEVATION_API_URL = 'https://maps.googleapis.com/maps/api/elevation/json'
	STATUS_OK = 'OK'
	STATUS_INVALID = 'INVALID_REQUEST'
	STATUS_LIMIT_EXCEEDED = 'OVER_QUERY_LIMIT'
	STATUS_DENIED = 'REQUEST_DENIED'
	STATUS_ERR = 'UNKNOWN_ERROR'

	def _parse_result(self, json):
		self.status = json['status']
		if self.status == STATUS_OK:
			for i in xrange(0, len(json['results'])):
				lat, lon = self.locations[i]
				self.locations[i] = lat, lon, json['results'][i]['elevation']

	def add_location(self, lat, lon):
		self.locations.append((lat, lon))

	def clear(self):
		self.locations = []

	def run(self):
		self.params['locations'] = '|'.join([
			('%0.6f,%0.6f' % item) for item in self.locations
		])
		self._parse_result(self.get(self.ELEVATION_API_URL).json())

	def __init__(self, api_key):
		super(GoogleElevationAPI, self).__init__()
		self.params = {
			'key': api_key
		}
		self.locations = []
		self.status = None


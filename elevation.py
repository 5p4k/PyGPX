import requests, time

class GoogleElevationAPI(requests.Session):
	CHUNK_SIZE = 56
	ELEVATION_API_URL = 'https://maps.googleapis.com/maps/api/elevation/json'
	STATUS_OK = 'OK'
	STATUS_INVALID = 'INVALID_REQUEST'
	STATUS_LIMIT_EXCEEDED = 'OVER_QUERY_LIMIT'
	STATUS_DENIED = 'REQUEST_DENIED'
	STATUS_ERR = 'UNKNOWN_ERROR'

	def _parse_result(self, json, idx=0):
		self.status = json['status']
		if self.status == GoogleElevationAPI.STATUS_OK:
			for i in xrange(0, len(json['results'])):
				lat, lon = self.locations[idx + i]
				self.locations[idx + i] = lat, lon, json['results'][i]['elevation']

	def add_location(self, lat, lon):
		self.locations.append((lat, lon))

	def clear(self):
		self.locations = []

	def run(self, index_range=None, auto_sleep_quota=True):
		slept = False
		if index_range is None:
			index_range = (0, len(self.locations))
		for start_idx in xrange(index_range[0], index_range[1], self.CHUNK_SIZE):
			print('Processing nodes %d..%d (of %d)...' % (start_idx, start_idx + self.CHUNK_SIZE, len(self.locations)))
			chunk = self.locations[start_idx : start_idx + self.CHUNK_SIZE]
			self.params['locations'] = '|'.join([
				('%0.6f,%0.6f' % item) for item in chunk
			])
			self._parse_result(self.get(self.ELEVATION_API_URL).json(), idx=start_idx)
			if self.status != GoogleElevationAPI.STATUS_OK:
				if auto_sleep_quota and self.status == STATUS_LIMIT_EXCEEDED and not slept:
					# Sleep and try again
					print('Quota exceeded. Sleeping 1 second.')
					time.sleep(1)
					slept = True
					continue
				else:
					return False
			else:
				slept = False
		return True

	def __init__(self, api_key):
		super(GoogleElevationAPI, self).__init__()
		self.params = {
			'key': api_key
		}
		self.locations = []
		self.status = None


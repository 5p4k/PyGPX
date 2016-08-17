import requests, time

class GoogleElevationAPI(requests.Session):
	CHUNK_SIZE = 56
	ELEVATION_API_URL = 'https://maps.googleapis.com/maps/api/elevation/json'
	STATUS_OK = 'OK'
	STATUS_INVALID = 'INVALID_REQUEST'
	STATUS_LIMIT_EXCEEDED = 'OVER_QUERY_LIMIT'
	STATUS_DENIED = 'REQUEST_DENIED'
	STATUS_ERR = 'UNKNOWN_ERROR'

	def _parse_result(self, json):
		self._last_status = json['status']
		if self._last_status == GoogleElevationAPI.STATUS_OK:
			for i in xrange(0, len(json['results'])):
				self._chunk[i].elevation = json['results'][i]['elevation']

	def run(self, trackpts, auto_sleep_quota=True):
		slept = False
		idx = 0
		padding_d = '{:>' + str(len(str(len(trackpts)))) + 'd}'
		format_str = 'Track points {0}..{0} (of {0}): querying {0} items...'.format(padding_d)
		start_idx = -1
		self._chunk = []
		while idx < len(trackpts):
			# if they're equal, the chunk has already been populated
			if idx != start_idx:
				start_idx = idx
				self._chunk = []
				# populate chunk
				for trackpt in trackpts[start_idx:]:
					idx += 1
					# if trackpt.elevation is None:
					self._chunk.append(trackpt)
					if len(self._chunk) >= self.CHUNK_SIZE:
						break
				# process chunk
				print(format_str.format(start_idx, idx, len(trackpts), len(self._chunk)))
				# populate params
				self.params['locations'] = '|'.join([item.apiformat() for item in self._chunk])

			print(self.params)
			response = self.get(self.ELEVATION_API_URL)
			self._last_status = GoogleElevationAPI.STATUS_ERR
			try:
				self._parse_result(response.json())
			except Exception, e:
				print(str(e))
				self._last_status = GoogleElevationAPI.STATUS_ERR
			# handle errors
			if self._last_status != GoogleElevationAPI.STATUS_OK:
				if auto_sleep_quota and self._last_status == GoogleElevationAPI.STATUS_LIMIT_EXCEEDED \
					and not slept:
					# sleep and try again
					print('Quota exceeded. Sleeping 1s.')
					time.sleep(1)
					slept = True
					idx = start_idx
					continue # aka retry
				else:
					print('Status: %s. Aborting.' % self._last_status)
					return False
			else:
				slept = False
		return True

	def __init__(self, api_key):
		super(GoogleElevationAPI, self).__init__()
		self.params = {
			'key': api_key
		}
		self._chunk = []
		self._last_status = None


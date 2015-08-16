import requests, time
import xml.dom.minidom as DOM
from datetime import datetime
import dateutil

class TrackPoint(object):
	def __getattr__(self, key):
		if key in ['lat', 'latitude']:
			return float(self._dom_node.getAttribute('lat'))
		elif key in ['lon', 'longitude']:
			return float(self._dom_node.getAttribute('lon'))
		elif key in ['elevation', 'ele']:
			return self._get_elevation()
		elif key == 'time':
			return self._get_time()
		else:
			return super(TrackPoint, self).__getattr__(key)

	def __setattr__(self, key, value):
		if key in ['lat', 'latitude']:
			self._dom_node.setAttribute('lat', ('%0.6f' % value))
		elif key in ['lon', 'longitude']:
			self._dom_node.setAttribute('lon', ('%0.6f' % value))
		elif key in ['elevation', 'ele']:
			self._set_elevation(value)
		elif key == 'time':
			self._set_time(value)
		else:
			super(TrackPoint, self).__setattr__(key, value)

	def _ensure_tag(self, dom, tagname, default_value=''):
		candidates = self._dom_node.getElementsByTagName(tagname)
		if len(candidates) == 0:
			node = dom.createElement(tagname)
			node.appendChild(dom.createTextNode(default_value))
			self._dom_node.appendChild(node)
			return node
		else:
			node = candidates[0]
			if node.hasChildNodes():
				if node.firstChild.nodeType == DOM.TEXT_NODE:
					default_value = node.firstChild.nodeValue
					if node.firstChild == node.lastChild:
						return node
				while node.hasChildNodes():
					node.removeChild(node.firstChild)
			node.appendChild(dom.createTextNode(default_value))
			return node

	def _get_elevation(self):
		str_value = self._dom_ele.firstChild.nodeValue
		if str_value == '':
			return None
		else:
			return float(str_value)
	def _set_elevation(self, elevation):
		print('setting elevation ' + str(elevation))
		if elevation is None:
			self._dom_ele.firstChild.nodeValue = ''
		else:
			self._dom_ele.firstChild.nodeValue = ('%0.2f' % elevation)

	def _get_time(self):
		str_value = self._dom_time.firstChild.nodeValue
		if str_value == '':
			return None
		else:
			return dateutil.parse(str_value)
	def _set_time(self, dt):
		if dt is None:
			self._dom_time.firstChild.nodeValue = ''
		else:
			self._dom_time.firstChild.nodeValue = dt.isoformat()

	def apiformat(self):
		return '%0.6f,%0.6f' % (self.lat, self.lon)

	def __init__(self, dom, trackpt_dom):
		self._dom_node = trackpt_dom
		self._dom_ele = self._ensure_tag(dom, 'ele')
		self._dom_time = self._ensure_tag(dom, 'time')

class TrackPoints(object):

	def __getitem__(self, key):
		return self._locations.__getitem__(key)
	def __len__(self):
		return len(self._locations)
	def __iter__(self):
		return self._locations.__iter__()
	def __reversed__(self):
		return self._locations.__reversed__()
	def __contains__(self, item):
		return self._locations.__contains__(item)

	def __init__(self, dom):
		self._locations = []
		for trkpt in dom.getElementsByTagName('trkpt'):
			self._locations.append(TrackPoint(dom, trkpt))


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
					if trackpt.elevation is None:
						self._chunk.append(trackpt)
						if len(self._chunk) >= self.CHUNK_SIZE:
							break
				# process chunk
				print(format_str.format(start_idx, idx, len(trackpts), len(self._chunk)))
				# populate params
				self.params['locations'] = '|'.join([item.apiformat() for item in self._chunk])

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


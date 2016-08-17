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
				if node.firstChild.nodeType == 3:
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

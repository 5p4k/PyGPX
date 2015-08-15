#/usr/bin/env python
import xml.dom.minidom
import sys

API_KEY = 'YOUR_API_KEY'

def main(filename):
	pass

if __name__ == '__main__':
	if len(sys.argv) <= 1:
		print('Usage: %s <file.gpx>' % sys.argv[0])
	else:
		main(sys.argv[1])

from docopt import docopt as docopt1
from collections import namedtuple
import re

def dict_to_obj(d):
	def add_to_dict_if_match(r, k, v, d):
		m = re.match(r, k)
		if m:
			d[m[1].replace('-', '_')] = v
		return not not m

	d1 = dict()
	for k, v in d.items():
		if isinstance(v, dict):
			d1[k] = dict_to_obj(v)
		elif add_to_dict_if_match('--(.*)', k, v, d1):
			pass
		elif add_to_dict_if_match('\<(.*)\>', k, v, d1):
			pass
	return namedtuple('object', d1.keys())(*d1.values())

def docopt(*args, **kwargs):
	a = docopt1(*args, **kwargs)
	return dict_to_obj(a)

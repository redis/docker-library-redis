
import sys

def eprint(*args, **kwargs):
	print >> sys.stderr, ' '.join(map(lambda x: "%s" % x, args))

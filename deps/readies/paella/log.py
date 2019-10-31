
import os

def fatal(text):
	eprint("%s: %s" %(os.path.basename(__file__), text))
	exit(1)

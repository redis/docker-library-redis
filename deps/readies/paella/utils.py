
import sys
from subprocess import Popen, PIPE

if (sys.version_info > (3, 0)):
	from .utils3 import *
else:
	from .utils2 import *

def sh(cmd):
    return " ".join(Popen(cmd.split(), stdout=PIPE).communicate()[0].split("\n"))

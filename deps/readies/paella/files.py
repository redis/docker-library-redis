
from contextlib import contextmanager
import os
import os.path
import tempfile
try:
    from urllib2 import urlopen
except:
    from urllib.request import urlopen

#----------------------------------------------------------------------------------------------

def fread(fname, mode='rb'):
	with open(fname, mode) as file:
		return file.read()

#----------------------------------------------------------------------------------------------

def fwrite(fname, text, mode='w'):
	with open(fname, mode) as file:
		return file.write(text)

#----------------------------------------------------------------------------------------------

def flines(fname, mode = 'rb'):
	return [line.rstrip() for line in open(fname)]

#----------------------------------------------------------------------------------------------

def tempfilepath():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    return path

#----------------------------------------------------------------------------------------------

def wget(url, dest="", tempdir=False):
    if dest == "":
        dest = os.path.basename(url)
        if dest == "":
            dest = tempfilepath()
        elif tempdir:
            dest = os.path.join('/tmp', dest)
    ufile = urlopen(url)
    data = ufile.read()
    with open(dest, "wb") as file:
        file.write(data)
    return os.path.abspath(dest)

#----------------------------------------------------------------------------------------------

@contextmanager
def cwd(path):
    d0 = os.getcwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(d0)

#----------------------------------------------------------------------------------------------

def mkdir_p(dir):
    if dir != '':
        os.makedirs(dir, exist_ok=True)

#----------------------------------------------------------------------------------------------

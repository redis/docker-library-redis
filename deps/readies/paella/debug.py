
import os

#----------------------------------------------------------------------------------------------

if 'PYDEBUG' in os.environ and os.environ['PYDEBUG'] == '1':
    try:
        from pudb import set_trace as bb
    except ImportError:
        from pdb import set_trace as bb
else:
	def bb(): pass

#----------------------------------------------------------------------------------------------

#
# simple Python program use for checking JpyDbg Python configuration   
# before launching jpydbg stuff
#
import sys
import os.path

#
# Unit testing startup
#
if __name__ == '__main__':
#   checking for provided parameters
  print "args = " , sys.argv
  print "sys.path =", sys.path
  print "Hello from Python"
  pass

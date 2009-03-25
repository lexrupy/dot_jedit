""" pylint: disable-msg=W0401, E0202

 Launch a pylint control from jpydbg

 arg 1 = pythonpath to load
 arg 2 = pylint location
 arg 3 = candidate pysource to pylint
 arg 4  and above pylint complementary options

"""

__version__='$Revision: 1.1 $'
__date__='$Date: 2006/01/04 16:13:34 $'
# $Source: /cvsroot/jpydbg/jpydebugforge/java/org/jymc/jpydebug/python/pylintlauncher.py,v $

import sys
from dbgutils import *

# build a tiny wrapper on top of PyLint
class PyLintWrapper:
    """ Tiny JpyDbg wrapping class sitting on top of pylint modules"""
  
    def _removePySuffix( self , pyName ):
        """ remove trailinc .py or .pyc suffix """
        pyLoc =  pyName.rfind('.py')
        if pyLoc == -1:
            return pyName
        return pyName[:pyLoc]
  
    def run(  self , args ) :
        """ constructor gettint the current command line args """
        print sys.path
        utils = jpyutils()
        pyPathHandler = None
        if ( len(args) > 1 ): pyPathHandler   = PythonPathHandler(utils.getArg(args[1]))
        if ( len(args) > 2 ): pyLintLoc   = utils.getArg(args[2])
        if ( len(args) > 3 ): source   = utils.getArg(args[-1])
        if ( len(args) < 3 ): sys.exit(12) # missing arguments
        # build the accurate path 
        if pyPathHandler != None:
            pyPathHandler.getPyPathFromFile()
        # Insert source path in pythonpath
        # and make it current path on top of path
        debugPath = os.path.dirname(source)
        sys.path.insert(0,debugPath)
        # Insert pylint path in pythonpath
        # and make it current path
        debugPath = os.path.dirname(pyLintLoc)
        sys.path.append(debugPath)
        # import lint from specified location
        pyLintLoc = self._removePySuffix(pyLintLoc)
        pylint = __import__(os.path.basename(pyLintLoc))
        # process pylint with remainding arguments
        args[-1] = os.path.basename(args[-1])
        args[-1] = self._removePySuffix(args[-1])
        pylint.Run( args[3:] )
        sys.path.insert(0, debugPath )
#
# launching startup
#
if __name__ == '__main__':
    #   checking for provided parameters
    print "entering main"
    print "args = " , sys.argv
    runner = PyLintWrapper() ;
    runner.run(sys.argv)
  

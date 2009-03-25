""" pylint: disable-msg=W0401, E0202

 Launch a python shell for window execution inside a java swing pane

 arg 1 = pythonpath to load
 arg 3 = candidate pysource to pylint
 arg 4  and above candidate source complementary arguments

"""

__version__='$Revision: 1.1 $'
__date__='$Date: 2006/01/04 16:13:34 $'
# $Source: /cvsroot/jpydbg/jpydebugforge/java/org/jymc/jpydebug/python/pyshelllauncher.py,v $

import sys
from dbgutils import *

#
# build a tiny running class wrapperwrapper
#
class ShellWrapper:
    """ Tiny JpyDbg wrapping class sitting on top of python shell launch"""
  
    def run(  self , args ) :
        """ constructor gettint the current command line args """
        print sys.path
        utils = jpyutils()
        pyPathHandler = None
        if ( len(args) > 1 ): pyPathHandler   = PythonPathHandler(utils.getArg(args[1]))
        if ( len(args) > 2 ): source   = utils.getArg(args[2])
        if ( len(args) < 2 ): sys.exit(12) # missing arguments
        # build the accurate path 
        if pyPathHandler != None:
            pyPathHandler.getPyPathFromFile()
        # Insert source path in pythonpath
        # and make it current path
        debugPath = os.path.dirname(source)
        sys.path.append(debugPath)
        # process source with remainding arguments
        sys.argv = args[2:]
        import __main__
        myGlobals = __main__.__dict__
        myLocals = myGlobals
        inFile = open(source,"r")
        exec inFile.read() in myGlobals, myLocals
        inFile.close()
#        source = __import__(os.path.basename(sourceLoc),globals(),locals(),["__main__"])
#
# launching startup
#
if __name__ == '__main__':
    #   checking for provided parameters
    print "entering main"
    print "args = " , sys.argv
    runner = ShellWrapper() ;
    runner.run(sys.argv)
  

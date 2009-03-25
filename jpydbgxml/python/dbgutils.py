""" misc utility modules used by jpydbg stuff """

__version__='$Revision: 1.1 $'
__date__='$Date: 2006/01/04 16:13:34 $'
# $Source: /cvsroot/jpydbg/jpydebugforge/java/org/jymc/jpydebug/python/dbgutils.py,v $

import sys
import traceback
import os


class jpyutils :
  
    def __init__( self ):
        if ( os.name == 'java' ):
            self.isJython = 1 
        else:
            self.isJython = 0
 
    def parsedReturned( self , 
                        command = 'COMMAND' , 
                        argument = None , 
                        message = None , 
                        details = None ):
        parsedCommand = []
        parsedCommand.append(command)
        parsedCommand.append(argument)
        parsedCommand.append(message)
        parsedCommand.append(details)
        return parsedCommand

    def populateCMDException( self , arg , oldstd ):
        "global utility exception reporter for all pydbg classes"
        sys.stdout=oldstd
        tb , exctype , value = sys.exc_info()
        excTrace = traceback.format_exception( tb , exctype , value )
        tb = None # release
        return self.parsedReturned( argument = arg ,
                                    message = "Error on CMD" ,
                                    details = excTrace
                                  )  
                              
    def removeForXml( self , strElem , keepLinefeed = 0 ):
        "replace unsuported xml encoding characters"
        if (not  keepLinefeed ):       
            strElem = strElem.replace('\n','')
        strElem = strElem.replace('&',"&amp;")
        strElem = strElem.replace('"',"&quot;")
        strElem = strElem.replace('<','&lt;')
        strElem = strElem.replace('>','&gt;')
        # strElem = string.replace(strElem,'&','&amp;')
        return strElem
    
    def getArg( self , toParse ):
        toParse = toParse.strip()
        if len(toParse) == 0:
            return None
        # check for leading quotes in arguments which implies
        # quoted argument separated by quotes instead of spaces
        if ( toParse[0] == '"' or toParse[0]== "'" ):
            toParse = toParse[1:len(toParse)-1]
        #
        return toParse

class PythonPathHandler:
    "store the python path in a text file for jpydebug usage"
    def __init__(self , pyPathFName):
        self.PyPathFName = pyPathFName
        
  
    def getPyPathFromFile( self ):
        "read PYTHONPATH file and set python path variable out of it"
        try:
            pyPathFile = open( self.PyPathFName )
            pyPath = pyPathFile.read()
            # cleanly take care of previous ';' convention
            if os.pathsep != ';':
                pyPath.replace(';' , os.pathsep)
            if pyPath.find(os.pathsep) != -1:
                sys.path = pyPath.split(os.pathsep)
                # remove empty nodes first
                for element in sys.path:
                    if ( len(element.strip())==0 ):
                        sys.path.remove(element)
            pyPathFile.close()  
        except:
            # go ahead on exception on file access
            pass
    
    def setPyPathFileFromPath( self ):
        "save PYTHON sys path in a file"
        try:
            pathStr = ''
            for pathElem in sys.path:
                pathStr += pathElem+os.pathsep
            pyPathFile = open( self.PyPathFName , mode='w' )
            pyPathFile.write(pathStr)
            pyPathFile.close()
        except:
            # go ahead on exception on file access
            pass
    


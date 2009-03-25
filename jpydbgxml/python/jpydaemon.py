#! /usr/bin/env python

""" this daemon may be used by 'external' python sollicitors interfaces"""

__version__='$Revision: 1.1 $'
__date__='$Date: 2006/01/04 16:13:34 $'
# $Source: /cvsroot/jpydbg/jpydebugforge/java/org/jymc/jpydebug/python/jpydaemon.py,v $



import sys
import bdb 
import socket
import string
import traceback
import os
# import inspect
import types
import __builtin__

from dbgutils import *

HOST = '' 
PORT = 29000 # default listening port
OK   = "OK"

COMMAND = 0
SET_BP  = 2
DEBUG   = 31
STEP    = 4
NEXT    = 5
RUN     = 6
FREEZE  = 7 # remain on current line 
CLEAR_BP  = 8
STACK   = 9
QUIT    = 10
LOCALS  = 11
GLOBALS = 12
SETARGS = 13
READSRC = 14
COMPOSITE = 15
UNKNOWN = -1


CP037_OPENBRACKET='\xBA'
CP037_CLOSEBRACKET='\xBB'



# instanciate a jpyutil object
_utils = jpyutils() 

class JPyDbg(bdb.Bdb) :
    
    def __init__(self):
        bdb.Bdb.__init__(self)
        # store debugger script name to avoid debugging it's own frame
        #self.debuggerFName = os.path.normcase(sys.argv[0])
        self.debuggerFName = os.path.normcase(sys._getframe(0).f_code.co_filename)
        print self.debuggerFName
        # client debugger connection
        self.connection = None
        # frame debuggee contexts
        self.globalContext = None
        self.localContext = None 
        self.verbose = 0
        # hide is used to prevent debug inside debugger
        self.hide = 0
        # debugger active information
        self.debuggee = None
        self.cmd = UNKNOWN
        # net buffer content
        self.lastBuffer = ""
        # EXCEPTION raised flag
        self.exceptionRaised = 0
        # debuggee current 'command line arguments'
        self.debuggeeArgs = None
        # last executed line exception or None
        self.lastLineException = None
        # tracing facility
        # self.dbgTrc = file("./jpydbgtrace.TXT" , "w+")

#    def trace( self , message ):
#      self.dbgTrc.write(message + '\n');
    def do_clear(self, arg):
        pass
      
    def populateToClient( self , bufferList ) :
        mbuffer = '<JPY>'   
        for element in bufferList:
            mbuffer = mbuffer + ' ' + __builtin__.str(element)
        mbuffer = mbuffer + '</JPY>\n'
        #print buffer
        self.connection.send( mbuffer )
    
    # bdb overwitten to capture call debug event  
    def user_call(self, frame, args):
        name = frame.f_code.co_name
        if not name: name = '???'
        fn = self.canonic(frame.f_code.co_filename)
        if not fn: fn = '???'
        # discard debugger frame 
        if fn == self.debuggerFName or self.hide:
            self.hide = self.hide + 1
        if self.hide:     
            return None
        self.populateToClient( [ '<CALL',
                                 'cmd="'+ __builtin__.str(self.cmd)+'"' , 
                                 'fn="'+ _utils.removeForXml(fn) +'"' ,
                                 'name="'+name+'"',
                                 'args="'+__builtin__.str(args)+'"' ,
                                 '/>' ]
                             )
      
      
    def checkDbgAction( self , frame ):
        if ( self.cmd == DEBUG )  or ( self.cmd == STEP ) or ( self.cmd == NEXT ) or ( self.cmd == RUN ):
            # DEBUG STARTING event  
            # Debuggin starts stop on first line wait for NEXT , STEP , RUN , STOP ....  
            while ( self._parseSubCommand( self._receiveCommand() , frame ) == FREEZE ):
                pass
        
        
    # bdb overwitten to capture line debug event  
    def user_line(self, frame):
        if self.hide:
            return None 
        import linecache
        name = frame.f_code.co_name
        if not name: name = '???'
        fn = self.canonic(frame.f_code.co_filename)
        if not fn: fn = '???'
        # populate info to client side
        line = linecache.getline(fn, frame.f_lineno)
        self.populateToClient( [ '<LINE',
                               'cmd="'+ __builtin__.str(self.cmd)+'"' , 
                               'fn="'+ _utils.removeForXml(fn)+'"' ,
                               'lineno="'+__builtin__.str(frame.f_lineno)+'"' ,
                               'name="' + name + '"' ,
                               'line="' + _utils.removeForXml(line.strip())+'"',
                               '/>'] )
        # what's on next
        self.checkDbgAction( frame ) 
        
    # bdb overwitten to capture return debug event  
    def user_return(self, frame, retval):
        fn = self.canonic(frame.f_code.co_filename)
        if not fn: fn = '???'
        if self.hide:
            self.hide = self.hide - 1
            return None  
        self.populateToClient( [  '<RETURN',
                                  'cmd="'+__builtin__.str(self.cmd)+'"' , 
                                  'fn="'+ _utils.removeForXml(fn)+'"' ,
                                  'retval="'+__builtin__.str(retval)+'"' ,
                                  '/>'] )
    
    #
    # handle EBCDIC MVS idiosynchrasies
    #
    def _mvsCp037Check( self , inStr ):
        if sys.platform != 'mvs' :
            return inStr
        inStr = inStr.replace('[',CP037_OPENBRACKET)
        inStr = inStr.replace(']',CP037_CLOSEBRACKET)
        return inStr

    def send_client_exception( self , cmd , content ):
        # self.trace("exception sent")
        self.populateToClient( ['<EXCEPTION',
                               'cmd="'+cmd+'"' , 
                               'content="'+self._mvsCp037Check(content)+'"' ,
                              '/>'] ) 
      
                                  
    def populate_exception( self , exc_stuff):
        # self.trace("exception populated")
        if ( self.exceptionRaised == 0 ): # exception not yet processed
            extype  = exc_stuff[0]
            details = exc_stuff[1]
          
            #ex = exc_stuff
            # Deal With SystemExit in specific way to reflect debuggee's return
            if issubclass( extype , SystemExit):
                content = 'System Exit REQUESTED BY DEBUGGEE  =' + str(details)
            elif issubclass(extype, SyntaxError):  
                content = __builtin__.str(details)
                error = details[0]
                compd = details[1]
                content = 'SOURCE:SYNTAXERROR:"'+\
                       __builtin__.str(compd[0])+ '":('+\
                       __builtin__.str(compd[1])+','+\
                       __builtin__.str(compd[2])+\
                       ')'+':'+error
            elif issubclass(extype,NameError):
                content = 'SOURCE:NAMEERROR:'+__builtin__.str(details)
            elif issubclass(extype,ImportError):
                content = 'SOURCE::IMPORTERROR:'+__builtin__.str(details)
            else:
                content = __builtin__.str(details)
            # keep track of received exception
            # populate exception
            self.lastLineException = ['<EXCEPTION',
                                    'cmd="'+__builtin__.str(self.cmd)+'"' , 
                                    'content="'+ _utils.removeForXml(content)+ \
                                    '"' ,
                                    '/>']
            self.send_client_exception( __builtin__.str(self.cmd) , _utils.removeForXml(content) )
            self.exceptionRaised = 1 # set ExceptionFlag On 
            
        
    # bdb overwitten to capture Exception events  
    def user_exception(self, frame, exc_stuff):
      # self.trace("first exception populated")
      # capture next / step go ahead when exception is around 
      # current steatement while steping
        if self.cmd==NEXT or self.cmd==STEP:
            # self.populate_exception( exc_stuff )
            self.set_step()
            sys.settrace(self.trace_dispatch)
        else:   
            self.populate_exception( exc_stuff )
            self.set_continue()
  
    def parsedReturned( self , command = 'COMMAND' , argument = None , message = None , details = None ):
        parsedCommand = []
        parsedCommand.append(command)
        parsedCommand.append(argument)
        parsedCommand.append(message)
        parsedCommand.append(details)
        return parsedCommand

    # acting as stdout => redirect read to the wire 
    def readline( self ):
        command = self.readNetBuffer()
        verb , mhelp = self.commandSyntax( command )
        return mhelp
        
      
    # acting as stdout => redirect to client side 
    def write( self , toPrint ):
        # transform eol pattern   
        if ( toPrint == "\n" ):
            toPrint = "/EOL/"
        self.populateToClient( ['<STDOUT' , 'content="'+ _utils.removeForXml(toPrint)+'"' , '/>' ] )
      
    # acting as stdout => redirect to client side 
    def writeline( self , toPrint ):
        # stdout redirection
        self.write(toPrint )
        self.write("\n")

      # stdout flush override
    def flush( self ):
        pass
      
    def buildEvalArguments( self , arg ):
        posEqual = arg.find('=')
        if posEqual == -1:
            return None,None # Syntax error on provided expession couple
        return arg[:posEqual].strip() , arg[posEqual+1:].strip()

    #
    # parse & execute buffer command 
    #
    def dealWithCmd( self , 
                     verb , 
                     arg , 
                     myGlobals = globals() , 
                     myLocals = locals() 
                   ):
        #cmd = COMMAND
        msgOK = OK
        cmdType = "single"
        silent , silentarg = self.commandSyntax( arg )
        if silent == 'silent':
            arg = silentarg # consume
            # "exec" is the magic way which makes 
            # used debuggees dictionaries updatable while 
            # stopped in debugging hooks
            cmdType = "exec"  
            msgOK = silent
        # we use ';' as a python multiline syntaxic separator 
        arg = string.replace(arg,';','\n')
        # execute requested dynamic command on this side
        try:
            # redirect screen and keyboard io to jpydaemon
            oldstd = sys.stdout
            oldstdin = sys.stdin
            sys.stdout=self
            sys.stdin =self
            code = compile( arg ,"<string>" , cmdType)  
            exec code in myGlobals , myLocals
            sys.stdout=oldstd
            sys.stdin =oldstdin
            return _utils.parsedReturned( argument = arg , message = msgOK ) 
        except:
            try: 
                return _utils.populateCMDException(arg,oldstd)
            except:
                tb , exctype , value = sys.exc_info()
                excTrace = traceback.format_exception( tb , exctype , value )
                print excTrace
          
    #
    # build an xml CDATA structure
    # usage of plus is for jpysource.py xml CDATA encapsulation of itself
    #
    def CDATAForXml( self , data ):
        if sys.platform == 'mvs' :
            return '<'+'!'+ CP037_OPENBRACKET + 'CDATA' + \
               CP037_OPENBRACKET + data + \
               CP037_CLOSEBRACKET+ CP037_CLOSEBRACKET+'>'
        else:
            return '<'+'![CDATA['+ data + ']'+']>'
      
    def nextArg( self , toParse ):
        if toParse == None :
            return None , None  
        toParse = string.strip(toParse)
        separator = " "
        if len(toParse) == 0:
            return None , None
        # check for leading quotes in arguments which implies
        # quoted argument separated by quotes instead of spaces
        if ( toParse[0] == '"' or toParse[0]== "'" ):
            separator = toParse[0]
            toParse = toParse[1:]
        #
        nextSpace = toParse.find(separator)
        if ( nextSpace == -1 ):
            return string.strip(toParse) , None
        else:
            return string.strip(toParse[:nextSpace]) , string.strip(toParse[nextSpace+1:])
    
    #
    # parse & execute buffer command
    #
    def dealWithRead( self , verb , arg ):
        #cmd = READSRC
        # check python code and send back any found syntax error
        if arg == None:
            return _utils.parsedReturned( message = "JPyDaemon ReadSrc Argument missing")
        try:
            arg , lineno = self.nextArg(arg)  
            candidate = open(arg) # use 2.1 compatible open builtin for Jython
            myBuffer = _utils.parsedReturned( argument = arg , message=OK )
          # 
          # append the python source in <FILEREAD> TAG
            myBuffer.append( ['<FILEREAD' ,
                              'fn="'+arg+'"' ,
                              'lineno="'+__builtin__.str(lineno)+'">' +
                              self.CDATAForXml(self._mvsCp037Check(candidate.read())) +
                              '</FILEREAD>' ] )
            return myBuffer
        except IOError, e:
            return _utils.parsedReturned( argument = arg , message = e.strerror )
    #
    # parse & execute buffer command
    #
    def dealWithSetArgs( self , arg ):
        #cmd = SETARGS
        # populate given command line argument before debugging start
        # first slot reserved for program name 
        self.debuggeeArgs = [''] # nor args provided
        if arg != None:
            # loop on nextArg
            current , remainder = self.nextArg(arg)
            while current != None :
                self.debuggeeArgs.append(current)
                current , remainder = self.nextArg(remainder)
          
          # self.debuggeeArgs = string.split(arg)
        sys.argv = self.debuggeeArgs # store new argument list ins sys argv
        return _utils.parsedReturned( argument = arg , message = OK ) 

    # load the candidate source to debug
    # Run under debugger control 
    def dealWithDebug( self , verb , arg ):
        self.cmd = DEBUG
        if self.debuggee == None:
            result = "source not found : " + arg
            for dirname in sys.path:
                fullname = os.path.join(dirname,arg)
                if os.path.exists(fullname):
                    # Insert script directory in front of module search path
                    # and make it current path (#sourceforge REQID 88108 fix)
                    debugPath = os.path.dirname(fullname)
                    sys.path.insert(0, debugPath)
                    if (  len(debugPath) != 0 ):
                        # following test added for JYTHON support
                        if ( not _utils.isJython ):
                            # chdir not available in jython
                            os.chdir(debugPath)
                    oldstd = sys.stdout
                    sys.stdout=self
                    self.debuggee = fullname
                    sys.argv[0] = fullname # keep sys.argv in sync
                    try:
                        self.run('execfile(' + `fullname` + ')')
                        # send a dedicated message for syntax error in order for the
                        # frontend debugger to handle a specific message and display the involved line
                        # in side the frontend editor
                    except:
                        tb , exctype , value = sys.exc_info()
                        excTrace = __builtin__.str(traceback.format_exception( tb , exctype , value ))
                        # self.populateException(excTrace)
                        #self.trace("populating exception here : ("+str(len(excTrace))+")" + excTrace)
                        #self.trace("populating exception for XML here : " +  _utils.removeForXml(excTrace))
                        self.send_client_exception(__builtin__.str(self.cmd) , _utils.removeForXml(excTrace))
                        #print excTrace
                        pass
              
                sys.stdout=oldstd
                result ="OK"
                self.debuggee = None 
                break 
        else:
            result = "debug already in progress on : " + self.debuggee   
        return _utils.parsedReturned( command = 'DEBUG' , argument = arg , message = result ) 
    
    def formatStackElement( self , element ):
        curCode = element[0].f_code
        fName = curCode.co_filename
        line  =  element[1]
        if ( fName == '<string>' ):
            return ("program entry point")
        return _utils.removeForXml(fName + ' (' + __builtin__.str(line) + ') ')
    
    # populate current stack info to client side 
    def dealWithStack( self , frame ):
        stackList , size = self.get_stack ( frame , None )
        stackList.reverse() 
        xmlStack = ['<STACKLIST>' ] 
        for stackElement in stackList:
            xmlStack.append('<STACK')
            xmlStack.append('content="'+ self.formatStackElement(stackElement) +'"')
            xmlStack.append( '/>')
        xmlStack.append('</STACKLIST>') 
        self.populateToClient( xmlStack )
    
    # populate requested disctionary to client side
    def dealWithVariables( self , frame , type , stackIndex  ):
        # get the stack frame first   
        stackList , size = self.get_stack ( frame , None )
        stackList.reverse() 
        stackElement = stackList[int(stackIndex)]
        if ( type == 'GLOBALS' ):
            variables = stackElement[0].f_globals
        else:
            variables = stackElement[0].f_locals
        xmlVariables = ['<VARIABLES type="'+type+'">' ]
        for mapElement in variables.items():
            xmlVariables.append('<VARIABLE ')
            xmlVariables.append('name="'+ _utils.removeForXml(mapElement[0])+'" ')
            xmlVariables.append('content="'+ _utils.removeForXml(__builtin__.str(mapElement[1]))+'" ')
            xmlVariables.append('vartype="'+ self.getVarType(mapElement[1])+'" ')
            xmlVariables.append( '/>')
        xmlVariables.append('</VARIABLES>') 
        self.populateToClient( xmlVariables )
    
    # return true when selected element is composite candidate
    def isComposite( self , value ):
        if not ( isinstance(value , types.StringType ) or \
               isinstance(value , types.ComplexType ) or \
               isinstance(value , types.FloatType ) or \
               isinstance(value , types.IntType ) or \
               isinstance(value , types.LongType ) or \
               isinstance(value , types.NoneType ) or \
               isinstance(value , types.ListType ) or \
               isinstance(value , types.DictType ) or \
               isinstance(value , types.UnicodeType ) ):
            return 1
        else:
            return 0
       
    # return true when selected element is composite candidate
    def getVarType( self , value ):
        if self.isComposite(value):
            return 'COMPOSITE'
        else:
            return 'SIMPLE'
      
    # populate a variable XML structure back 
    def dealsWithComposites( self , oName , myGlobals , myLocals ):
        xmlVariables = ['<VARIABLES>' ]
        myObject = eval(oName ,  myGlobals , myLocals )
        for key in dir(myObject):
            value = getattr(myObject, key)
            #if self.isComposite(value):
            xmlVariables.append('<VARIABLE ')
            xmlVariables.append('name="'+ _utils.removeForXml(key) +'" ')
            xmlVariables.append('content="'+ _utils.removeForXml(__builtin__.str(value)) +'" ')
            xmlVariables.append('vartype="'+ self.getVarType(value)+'" ')
            xmlVariables.append( '/>')
        xmlVariables.append('</VARIABLES>') 
        self.populateToClient( xmlVariables )
      
    def variablesSubCommand( self , frame , verb , arg , cmd ):
        self.cmd = cmd
        if ( arg == None ):
            arg = "0"  
        else:    
            arg , optarg = self.nextArg(arg) # split BP arguments  
        self.dealWithVariables( frame , verb , arg )
        self.cmd = FREEZE 
    
    
    # rough command/subcommand syntax analyzer    
    def commandSyntax( self , command ):
        self.cmd  = UNKNOWN
        verb , arg  = self.nextArg(command)
        return verb , arg  
    
    
    def quiting( self ):
        self.populateToClient( ['<TERMINATE/>'] )
        self.set_quit()

    def parseSingleCommand( self , command ):
        verb , arg = self.commandSyntax( command )
        if ( string.upper(verb) == "CMD" ):
            return self.dealWithCmd( verb , arg )
        if ( string.upper(verb) == "READSRC" ):
            return self.dealWithRead( verb , arg )
        if ( string.upper(verb) == "SETARGS" ):
            return self.dealWithSetArgs( arg )
        elif ( string.upper(verb) == "DBG" ):
            return self.dealWithDebug( verb, arg )
        elif ( string.upper(verb) == "STOP" ):
            return None
        else:
            return _utils.parsedReturned( message = "JPyDaemon SYNTAX ERROR : " + command ) 
        
    # receive a command when in debugging state using debuggee's frame local and global
    # contexts
    def _parseSubCommand( self , command , frame ):
        if ( command == None ): # in case of IP socket Failures
            return UNKNOWN
        verb , arg = self.commandSyntax( command )
        if ( string.upper(verb) == "CMD" ):
            self.populateCommandToClient( command ,
                                        self.dealWithCmd( verb ,
                                                          arg ,
                                                          myGlobals= frame.f_globals ,
                                                          myLocals = frame.f_locals
                                                        )
                                        )
            self.cmd = FREEZE

        elif ( string.upper(verb) == "READSRC" ):
            self.populateCommandToClient( command ,
                                        self.dealWithRead( verb , arg )
                                      )
            self.cmd = FREEZE
        
        elif ( string.upper(verb) == "NEXT" ):
            self.cmd = NEXT
            self.set_next(frame)
        elif ( string.upper(verb) == "STEP" ):
            self.cmd = STEP
            self.set_step()
        elif ( string.upper(verb) == "RUN" ):
            self.cmd = RUN
            self.set_continue()
        elif ( string.upper(verb) == "STOP"):
            self.cmd = QUIT  
            self.quiting()
        elif ( string.upper(verb) == "BP+"):
            self.cmd = SET_BP
            # split the command line argument on the last blank
            col = string.rfind( arg, ' ' )
            arg ,optarg  = arg[:col].strip(),arg[col+1:]
            self.set_break( arg , int(optarg) )
            self.cmd = FREEZE 
        elif ( string.upper(verb) == "STACK"):
            self.cmd = STACK
            self.dealWithStack(frame)
            self.cmd = FREEZE 
        elif ( string.upper(verb) == "LOCALS"):
            self.variablesSubCommand( frame , verb , arg , LOCALS )
        elif ( string.upper(verb) == "GLOBALS"):
            self.variablesSubCommand( frame , verb , arg , GLOBALS )
        elif ( string.upper(verb) == "COMPOSITE"):
            self.cmd=COMPOSITE
            arg , optarg = self.nextArg(arg) # split BP arguments  
            self.dealsWithComposites( arg ,  frame.f_globals ,  frame.f_locals )
            self.cmd = FREEZE
        elif ( string.upper(verb) == "BP-"):
            self.cmd = CLEAR_BP
            arg , optarg = self.nextArg(arg) # split BP arguments  
            self.clear_break( arg , int(optarg) )
            self.cmd = FREEZE 
        return self.cmd       
      
    # send command result back 
    def populateCommandToClient( self , command , result ):
        self.populateToClient( [ '<' + result[0] , 
                               'cmd="' + _utils.removeForXml(command) +'"' ,
                               'operation="' + _utils.removeForXml(__builtin__.str(result[1]))+'"' ,
                               'result="' +__builtin__.str(result[2])+'"' ,
                               '/>' ] )
        if ( result[3] != None ):
            for element in result[3]:
#               print strElement
                self.populateToClient( [ '<COMMANDDETAIL ' ,
                                       'content="'+ _utils.removeForXml(element)+'"',
                                       ' />'
                                      ]
                                    )
        # complementary TAG may be provided starting at position 4
        if len(result) > 4 and (result[4]!=None):
            self.populateToClient( result[4] )
        # mark the end of <COMMANDDETAIL> message transmission 
        self.populateToClient( [ '<COMMANDDETAIL/>' ] ) 
      
      
    # check and execute a received command
    def parseCommand( self , command ):
        # IP exception populating None object  
        if ( command == None ):
            return 0 # => stop daemon
      
        if ( self.verbose ):   
            print command
        result = self.parseSingleCommand(command)
        if ( result == None ):
            self.populateToClient( ['<TERMINATE/>'] )
            return 0 # stop requested
        self.populateCommandToClient( command , result )
        return 1
    
    # reading on network 
    def readNetBuffer( self ):
        try:
            if ( self.lastBuffer.find('\n') != -1 ):
                return self.lastBuffer ; # buffer stills contains commands
            networkData = self.connection.recv(1024)
            if not networkData:  # capture network interuptions if any
                return None
            data = self.lastBuffer + networkData
            return data
        except socket.error, (errno,strerror):
            print "recv interupted errno(%s) : %s" % ( errno , strerror )
            return None
          
    
    # receive a command from the net 
    def _receiveCommand( self ):
        data = self.readNetBuffer() ;
        # data reception from Ip
        while ( data != None and data):
            eocPos = data.find('\n')
            nextPos = eocPos ;
            while (  nextPos < len(data) and \
                   ( data[nextPos] == '\n' or data[nextPos] == '\r') ): # ignore consecutive \n\r
                nextPos = nextPos+1     
            if ( eocPos != -1 ): # full command received in buffer
                self.lastBuffer = data[nextPos:] # cleanup received command from buffer
                returned = data[:eocPos]
                if (returned[-1] == '\r'):
                    return returned[:-1]
                return returned  
            data = self.readNetBuffer() ; 
        # returning None on Ip Exception
        return None 

    # start the deamon 
    def start( self , port = PORT , host = None , debuggee = None ,debuggeeArgs = None ):
        if ( host == None ):
            # start in listen mode waiting for incoming sollicitors   
            print "JPyDbg listening on " , port 
            s = socket.socket( socket.AF_INET , socket.SOCK_STREAM )
            s.bind( (HOST , port) )
            s.listen(1)
            self.connection , addr = s.accept()
            print "connected by " , addr
        else:
            # connect back provided listening host
            print "JPyDbg connecting " , host , " on port " , port 
            try:   
                self.connection = socket.socket( socket.AF_INET , socket.SOCK_STREAM )
                self.connection.connect( (host , port) )
                print "JPyDbgI0001 : connected to " , host
            except socket.error, (errno,strerror):
                print "ERROR:JPyDbg connection failed errno(%s) : %s" % ( errno , strerror )
                return None
        welcome = [ '<WELCOME/>' ]
        # populate debuggee's name for remote debugging bootstrap
        if debuggee != None:
            welcome = [ '<WELCOME' ,  
                        'debuggee="'+ _utils.removeForXml(debuggee)]
            if debuggeeArgs != None:
                welcome.append(string.join(debuggeeArgs))
              # populate arguments after program Name
            # finally append XML closure  
            welcome.append('" />')
          
        self.populateToClient( welcome )
        while ( self.parseCommand( self._receiveCommand() ) ):
            pass    
          
        print "'+++ JPy/sessionended/"
        self.connection.close()
#
# consume requested sys.argv and return its value back
#
def consumeArgv( containing=None ):
    if (len(sys.argv) > 1):
        returned = sys.argv[1]
        if ( containing != None ):
            # check matching
            if returned.find(containing) == -1:
                return None #don't match
        #  consume and return value    
        sys.argv =  [sys.argv[0]] + sys.argv[2:]
        return returned
    else:
        return None

#
# Instanciate a client side debugging session
#
def remoteDbgSession( localDebuggee , host , port=PORT , args = None ):
    minstance = JPyDbg()
    minstance.start( host=host , 
                     port=port , 
                     debuggee=localDebuggee ,
                     debuggeeArgs=args
                   )

# start a listening instance when invoked as main program
# without arguments
# when [host [port]] are provided as argv jpydamon will try to
# connect back host port instead of listening
if __name__ == "__main__":
    instance = JPyDbg()
    print "args = " , sys.argv
    host = consumeArgv()
    port = consumeArgv()
    if port == None:
        port = PORT
    else:
        port = int(port)
    # starting with version 0.0.9 of jpydbg the 4th parameter
    # is assumed to point to the name of a file containing the pythonPath 
    # string 
    # starting with version 0.0.10 Jython debugging is supported as well
    if ( os.name == "java" ):
        pathArgs = "JYTHONPATH"
    else:
        pathArgs = "PYTHONPATH"
    
    pyPathArg = consumeArgv(pathArgs)
    if (pyPathArg != None ):
        pythonPath = PythonPathHandler(pyPathArg)
        pythonPath.getPyPathFromFile()
    # finally get the optional local debuggee  
    localDebuggee = consumeArgv()
    print "localDebuggee=" , localDebuggee
    #
    instance.start( host=host , 
                    port=port , 
                    debuggee=localDebuggee ,
                    debuggeeArgs=sys.argv
                  )
    print "deamon ended\n"

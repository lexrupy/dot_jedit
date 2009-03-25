#! /usr/bin/env python

__version__ ='$Revision: 1.1 $'
__date__ ='$Date: 2006/01/04 16:13:34 $'
# $Source: /cvsroot/jpydbg/jpydebugforge/java/org/jymc/jpydebug/python/inspector.py,v $

import sys
import traceback
import os
import symbol
import token 

from dbgutils import *

from types import ListType, TupleType

def get_docs( mysource , basename ):
    """Retrieve information from the parse tree of a source file.

    source
        source code to parse.
    """
    import parser
    ast = parser.suite(mysource)
    return ModuleInfo(ast.totuple(1), basename)


class SuiteInfoBase:
    _docstring = ''
    _name = ''

    def __init__(self, tree = None):
        self._class_info = {} 
        self._function_info = {}
        self._import_info = {}
        if tree:
            if sys.version_info[0] == 2 and sys.version_info[1] >= 4:   
            #  
                self._extract_info_24(tree)
            else:
                self._extract_info(tree)

    def _extract_name( self , importNameSubtree ):
        retName = ''
        for nameElement in importNameSubtree:
            retName = retName + nameElement[1]
        return retName
      
    def _resolv_name( self , importName ):
        # import it to get imports path informations back
        try:
            pathName = __import__(importName)
            pathName = str(pathName)
            if pathName.find('(built-in)') != -1 :
                pathName ="builtin"
            else:  
                pathName = pathName.split()[3]
                pathName = pathName[1:-2]
        except :
            pathName ="import failure"
        pass
        return pathName
            
    def _extract_info(self, tree):
        # ignore encoding declarations patch provided byStefanRank
        if len(tree) == 3: 
            tree = tree[1] 
        # extract docstring
        if len(tree) == 2:
            found, myvars = match(DOCSTRING_STMT_PATTERN[1], tree[1])
        else:
            found, myvars = match(DOCSTRING_STMT_PATTERN, tree[3])
        if found:
            self._docstring = eval(vars['docstring'])
        # discover inner definitions
        for node in tree[1:]:
            found, myvars = match(COMPOUND_STMT_PATTERN, node)
            if found:
                cstmt = myvars['compound']
                if cstmt[0] == symbol.funcdef:
                    name = cstmt[2][1]
                    self._function_info[name] = FunctionInfo(cstmt)
                elif cstmt[0] == symbol.classdef:
                    name = cstmt[2][1]
                    self._class_info[name] = ClassInfo(cstmt)
            else:
                found, myvars = match(SMALL_STMT_PATTERN, node)
                if found:
                    cstmt = myvars['small'] 
                    if cstmt[0] == symbol.import_stmt:
                        if cstmt[1][1] != 'from':
                            name = self._extract_name(cstmt[2][1][1:])
                            location = self._resolv_name(name)
                            line = cstmt[2][1][1][2]
                            cstmt = cstmt[3:]
                        else:
                            name =  self._extract_name(cstmt[2][1:])
                            location = self._resolv_name(name)
                            line = cstmt[2][1][2]
                            cstmt = cstmt[3:]
                        self._import_info[name] = ImportInfo(name, 
                                                             line, 
                                                             location)
                        # handling import list
                        while ( len(cstmt) > 0 and cstmt[0][0] == token.COMMA ):
                            line = cstmt[1][1][1][2]
                            name = cstmt[1][1][1][1]
                            location = self._resolv_name(name)
                            self._import_info[name] = ImportInfo(name, 
                                                                 line,
                                                                 location)
                            cstmt = cstmt[2:]


    def _extract_info_24(self, tree):
        # Thanks to Zacharie MacGrew for providing this patch 
        # for supporting python 2.4 AST changes 
        # extract docstring
        
        # ignore encoding declarations patch provided by StefanRank
        if len(tree) == 3: 
            tree = tree[1]
            
        if len(tree) == 2:
            found, myvars = match(DOCSTRING_STMT_PATTERN[1], tree[1])
        else:
            found, myvars = match(DOCSTRING_STMT_PATTERN, tree[3])

        if found:
            self._docstring = eval(myvars['docstring'])
        # discover inner definitions
        for node in tree[1:]:
            found, myvars = match(COMPOUND_STMT_PATTERN, node)
            if found:
                cstmt = myvars['compound']
                if cstmt[0] == symbol.funcdef:
                    name = cstmt[2][1]
                    self._function_info[name] = FunctionInfo(cstmt)
                elif cstmt[0] == symbol.classdef:
                    name = cstmt[2][1]
                    self._class_info[name] = ClassInfo(cstmt)
            else:
                found, myvars = match(SMALL_STMT_PATTERN, node)

		if found:
		    cstmt = myvars['small']
		    cstmt = list(cstmt)
		    cstmt[1] = list(cstmt[1])

		    for s in range(len(cstmt[1])):
			try:
			    cstmt[1][s] = list(cstmt[1][s])
			except:
			    pass

		    if cstmt[0] == symbol.import_stmt:
			if cstmt[1][0] != symbol.import_from:
			    if cstmt[1][2][1][0] == symbol.dotted_as_name: #Expect Name of import
				if cstmt[1][2][1][1][0] == symbol.dotted_name: #Name of import
				    name = cstmt[1][2][1][1][1][1] #Wow! That's insanely deep! -- Name
				    location = self._resolv_name(name)
				    line = cstmt[1][2][1][1][1][2] #Wow! That's insanely deep! -- Line #
				    cstmt[1][2] = cstmt[1][2][2:]
			else:
			    name = cstmt[1][2][1][1]
			    location = self._resolv_name(name)
			    line = cstmt[1][2][1][2]
			    cstmt[1][2] = cstmt[1][2][2:]

			self._import_info[name] = ImportInfo(name, line, location)

			# handling import list
			while ( len(cstmt[1][2]) > 2):
			    if cstmt[1][2][1][0] == symbol.dotted_as_name: #Expect Name of import
				if cstmt[1][2][1][1][0] == symbol.dotted_name: #Name of import
				    name = cstmt[1][2][1][1][1][1] #Wow! That's insanely deep! -- Name
				    location = self._resolv_name(name)
				    line = cstmt[1][2][1][1][1][2] #Wow! That's insanely deep! -- Line #
				    self._import_info[name] = ImportInfo(name, line, location)
			    cstmt[1][2] = cstmt[1][2][2:]


    def get_docstring(self):
        return self._docstring

    def get_name(self):
        return self._name

    def get_class_names(self):
        return self._class_info.keys()

    def get_class_info(self, name):
        return self._class_info[name]

    def get_import_names(self):
        return self._import_info.keys()

    def get_import_info(self, name):
        return self._import_info[name]

    def __getitem__(self, name):
        try:
            return self._class_info[name]
        except KeyError:
            return self._function_info[name]



class ImportInfo(SuiteInfoBase):
    def __init__(self, name , line , location):
        self._name = name
        self._lineNo = line
        self._location = location

    def get_DeclareLineNo( self ):
        return self._lineNo
        

class SuiteFuncInfo:
    #  Mixin class providing access to function names and info.

    def get_function_names(self):
        return self._function_info.keys()

    def get_function_info(self, name):
        return self._function_info[name]


class FunctionInfo(SuiteInfoBase):
    def __init__(self, tree = None):
        self._name = tree[2][1]
        self._lineNo = tree[2][2]
        self._args = []
        self.argListInfos( tree[3] )
        SuiteInfoBase.__init__(self, tree and tree[-1] or None)

    def get_DeclareLineNo( self ):
        return self._lineNo
        
    def argListInfos( self , tree ):
        argType = tree[0]
        if argType == symbol.parameters:
            self.argListInfos(tree[2])
        elif argType == symbol.varargslist:
            for arg in tree[1:]:
                self.argListInfos(arg)
        elif argType == symbol.fpdef:
            self._args.append(tree[1])

class ClassInfo(SuiteInfoBase):
    def __init__(self, tree = None):
        self._name = tree[2][1]
        self._lineNo = tree[2][2]
        SuiteInfoBase.__init__(self, tree and tree[-1] or None)

    def get_method_names(self):
        return self._function_info.keys()

    def get_method_info(self, name):
        return self._function_info[name]

class ModuleInfo(SuiteInfoBase, SuiteFuncInfo):
    def __init__(self, tree = None, name = "<string>"):
        self._name = name
        SuiteInfoBase.__init__(self, tree)
        if tree:
            found, myvars = match(DOCSTRING_STMT_PATTERN, tree[1])
            if found:
                self._docstring = myvars["docstring"]


def match(pattern, data, myvars=None):
    """Match `data' to `pattern', with variable extraction.

    pattern
        Pattern to match against, possibly containing variables.

    data
        Data to be checked and against which variables are extracted.

    vars
        Dictionary of variables which have already been found.  If not
        provided, an empty dictionary is created.

    The `pattern' value may contain variables of the form ['varname'] which
    are allowed to match anything.  The value that is matched is returned as
    part of a dictionary which maps 'varname' to the matched value.  'varname'
    is not required to be a string object, but using strings makes patterns
    and the code which uses them more readable.

    This function returns two values: a boolean indicating whether a match
    was found and a dictionary mapping variable names to their associated
    values.
    """
    if myvars is None:
        myvars = {}
    if type(pattern) is ListType and len(pattern) >= 1:
        # 'variables' are ['varname']
        myvars[pattern[0]] = data
        return 1, myvars
    if type(pattern) is not TupleType:
        return (pattern == data), myvars
    if len(data) != len(pattern):
        return 0, myvars
    for pattern, data in map(None, pattern, data):
        same, myvars = match(pattern, data, myvars)
        if not same:
            break
    return same, myvars


#  This pattern identifies compound statements, allowing them to be readily
#  differentiated from simple statements.
#
COMPOUND_STMT_PATTERN = (
    symbol.stmt,
    (symbol.compound_stmt, ['compound'])
    )


#  This pattern identifies import statements, allowing them to be readily
#  differentiated from simple statements.
#
SMALL_STMT_PATTERN = (
    symbol.stmt ,
    ( symbol.simple_stmt ,
      ( symbol.small_stmt , ['small'] ) ,
         ( token.NEWLINE, '' , ['ignore'] )
      ))

#  This pattern will match a 'stmt' node which *might* represent a docstring;
#  docstrings require that the statement which provides the docstring be the
#  first statement in the class or function, which this pattern does not check.
#
DOCSTRING_STMT_PATTERN = (
    symbol.stmt,
    (symbol.simple_stmt,
     (symbol.small_stmt,
      (symbol.expr_stmt,
       (symbol.testlist,
        (symbol.test,
         (symbol.and_test,
          (symbol.not_test,
           (symbol.comparison,
            (symbol.expr,
             (symbol.xor_expr,
              (symbol.and_expr,
               (symbol.shift_expr,
                (symbol.arith_expr,
                 (symbol.term,
                  (symbol.factor,
                   (symbol.power,
                    (symbol.atom,
                     (token.STRING, ['docstring'])
                     )))))))))))))))),
     (token.NEWLINE, '')
     ))

class xmlizer:
    "xmlize a provided syntax error or parsed module infos"
  
    def __init__(self , infos , baseName , fName , destFName , error = None ):
        self.Infos = infos
        self.Error = error
        self.Utils = jpyutils()
        self.FileName = fName 
        self.DestFName = destFName
        self.BaseName = baseName

    def populate_error( self ):
        LINESTR = 'line '
        reason = self.Error[len(self.Error)-1]
        lower = self.Error[2].find(LINESTR)+len(LINESTR)
        # higher = self.Error[2].find(',', lower)
        lineNo = self.Error[2][lower:]
        if not lineNo.isdigit():
            pos = 0
            for element in lineNo:
                if not element.isdigit():
                    break
                pos = pos + 1
            lineNo = lineNo[:pos]
        self.Dest.write('<error  fileid="'+ \
                         self.Utils.removeForXml(self.FileName)+ \
                         '" reason="' + \
                         reason + \
                         '" lineno="'+lineNo+'" />' )
    
    def populate_class_infos( self , className ):
        classInfo = self.Infos.get_class_info(className)
        self.Dest.write('<class  name="'+ \
                         self.Utils.removeForXml(className)+ \
                         '" doc="' + \
                         self.Utils.removeForXml(classInfo.get_docstring()) + \
                         '" lineno="'+ str(classInfo._lineNo) +'" >\n' )
        # gather infos about class methods
        methods = classInfo.get_method_names()
        for methodName in methods:
            method = classInfo.get_method_info(methodName)
            self.populate_method_infos(method, methodName)
        self.Dest.write('</class>\n' )
  
    def populate_function_arguments_infos( self , args ):
        for arg in args:
            self.Dest.write('  <argument name="' + \
                            arg[1] + '" lineno="' +\
                            str(arg[2]) + '"/>\n')
                      
    def populate_method_infos( self , method , methodName):
        self.Dest.write('<function  name="'+ \
                         self.Utils.removeForXml(methodName)+ \
                         '" doc="' + \
                         self.Utils.removeForXml(method.get_docstring()) + \
                         '" lineno="'+ str(method._lineNo) +'" >\n' )
        if (len(method._args) != 0):
            self.populate_function_arguments_infos(method._args)
        self.Dest.write("</function>\n")                  
    
    def populate_import_infos( self , importName):
        importInfo = self.Infos.get_import_info(importName)
        self.Dest.write('<import  name="'+ \
                         self.Utils.removeForXml(importName)+ \
                         '" location="'+ \
                         self.Utils.removeForXml(importInfo._location)+ \
                         '" lineno="'+ str(importInfo._lineNo) +'" >\n' \
                       )
        self.Dest.write("</import>\n")                  
    
    def populate_function_infos( self , functionName ):
        functionInfo = self.Infos.get_function_info(functionName)
        self.populate_method_infos(functionInfo, functionName)
    
    def populate_tree( self ):
        self.Dest.write('<module name="'+self.BaseName+'">\n')
        # handle imports first
        imports = self.Infos.get_import_names()
        if len(imports) != 0:
            self.Dest.write("<imports>\n")                  
        for curImport in imports:
            self.populate_import_infos(curImport)
        if len(imports) != 0:
            self.Dest.write("</imports>\n")                  
        # handle local classes if any 
        classes = self.Infos.get_class_names()
        for curClass in classes:
            self.populate_class_infos(curClass)
        # finally deal with non object stuff  
        functions = self.Infos.get_function_names()
        for curFunction in functions:
            self.populate_function_infos(curFunction)
        self.Dest.write("</module>\n")                  
    
    def populate( self ):
        self.Dest = file( self.DestFName , 'w+' )
        self.Dest.write( '<?xml version="1.0"?>\n')
        if self.Error != None:
            self.populate_error()
        else:
            self.populate_tree()
        self.Dest.close()
    
class commander :
    "python source file inspector/introspector"

    def __init__(self , mysource , mydest ):
        "constructor providing python source to inspect"
        self.SourceFile = mysource
        self.DestFile = mydest
        self.Infos = None
        self.BaseName = None
        self.Errors = None
        self.Code = None
  
    def check(self):    
        "make a syntaxic control of provided source "
        # execute requested dynamic command on this side
        fp = open(self.SourceFile,"r")
        sourceStr = fp.read() + "\n"
        # get read of any dos style carriage returnto avoid syntax errors
        sourceStr = sourceStr.replace( '\x0d' ,'')
        try:
            # extract python module name
            self.BaseName = os.path.basename(
                             os.path.splitext(self.SourceFile)[0])
            self.Code = compile( sourceStr , self.SourceFile , "exec" )
            self.Infos = get_docs( sourceStr , self.BaseName )
        except:
            tb , exctype , value = sys.exc_info()
            self.Errors = traceback.format_exception(tb, exctype,value)
            pass

    def serialize(self):
        "store tree in XML file format"
        xml = xmlizer(self.Infos , self.BaseName , 
                      self.SourceFile , self.DestFile , self.Errors )
        xml.populate()
   
# 
# inspector launcher entry point
#
if __name__ == "__main__":
    # inspect jpydaemon itself      
    print "args = " , sys.argv
    utils = jpyutils()
    pyPathHandler = None
    if ( len(sys.argv) > 1 ): 
        source = utils.getArg(sys.argv[1])
    if ( len(sys.argv) > 2 ): 
        dest   = utils.getArg(sys.argv[2])
    if ( len(sys.argv) > 3 ): 
        pyPathHandler   = PythonPathHandler(utils.getArg(sys.argv[3]))
    if ( len(sys.argv) < 3 ): 
        sys.exit(12) # missing arguments
    if pyPathHandler != None:
        pyPathHandler.getPyPathFromFile()
    # Insert script directory in front of module search path
    # and make it current path (#sourceforge REQID 88108 fix)
    debugPath = os.path.dirname(source)
    sys.path.insert(0, debugPath)
    #  
    instance = commander( source , dest)
    instance.check()
    instance.serialize()
    if pyPathHandler != None:
        # remove previously inserted current path 0 node before saving
        del(sys.path[0])
        pyPathHandler.setPyPathFileFromPath()
    pass


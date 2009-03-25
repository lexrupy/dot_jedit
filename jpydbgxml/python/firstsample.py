#
# This sample python file may be used to check jpydbg 
# installation and configuration correctness
#
__revision__ = '$Revision: 1.1 $'
__date__ ='$Date: 2006/01/04 16:13:34 $'
# $Source: /cvsroot/jpydbg/jpydebugforge/java/org/jymc/jpydebug/python/firstsample.py,v $

print "sourceSample loaded name=" ,__name__
#from os import *
import sys
import os  

#
# import mysubsample

import z

#
# A sample List returning function test modified again
#
def buildList():
    "test documentation comment"
    print "this will return a sample constant list back"
    mylist = ["dave" , "mark" , "ann" , "phil"]
    return mylist
#
# A sample multiplication function
#
def multiply( first , second  ):
    print "this shall add " , first , "times " , second
    returned = 0
    for i in range ( 0, long(first) ):
        returned = returned + long(second)
    print i
    return returned

#
# Unit testing startup
#
if __name__ == '__main__':
#   checking for provided parameters
    args = sys.argv
    print "length args=" , len(args)
    if len( args ) > 1 :
        ii = 0 
        for current in args:
            print "arg [" , ii , "]=" , str(args[ii])
            ii = ii + 1
    else:
        print "no argument provided"
# check writeline case on stdout capture
#    mystdout = sys.stdout
#    mystdout.writeline("test writeline implemented in jpydbg")
# test KeyError correct capture on Dict
    print "Hello","World!"
    print "Hello" + ' ' + "World!"
    myvar = "test"
    data = {'last':"Feigenbaum", 'first':"Barry"}
    print data
    myDict = { 'spam':2 , 'zozo':1 }
    try :
        print myDict['riri']
    except KeyError:
        print "we got it "
    print "testing multiply = " , multiply ("5" , "6")
    for ii in xrange(1000):
        print "ii value is = " , ii 
    print "testing multiply = " , multiply (5, 6)
#    print "testing multiply = " , multiply (5,6,7)
#   test uncaptured exception on next line
    print "testing buildlist = " , buildList() 
#    1+''
#    print "strange : we should not be here"
#   print mysubsample.testImporter("zozo")


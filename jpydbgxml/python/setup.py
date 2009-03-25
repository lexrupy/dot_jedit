#!/usr/bin/env python
from distutils.core import setup

setup( name="jpydaemon" , 
       version="0.16" ,
       description="jpydbg python debugger backend + samples" ,
       author="Jean-Yves Mengant" ,
       author_email="jymengant@ifrance.com" ,
       url="http://jpydbg.sourceforge.net"  ,
       py_modules=["jpydaemon" , "firstsample" , "inspector" , 
                                  "dbgutils " ,"pylintlauncher",  "simplejy" , "simplepy" ]
     )


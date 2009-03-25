"""\
Equivalent to the ../awt/simple.py example but using swing components
instead of AWT ones.
"""

# This line will import the appropriate swing library for your system (jdk 1.1 or 1.2)
import org.python.core
from pawt import swing
import java
leaving =0

def exit(e): 
  leaving = 1 
  java.lang.System.exit(0)

frame = swing.JFrame('Hello from Jython', visible=1)
button = swing.JButton('Hello from jython : click here to close Me!', actionPerformed=exit)
frame.contentPane.add(button)
frame.pack()
frame.show()

import time
while not leaving:
  time.sleep(1)

import sys
import numpy as np
import matplotlib.pyplot as plt


import interpies
inFile = r'D:\PycharmProjects\pythonProject\SEG/brtpgrd.gxf'
grid1 = interpies.open(inFile)


ax = grid1.show()



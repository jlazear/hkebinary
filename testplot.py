from matplotlib.pyplot import *
from HKEBinaryFile import HKEBinaryFile as File
from scipy import *
from scipy.interpolate import interp1d

cal = loadtxt('U02728.txt')
calTs, calRs = cal.T
calRs = calRs[::-1]
calTs = calTs[::-1]
TofR = interp1d(calRs, calTs)

f0615_001 = File('hke_20120615_001.dat')
dataT = f0615_001.get_data(0).flatten()
dataR = f0615_001.get_data(-6)
r1 = dataR[...,2]
r1 = sqrt(r1*r1)

t1 = TofR(dataT)

plot(t1, r1, label='SHINY Electronics (I = 10 $\mu A$)')
yscale('log')
xscale('log')
ylabel('$|R_{\mathrm{device}}|$ ($\Omega$)', fontsize='large')
xlabel('T (K)', fontsize='large')
title('R vs T for Characterization Test Chip Channel 1', fontsize='large')
show()

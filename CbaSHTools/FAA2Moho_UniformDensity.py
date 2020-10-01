#!/usr/bin/env python
"""
This script creates a crustal thickness map.
"""
from __future__ import absolute_import, division, print_function

import os
import sys

sys.path.append(r'/Users/dingmin/tutorial_env/lib/python3.7/site-packages') 

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

import pyshtools
from pyshtools import shio
from pyshtools import expand
from pyshtools import gravmag
from pyshtools import constant

pyshtools.utils.figstyle()


# ==== MAIN FUNCTION ====

def main():
    TestCrustalThickness()

# ==== TEST FUNCTIONS ====


def TestCrustalThickness():
    """
    calculates the crustal thickness of the Moon
    """
    delta_max = 5.0 # Default = 5 [m] for convergence criteria
    nmax = 10
    degmax = 600
    lmax = 1200
    rho_c = 2550.0
    rho_m = 3220.0
    filter_type = 1
    half = 110
    Tc_mean = 35e3 # [m] assumed mean crustal thickness

#   gravfile = '../../ExampleDataFiles/gmm3_120_sha.tab'
    gravfile = 'gggrx_1200a_sha.tab'
    pot, lmaxp, header = shio.shread(gravfile, lmax=degmax, header=True)
    gm = float(header[1]) * 1.e9
    mass = gm / constant.G.value
    r_grav = float(header[0]) * 1.e3
    print(r_grav, gm, mass, lmaxp)

#   topofile = '../../ExampleDataFiles/MarsTopo719.shape'
    topofile = 'lro_ltm05_2050_sha.tab'
    hlm, lmaxt = shio.shread(topofile)
    r0 = hlm[0, 0, 0]
    d = r0 - Tc_mean
    print(r0, lmaxt)

    for l in range(2, lmaxp + 1):
        pot[:, l, :l + 1] = pot[:, l, :l + 1] * (r_grav / r0)**l

    topo_grid = expand.MakeGridDH(hlm, lmax=lmax, sampling=2,
                                  lmax_calc=degmax)

    print("Maximum radius (km) = ", topo_grid.max() / 1.e3)
    print("Minimum radius (km) = ", topo_grid.min() / 1.e3)

    bc, r0 = gravmag.CilmPlusDH(topo_grid, nmax, mass, rho_c, lmax=degmax)


    ## save BA coefficients before correcting for mare 
    ba_tmp = pot - bc 
    for l in range(2, lmaxp + 1):
        ba_tmp[:, l, :l + 1] = ba_tmp[:, l, :l + 1] * (r0 / r_grav)**l
    
    Cba_grid = expand.MakeGridDH(ba_tmp, lmax=degmax, sampling=2,lmax_calc=degmax)
    np.savetxt('BAcoef_UniformDensity.out',Cba_grid)

    ba = pot - bc

    moho_c = np.zeros([2, degmax + 1, degmax + 1], dtype=float)
    moho_c[0, 0, 0] = d

    for l in range(1, degmax + 1):
        if filter_type == 0:
            moho_c[:, l, :l + 1] = ba[:, l, :l + 1] * mass * (2 * l + 1) * \
                                   ((r0 / d)**l) \
                                   / (4.0 * np.pi * (rho_m - rho_c) * d**2)
        elif filter_type == 1:
            moho_c[:, l, :l + 1] = gravmag.DownContFilterMA(l, half, r0, d) * \
                                   ba[:, l, :l + 1] * mass * (2 * l + 1) * \
                                   ((r0 / d)**l) / \
                                   (4.0 * np.pi * (rho_m - rho_c) * d**2)
        else:
            moho_c[:, l, :l + 1] = gravmag.DownContFilterMC(l, half, r0, d) * \
                                   ba[:, l, :l + 1] * mass * (2 * l + 1) *\
                                   ((r0 / d)**l) / \
                                   (4.0 * np.pi * (rho_m - rho_c) * d**2)

    moho_grid3 = expand.MakeGridDH(moho_c, lmax=lmax, sampling=2,
                                   lmax_calc=degmax)
    print('Maximum Crustal thickness (km) = ',
          (topo_grid - moho_grid3).max() / 1.e3)
    print('Minimum Crustal thickness (km) = ',
          (topo_grid - moho_grid3).min() / 1.e3)

    moho_c = gravmag.BAtoHilmDH(ba, moho_grid3, nmax, mass, r0,
                                (rho_m - rho_c), lmax=lmax,
                                filter_type=filter_type, filter_deg=half,
                                lmax_calc=degmax)

    moho_grid2 = expand.MakeGridDH(moho_c, lmax=lmax, sampling=2,
                                   lmax_calc=degmax)
    print('Delta (km) = ', abs(moho_grid3 - moho_grid2).max() / 1.e3)

    temp_grid = topo_grid - moho_grid2
    print('Maximum Crustal thickness (km) = ', temp_grid.max() / 1.e3)
    print('Minimum Crustal thickness (km) = ', temp_grid.min() / 1.e3)

    iter = 0
    delta = 1.0e9

    while delta > delta_max:
        iter += 1
        print('Iteration ', iter)

        moho_grid = (moho_grid2 + moho_grid3) / 2.0
        print("Delta (km) = ", abs(moho_grid - moho_grid2).max() / 1.e3)

        temp_grid = topo_grid - moho_grid
        print('Maximum Crustal thickness (km) = ', temp_grid.max() / 1.e3)
        print('Minimum Crustal thickness (km) = ', temp_grid.min() / 1.e3)

        moho_grid3 = moho_grid2
        moho_grid2 = moho_grid

        iter += 1
        print('Iteration ', iter)

        moho_c = gravmag.BAtoHilmDH(ba, moho_grid2, nmax, mass, r0,
                                    rho_m - rho_c, lmax=lmax,
                                    filter_type=filter_type, filter_deg=half,
                                    lmax_calc=degmax)

        moho_grid = expand.MakeGridDH(moho_c, lmax=lmax, sampling=2,
                                      lmax_calc=degmax)
        delta = abs(moho_grid - moho_grid2).max()
        print('Delta (km) = ', delta / 1.e3)

        temp_grid = topo_grid - moho_grid
        print('Maximum Crustal thickness (km) = ', temp_grid.max() / 1.e3)
        print('Minimum Crustal thickness (km) = ', temp_grid.min() / 1.e3)

        moho_grid3 = moho_grid2
        moho_grid2 = moho_grid

        if temp_grid.max() > 100.e3:
            print('Not converging')
            exit(1)
        
    temp_grid = temp_grid*1e-3
#    fig_map = plt.figure()
#    im = plt.imshow(temp_grid,cmap='jet')
#    fig_map.colorbar(im, orientation='horizontal')
#    fig_map.savefig('InvCrustalThickness.png')
    np.savetxt('CrustalThickness_UniformDensity.out',temp_grid)

# ==== EXECUTE SCRIPT ====
if __name__ == "__main__":
    main()

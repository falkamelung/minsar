#!/usr/bin/env python3
# Author: Farzaneh Aziz Zanjani               
# This script plot velocity, DEM error, and estimated elevation on the backscatter.
############################################################
import argparse
import os
import numpy as np
import glob
import matplotlib.pyplot as plt
import matplotlib
import mintpy
from osgeo import gdal
from mintpy.utils import plot as pp
from mintpy.utils import readfile, utils as ut 
import h5py
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from mintpy import view
from mintpy.objects import timeseries
from operator import itemgetter 
import datetime
from datetime import timedelta
from scipy import interpolate
import matplotlib.dates as mdates
from miaplpy.objects.invert_pixel import process_pixel 
from scipy import stats
from mpl_toolkits.axes_grid1 import make_axes_locatable
from miaplpy.dev import modified_dem_error
from miaplpy import correct_geolocation as corg

import matplotlib.ticker as mticker
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

####
# @Fari: This should be done in function cmd_line_parser
# @Fari: also there should be a main() function.
# @Fari: and all arrays/variables that are used by get_data() should be given in the function call. Same for the otehr functions
# use 26 as default for offset?
parser = argparse.ArgumentParser(description='plots velocity, DEM error, and estimated elevation on the backscatter')
parser.add_argument('project_dir', metavar='project_dir', type=str, help='enter your data address that includes input files for either sequential network or single reference defined as ../../dsm_reprojected_wgs84.tif, demErr.h5, velocity.h5, ../inputs/geometryRadar.h5, /../inputs/slcStack.h5, timeseries_demErr.h5, maskPS.h5, maskTempCoh.h5')
parser.add_argument('lat1', metavar='lat1', type=float, help='low latitude of the box')
parser.add_argument('lon1', metavar='lon1', type=float, help='low longitude of the box')
parser.add_argument('lat2', metavar='lat2', type=float, help='high latitude of the box')
parser.add_argument('lon2', metavar='lon2', type=float, help='high longitude of the box')
parser.add_argument('outfile', metavar='outfile', type=str, help='output png file name')

parser.add_argument('--vrange', '-v', type=float, help='velocity range')
parser.add_argument('--srtml', '-dsl', type=float, help='Dem SRTM low limit for color bar')
parser.add_argument('--srtmh', '-dsh', type=float, help='Dem SRTM high limit for color bar')
parser.add_argument('--demerl', '-el', type=float, help='Dem error low limit for color bar')
parser.add_argument('--demerh', '-eh', type=float, help='Dem error high limit for color bar')
parser.add_argument('--elel', '-elel', type=float, help='Estimated elevation low limit for color bar')
parser.add_argument('--eleh', '-eleh', type=float, help='Estimated elevation high limit for color bar')

parser.add_argument('--psize', '-s', type=float, help='points size')
parser.add_argument('--offset', '-d', type=float, help='dem offset e.g., it is 26 for Miami')
parser.add_argument('--fontsize', '-f', type=float, help='font size')
parser.add_argument('--figsizey', '-figy', type=float, help='figure size in y direction')
parser.add_argument('--figsizex', '-figx', type=float, help='figure size in x direction')

args = parser.parse_args()

project_dir = args.project_dir
lat1=args.lat1
lat2=args.lat2
lon1=args.lon1
lon2=args.lon2

outfile=args.outfile
####
#### Input files
#out_dir = './out_figures'
out_dir = '.'
out_amplitude = project_dir + '/mean_amplitude.npy'
geom_dsm = '/work2/05861/tg851601/stampede2/insarlab/DEM/Miami_DSM/dsm_reprojected_wgs84.tif'   
geom_dsm = project_dir + '/../../dsm_reprojected_wgs84.tif'
demError_file = project_dir + '/demErr.h5'
##demError_std_file = project_dir + '/demErr_std.h5'
vel_file = project_dir + '/velocity.h5'
geo_file = project_dir + '/../inputs/geometryRadar.h5'
mask_file_t = project_dir + '/maskTempCoh.h5'
mask_file_ps = project_dir + '/../maskPS.h5'
#mask_file_w = project_dir + '/waterMask.h5'
tsStack = project_dir + '/timeseries_demErr.h5'
#tsStack = project_dir + '/timeseries_ERA5_demErr.h5'
slcStack = project_dir + '/../inputs/slcStack.h5'
##### 
def calculate_mean_amplitude(slcStack, out_amplitude):
    with h5py.File(slcStack, 'r') as f:
        slcs = f['slc']
        s_shape = slcs.shape
        mean_amplitude = np.zeros((s_shape[1], s_shape[2]), dtype='float32')
        lines = np.arange(0, s_shape[1], 100)
        for t in lines:
            last = t + 100
            if t == lines[-1]:
                lst = s_shape[1]

            mean_amplitude[t:last, :] = np.mean(np.abs(f['slc'][:,t:last,:]), axis=0)
            np.save(out_amplitude, mean_amplitude)
    return



def get_data(ymin, ymax, xmin, xmax, ps, out_amplitude, shift=0):
 
    velocity, atr = readfile.read(vel_file, datasetName='velocity')

    if ymin >= ymax:
       tmp_ymin = ymin
       tmp_ymax = ymax
       ymin = tmp_ymax 
       ymax = tmp_ymin 
    if xmin >= xmax:
       tmp_xmin = xmin
       tmp_xmax = xmax
       xmin = tmp_xmax 
       xmax = tmp_xmin 

    # needed as for Tsx there is no ORBIT_DIRECTION attribute
    try:
        orbit_direction = attr['ORBIT_DIRECTION']
    except:
        result_list = []
        for x in ['TsxSMAT','TsxSLAT','TsxSTAT''TsxHSAT','CskAT']:
            result_list.append(x in project_dir )
        if any(result_list):
            orbit_direction = 'ASCENDING'

        for x in ['TsxSMDT','TsxSLDT','TsxSTDT','TsxHSDT','TsxSMD','CskDT']:
            result_list.append(x in project_dir )
        if any(result_list):
            orbit_direction = 'DESCENDING'

    if orbit_direction == 'ASCENDING':
        flipud_flag = True
        fliplr_flag = False
    if orbit_direction == 'DESCENDING':
        flipud_flag = False
        fliplr_flag = True

    # need to check in view.py how Yunjun is doing the flipping and whetehr it works for TSX (does he has the ORBIT_DIRECTION attribute?)
    if flipud_flag:
       DEM = np.flipud(readfile.read(geo_file, datasetName='height')[0][ymin:ymax, xmin:xmax]) + shift
       demError = np.flipud(readfile.read(demError_file, datasetName='dem')[0][ymin:ymax, xmin:xmax])
       amplitude = np.flipud(np.load(out_amplitude)[ymin:ymax, xmin:xmax]) 
       mask_t = np.flipud(readfile.read(mask_file_t, datasetName='mask')[0][ymin:ymax, xmin:xmax])
       mask_p = np.flipud(readfile.read(mask_file_ps, datasetName='mask')[0][ymin:ymax, xmin:xmax])
       if ps:
           mask = mask_p
       else:
           mask=mask_t
       velocity = np.flipud(velocity[ymin:ymax, xmin:xmax])
    if fliplr_flag:
       DEM = np.fliplr(readfile.read(geo_file, datasetName='height')[0][ymin:ymax, xmin:xmax]) + shift
       demError = np.fliplr(readfile.read(demError_file, datasetName='dem')[0][ymin:ymax, xmin:xmax])
       amplitude = np.fliplr(np.load(out_amplitude)[ymin:ymax, xmin:xmax]) 
       mask_t = np.fliplr(readfile.read(mask_file_t, datasetName='mask')[0][ymin:ymax, xmin:xmax])
       mask_p = np.fliplr(readfile.read(mask_file_ps, datasetName='mask')[0][ymin:ymax, xmin:xmax])
       if ps:
           mask = mask_p
       else:
           mask=mask_t
       velocity = np.fliplr(velocity[ymin:ymax, xmin:xmax])
  
    vel = velocity[mask==1]*1000
    demerr = demError[mask==1]
    dem = DEM[mask==1]
   # demerror_std = demError_std[mask==1]

    x = np.linspace(0, velocity.shape[1]-1, velocity.shape[1])
    y = np.linspace(0, velocity.shape[0]-1, velocity.shape[0])
    x, y = np.meshgrid(x, y)

    xv = x[mask==1]
    yv = y[mask==1]
   
    return amplitude, xv, yv, vel, demerr, dem, DEM, atr
    

def plot_subset(ymin, ymax, xmin, xmax, ps, vel_range, amplitude_im, dem_offset, dem_name, out_name, out_dir, size=200):
    
    plt.switch_backend('Agg')
    #import pdb; pdb.set_trace()
    amplitude, xv, yv, vel, demerr, dem, DEM, atr = get_data(ymin, ymax, xmin, xmax, ps, amplitude_im, dem_offset)

    if args.figsizey and args.figsizex is not None:
       fs=(args.figsizey,args.figsizey) 
    else:
       fs=(13, 4.5) 
    fig, axs = plt.subplots(nrows=1, ncols=5,figsize=fs)

    ax = axs[0]
    ax.imshow(amplitude, cmap='gray', vmin=0, vmax=300)
    im = ax.scatter(xv, yv, c=vel/10, s=size, cmap='jet', vmin=-vel_range, vmax=vel_range); 
    cbar = plt.colorbar(im, ax=ax, shrink=1, orientation='horizontal', pad=0.04)
    if args.vrange is not None:
        im.set_clim(-args.vrange, args.vrange)
    else:
        im.set_clim(-0.6, 0.6)
    
    cbar.set_label('velocity [cm/yr]')
    
    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)

    ax = axs[1]
    im=ax.imshow(amplitude, cmap='gray', vmin=0, vmax=300)
    cbar = plt.colorbar(im, ax=ax, shrink=1, orientation='horizontal', pad=0.04)
    cbar.set_label('Amplitude')
    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)

    ax = axs[2]
    ax.imshow(amplitude, cmap='gray', vmin=0, vmax=300)
    im = ax.scatter(xv, yv, c=dem, s=size, cmap='jet'); 
    cbar = plt.colorbar(im, ax=ax, shrink=1, orientation='horizontal', pad=0.04)
    cbar.set_label('SRTM DEM [m]')
    if args.srtml and args.srtmh is not None:
       im.set_clim(args.srtml, args.srtmh)
    
    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)


    ax = axs[3]
    ax.imshow(amplitude, cmap='gray', vmin=0, vmax=300)
    im = ax.scatter(xv, yv, c=-demerr, s=size, cmap='jet'); 
    cbar = plt.colorbar(im, ax=ax, shrink=1, orientation='horizontal', pad=0.04)
    cbar.set_label('DEM Error [m]')
    if args.demerl and args.demerh is not None:
       im.set_clim(args.demerl, args.demerh)
    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)

    ax = axs[4]
    ax.imshow(amplitude, cmap='gray', vmin=0, vmax=300)
    im = ax.scatter(xv, yv, c=-demerr+dem, s=size, cmap='jet');
    cbar = plt.colorbar(im, ax=ax, shrink=1, orientation='horizontal', pad=0.04)
    cbar.set_label('Estimated \nelevation [m]')
    if args.demerl and args.demerh is not None:
       im.set_clim(args.elel, args.eleh)
    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)
    
    ax.axes.get_yaxis().set_visible(False)
    
    if ps:
        psds = 'ps'
    else:
        psds = 'ds'
    plt.savefig(out_dir + '/{}_{}_{}.png'.format(out_name, dem_name, psds), bbox_inches='tight', dpi=300)

######

if args.fontsize is not None:
    f=args.fontsize
else:
    f=10

plt.rcParams["font.size"] = f

if not os.path.exists(out_amplitude):
   calculate_mean_amplitude(slcStack, out_amplitude)

#points_lalo = np.array([[25.875, -80.122],
#                  [25.8795, -80.121]])

points_lalo = np.array([[lat1, lon1],
                  [lat2, lon2]])
print (points_lalo)

attr = readfile.read_attribute(tsStack)
coord = ut.coordinate(attr, geo_file)
yg1, xg1 = coord.geo2radar(points_lalo[0][0], points_lalo[0][1])[0:2]
yg2, xg2 = coord.geo2radar(points_lalo[1][0], points_lalo[1][1])[0:2]
print (yg1, xg1, yg2, xg2)

yg1, xg1 = coord.geo2radar(points_lalo[0][0], points_lalo[0][1])[0:2]
yg2, xg2 = coord.geo2radar(points_lalo[0][0], points_lalo[1][1])[0:2]
yg3, xg3 = coord.geo2radar(points_lalo[1][0], points_lalo[0][1])[0:2]
yg4, xg4 = coord.geo2radar(points_lalo[1][0], points_lalo[1][1])[0:2]
print("Lat, Lon, y, x: ",points_lalo[0][0], points_lalo[0][1], yg1, xg1)
print("Lat, Lon, y, x: ",points_lalo[0][0], points_lalo[1][1], yg2, xg2)
print("Lat, Lon, y, x: ",points_lalo[1][0], points_lalo[0][1], yg3, xg3)
print("Lat, Lon, y, x: ",points_lalo[1][0], points_lalo[1][1], yg4, xg4)
print (yg1, xg1, yg2, xg2, yg3, xg3, yg4, xg4)
ymin = min(yg1, yg2, yg3, yg4)
ymax = max(yg1, yg2, yg3, yg4)
xmin = min(xg1, xg2, xg3, xg4)
xmax = max(xg1, xg2, xg3, xg4)
print (ymin, xmin, ymax, xmax)
#import pdb; pdb.set_trace()

if args.psize is not None:
        size=args.psize
else:
        size=10

if args.vrange is not None:
        vel=args.vrange
else:
        vel=0.6

if args.offset is not None:
        doff=args.offset
else:
        doff=26

plot_subset(ymin=ymin, ymax=ymax, xmin=xmin, xmax=xmax, ps=True, vel_range=vel,
            amplitude_im=out_amplitude, dem_offset=doff, dem_name='dem', 
            out_name=outfile, out_dir=out_dir, size=size)

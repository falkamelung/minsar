#! /usr/bin/env python3
"""
   Author: Falk Amelung, Sara Mirzaee
"""
###############################################################################

import os
import sys
import glob
import subprocess
import h5py
import math
import shutil

from mintpy.utils import readfile
import minsar.utils.process_utilities as putils
from minsar.objects.auto_defaults import PathFind
from minsar.objects import message_rsmas
from minsar.objects.dataset_template import Template

pathObj = PathFind()


###########################################################################################


def main(iargs=None):
    """ create template files for chunk processing """

    inps = putils.cmd_line_parse(iargs, script='generate_chunk_template_files')

    os.chdir(inps.work_dir)

    if not iargs is None:
        input_arguments = iargs
    else:
        input_arguments = sys.argv[1::]

    message_rsmas.log(inps.work_dir, os.path.basename(__file__) + ' ' + ' '.join(input_arguments))

    run_generate_chunk_template_files(inps)

    return

###################################################


def  run_generate_chunk_template_files(inps):
    """ create e*chunk*.template files """

    project_name = putils.get_project_name(inps.custom_template_file)

    location_name, sat_direction, sat_track = putils.split_project_name(project_name)

    location_name = location_name.split('Big')[0]

    chunk_templates_dir = inps.work_dir + '/chunk_templates'
    chunk_templates_dir_string = '$SCRATCHDIR/' + project_name + '/chunk_templates'
    os.makedirs(chunk_templates_dir, exist_ok=True)

    command_list = []
    sleep_time = 0

    command_options = ''
    if inps.start_step is None and inps.do_step is None:
       inps.start_step = 'jobfiles'

    if inps.do_step is not None:
        command_options =  command_options + ' --dostep ' + inps.do_step
    else:
        if inps.start_step is not None:
            command_options =  command_options + ' --start ' + inps.start_step
        if inps.end_step is not None:
            command_options =  command_options + ' --end ' + inps.end_step

    prefix = 'tops'
    bbox_list = inps.template[prefix + 'Stack.boundingBox'].split(' ')

    bbox_list[0] = bbox_list[0].replace("\'", '')   # this does ["'-8.75", '-7.8', '115.0', "115.7'"] (needed for run_operations.py, run_operations
    bbox_list[1] = bbox_list[1].replace("\'", '')   # -->       ['-8.75',  '-7.8', '115.0', '115.7']  (should be modified so that this is not needed)
    bbox_list[2] = bbox_list[2].replace("\'", '')
    bbox_list[3] = bbox_list[3].replace("\'", '')

    tmp_min_lat = float(bbox_list[0]) 
    tmp_max_lat = float(bbox_list[1])
 
    min_lat = math.ceil(tmp_min_lat)
    max_lat = math.floor(tmp_max_lat)
  
    lat = min_lat
    
    chunk_number = 0
    chunk1_option = ''

    while lat < max_lat:
        tmp_min_lat = lat
        tmp_max_lat = lat + inps.lat_step

        chunk_name =[ location_name + 'Chunk' +  str(int(lat)) + sat_direction + sat_track ] 
        chunk_template_file = chunk_templates_dir + '/' + chunk_name[0] + '.template'
        chunk_template_file_base = chunk_name[0] + '.template'
        shutil.copy(inps.custom_template_file, chunk_template_file)

        chunk_bbox_list = bbox_list
        chunk_bbox_list[0] = str(float(tmp_min_lat-inps.lat_margin))
        chunk_bbox_list[1] = str(float(tmp_max_lat+inps.lat_margin))
        print(chunk_name,tmp_min_lat, tmp_max_lat,chunk_bbox_list)

        custom_tempObj = Template(inps.custom_template_file)
        custom_tempObj.options['topsStack.boundingBox'] = ' '.join(chunk_bbox_list)
        
        slcDir = '$SCRATCHDIR/' + project_name + '/SLC'
        demDir = '$SCRATCHDIR/' + project_name + '/DEM'
        custom_tempObj.options['topsStack.slcDir'] = slcDir
        custom_tempObj.options['topsStack.demDir'] = demDir
        
        #if inps.download_flag in [ True , 'True']:
        #   del(custom_tempObj.options['topsStack.slcDir'])
          
        if 'download' in command_options :
           del(custom_tempObj.options['topsStack.slcDir'])
          
        putils.write_template_file(chunk_template_file, custom_tempObj)
        putils.beautify_template_file(chunk_template_file)

        chunk_number = chunk_number + 1
        if chunk_number > 1 and inps.bash_script == 'minsarApp.bash':
           chunk1_option = ' --no_download_ECMWF '

        command = inps.bash_script + ' ' + chunk_templates_dir_string + '/' + chunk_template_file_base +  command_options + chunk1_option + ' --sleep ' + str(sleep_time) + ' &'

        command_list.append(command)

        lat = lat + inps.lat_step
        sleep_time = sleep_time +inps.wait_time
        chunk1_option = ''
    
    commands_file = inps.work_dir + '/minsar_commands.txt'
    f = open(commands_file, "w")

    print()
    for item in command_list:
       print(item)
       f.write(item + '\n')

    print()
    f.write( '\n')

    return

###########################################################################################

if __name__ == '__main__':
    main(sys.argv[1:])

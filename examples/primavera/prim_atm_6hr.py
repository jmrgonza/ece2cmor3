#!/usr/bin/env python

import os
import sys
import logging
import ece2cmorlib
import ifs2cmor
import cmor_source
import jsonloader
import optparse
import datetime
from dateutil.relativedelta import relativedelta

# This example script performs cmorization of one month of atmosphere data, starting at \
# januari 1st 1990. It requires an output directory and an experiment name/prefix to \
# determine the output data files and configure \
# cmor3 correctly. The processed variables are listed in the "variables" dictionary

def is6hrtask(task):
   if(not isinstance(task.source,cmor_source.ifs_source)): return False
   if(task.target.variable in ["ua850","va850"]): return False
   if(getattr(task.target,"frequency",None) == "3hr"): return False
   return (task.source.spatial_dims == 3)

logging.basicConfig(level=logging.DEBUG)

startdate = datetime.date(1990,1,1)
interval = relativedelta(months=1)
srcdir = os.path.dirname(os.path.abspath(ece2cmorlib.__file__))
curdir = os.path.join(srcdir,"examples","primavera")
datdir = os.path.join(srcdir,"test","test_data","ifsdata","6hr")
tmpdir = os.path.join(curdir,"tmp")
varfile = os.path.join(curdir,"varlist.json")

def main(args):

    parser = optparse.OptionParser()
    parser.add_option("-d","--dir", dest = "dir",  help = "IFS output directory (optional)",       default = datdir)
    parser.add_option("-c","--conf",dest = "conf", help = "Input variable list (optional)",        default = ece2cmorlib.conf_path_default)
    parser.add_option("-e","--exp", dest = "exp",  help = "Experiment prefix (optional)",          default = "ECE3")
    parser.add_option("-t","--tmp", dest = "temp", help = "Temporary working directory (optional)",default = tmpdir)
    parser.add_option("-v","--var", dest = "vars", help = "Input variable list (optional)",        default = varfile)

    (opt,args) = parser.parse_args()

    # Initialize ece2cmorlib with experiment prefix:
    ece2cmorlib.initialize(opt.conf)

    # Load the variables as task targets:
    jsonloader.load_targets(opt.vars)

    # Remove targets that are constructed from three-hourly data:
    ece2cmorlib.tasks = [t for t in ece2cmorlib.tasks if is6hrtask(t)]

    # Execute the cmorization:
    if(opt.dir == datdir):
        ece2cmorlib.perform_ifs_tasks(opt.dir,opt.exp,startdate,interval,outputfreq = 6,tempdir = opt.temp,taskthreads=1)
    else:
        ece2cmorlib.perform_ifs_tasks(opt.dir,opt.exp,startdate,interval,outputfreq = 6,tempdir = opt.temp)

if __name__ == "__main__":
    main(sys.argv[1:])

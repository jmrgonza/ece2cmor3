#!/usr/bin/env python

# Call this script e.g. by:
#  ./drq2file_def-nemo.py --vars cmip6-data-request/cmip6-data-request-m=CMIP-e=CMIP-t=1-p=1/cmvme_CMIP_amip_1_1.xlsx

# Note that this script is called by the script:
#  generate-ec-earth-namelists.sh

import xml.etree.ElementTree as xmltree
import os.path                                                # for checking file or directory existence with: os.path.isfile or os.path.isdir
import sys                                                    # for aborting: sys.exit
from os.path import expanduser
import argparse
import logging
import re                                                     # for regular expressions

from ece2cmor3 import ece2cmorlib, taskloader, cmor_source, cmor_target, cmor_utils

basic_file_def_file_name          = "./xios-nemo-file_def-files/basic-cmip6-file_def_nemo.xml"
file_def_file_name                = "./xios-nemo-file_def-files/cmip6-file_def_nemo.xml"
file_def_opa_file_name            = "./xios-nemo-file_def-files/file_def_nemo-opa.xml"
file_def_lim_file_name            = "./xios-nemo-file_def-files/file_def_nemo-lim3.xml"
file_def_pisces_file_name         = "./xios-nemo-file_def-files/file_def_nemo-pisces.xml"
file_def_opa_file_name_compact    = "./xios-nemo-file_def-files/file_def_nemo-opa-compact.xml"
file_def_lim_file_name_compact    = "./xios-nemo-file_def-files/file_def_nemo-lim3-compact.xml"
file_def_pisces_file_name_compact = "./xios-nemo-file_def-files/file_def_nemo-pisces-compact.xml"

# Logging configuration
logging.basicConfig(level=logging.DEBUG)

# Logger construction
log = logging.getLogger(__name__)


# Main program
def main():
    parser = argparse.ArgumentParser(description="Create NEMO XIOS file_def input files for a given CMIP6 data request")
    parser.add_argument("--vars", metavar="FILE", type=str, required=True,
                        help="File (json|f90 namelist|xlsx) containing cmor variables (Required)")
    parser.add_argument("--tabdir", metavar="DIR", type=str, default=ece2cmorlib.table_dir_default,
                        help="Cmorization table directory")
    parser.add_argument("--tabid", metavar="PREFIX", type=str, default=ece2cmorlib.prefix_default,
                        help="Cmorization table prefix string")

    args = parser.parse_args()

    # Initialize ece2cmor:
    ece2cmorlib.initialize_without_cmor(ece2cmorlib.conf_path_default, mode=ece2cmorlib.PRESERVE, tabledir=args.tabdir,
                                        tableprefix=args.tabid)

    # Load the variables as task targets:
    taskloader.load_targets(args.vars, active_components={"ifs": False, "nemo": True})
    
    for task in ece2cmorlib.tasks:
    	 print ' {:15} {:8} {:15} {}'.format(task.target.variable, task.target.table, task.target.units, task.target.frequency)
        #print task.target.__dict__

    print ' Number of activated data request tasks is', len(ece2cmorlib.tasks)
        

    # READING THE BASIC FILE_DEF FILE:
    if os.path.isfile(basic_file_def_file_name) == False: print ' The file ', basic_file_def_file_name, '  does not exist.'; sys.exit(' stop')

    tree_basic_file_def             = xmltree.parse(basic_file_def_file_name)
    root_basic_file_def             = tree_basic_file_def.getroot()                        # This root has two indices: the 1st index refers to field_definition-element, the 2nd index refers to the field-elements
   #field_elements_basic_file_def   = root_basic_file_def[0][:]

    count = 0
    for field in root_basic_file_def.findall('.//field[@id]'):
     for task in ece2cmorlib.tasks:
      if field.attrib["name"] == task.target.variable and field.attrib["table"] == task.target.table:
       field.attrib["enabled"] = "True"
       count = count + 1
      #print field.attrib["name"], field.attrib["table"]
     # After the table attribute has been used to match with the data request, the table attribute is removed here because it is not a valid XIOS attribute:
     field.attrib.pop('table', None)

    # Write the NEMO XIOS file_def input files:
    tree_basic_file_def.write(file_def_file_name)

    print ' The number of variables which is enabled in', file_def_file_name, ' is', count


    # SPLIT THE FILE_DEF FILE IN THREE FILE_DEF FILES FOR OPA, LIM AND PISCES:

    # FILE_DEF FILE FOR OPA:
    tree_opa = xmltree.parse(file_def_file_name)
    root_opa = tree_opa.getroot()                        # This root has two indices: the 1st index refers to field_definition-element, the 2nd index refers to the field-elements

    for file_element in root_opa.findall('./file_group/file'):
     # Get the model component info from this attribute by  using a regular expression:
     model_component = re.search('_(.+?)_', file_element.attrib["name_suffix"]).group(1)
     if model_component == 'lim' or model_component == 'pisces':
     #print ' Remove file for opa file_def:', file_element.attrib["id"], model_component
      # Remove this file element from its parent element the file_group element:
      root_opa[0].remove(file_element)

    root_opa[0].attrib["id"] = "id_file_group_opa"
    tree_opa.write(file_def_opa_file_name)


    # FILE_DEF FILE FOR LIM:
    tree_lim = xmltree.parse(file_def_file_name)
    root_lim = tree_lim.getroot()                        # This root has two indices: the 1st index refers to field_definition-element, the 2nd index refers to the field-elements

    for file_element in root_lim.findall('./file_group/file'):
     # Get the model component info from this attribute by  using a regular expression:
     model_component = re.search('_(.+?)_', file_element.attrib["name_suffix"]).group(1)
     if model_component == 'opa' or model_component == 'pisces':
     #print ' Remove file for lim file_def:', file_element.attrib["id"], model_component
      # Remove this file element from its parent element the file_group element:
      root_lim[0].remove(file_element)

    root_lim[0].attrib["id"] = "id_file_group_lim"
    tree_lim.write(file_def_lim_file_name)


    # FILE_DEF FILE FOR PISCES:
    tree_pisces = xmltree.parse(file_def_file_name)
    root_pisces = tree_pisces.getroot()                        # This root has two indices: the 1st index refers to field_definition-element, the 2nd index refers to the field-elements

    for file_element in root_pisces.findall('./file_group/file'):
     # Get the model component info from this attribute by  using a regular expression:
     model_component = re.search('_(.+?)_', file_element.attrib["name_suffix"]).group(1)
     if model_component == 'opa' or model_component == 'lim':
     #print ' Remove file for pisces file_def:', file_element.attrib["id"], model_component
      # Remove this file element from its parent element the file_group element:
      root_pisces[0].remove(file_element)

    root_pisces[0].attrib["id"] = "id_file_group_pisces"
    tree_pisces.write(file_def_pisces_file_name)

    # Finishing up
    ece2cmorlib.finalize_without_cmor()


    # PRODUCE FILE_DEF FILES FOR OPA, LIM AND PISCES WITH ONLY ENABLED VARIABLES:

    # FILE_DEF FILE FOR OPA WITH ONLY ENABLED VARIABLES:
    tree_opa_enabled_only = xmltree.parse(file_def_opa_file_name)
    root_opa_enabled_only = tree_opa_enabled_only.getroot()    # This root has two indices: the 1st index refers to field_definition-element, the 2nd index refers to the field-elements

    for file_element in root_opa_enabled_only.findall('./file_group/file'):
      for field_element in file_element.findall('field[@enabled="False"]'): file_element.remove(field_element)
    tree_opa_enabled_only.write(file_def_opa_file_name_compact)


    # FILE_DEF FILE FOR LIM WITH ONLY ENABLED VARIABLES:
    tree_lim_enabled_only = xmltree.parse(file_def_lim_file_name)
    root_lim_enabled_only = tree_lim_enabled_only.getroot()    # This root has two indices: the 1st index refers to field_definition-element, the 2nd index refers to the field-elements

    for file_element in root_lim_enabled_only.findall('./file_group/file'):
      for field_element in file_element.findall('field[@enabled="False"]'): file_element.remove(field_element)
    tree_lim_enabled_only.write(file_def_lim_file_name_compact)


    # FILE_DEF FILE FOR PISCES WITH ONLY ENABLED VARIABLES:
    tree_pisces_enabled_only = xmltree.parse(file_def_pisces_file_name)
    root_pisces_enabled_only = tree_pisces_enabled_only.getroot()    # This root has two indices: the 1st index refers to field_definition-element, the 2nd index refers to the field-elements

    for file_element in root_pisces_enabled_only.findall('./file_group/file'):
      for field_element in file_element.findall('field[@enabled="False"]'): file_element.remove(field_element)
    tree_pisces_enabled_only.write(file_def_pisces_file_name_compact)





if __name__ == "__main__":
    main()

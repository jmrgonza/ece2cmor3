import cmor
import logging
import netCDF4
import numpy
import os

import cmor_target
import cmor_task
import cmor_utils

# Logger object
log = logging.getLogger(__name__)

# Experiment name
exp_name_ = None

# Table root
table_root_ = None

# Files that are being processed in the current execution loop.
nemo_files_ = []

# Dictionary of NEMO grid type with cmor grid id.
grid_ids_ = {}

# List of depth axis ids with cmor grid id.
depth_axes_ = {}

# Dictionary of output frequencies with cmor time axis id.
time_axes_ = {}

# Dictionary of sea-ice output types, 1 by default...
type_axes_ = {}


# Initializes the processing loop.
def initialize(path, expname, tableroot, start, length):
    global log, nemo_files_, exp_name_, table_root_
    exp_name_ = expname
    table_root_ = tableroot
    nemo_files_ = select_files(path, expname, start, length)
    cal = None
    for f in nemo_files_:
        cal = read_calendar(f)
        if cal:
            break
    if cal:
        cmor.set_cur_dataset_attribute("calendar", cal)
    return True


# Resets the module globals.
def finalize():
    global nemo_files_, grid_ids_, depth_axes_, time_axes_
    nemo_files_ = []
    grid_ids_ = {}
    depth_axes_ = {}
    time_axes_ = {}


# Executes the processing loop.
def execute(tasks):
    global log, time_axes_, depth_axes_, table_root_
    log.info("Looking up variables in files...")
    tasks = lookup_variables(tasks)
    log.info("Creating NEMO grids in CMOR...")
    create_grids(tasks)
    log.info("Executing %d NEMO tasks..." % len(tasks))
    log.info("Cmorizing NEMO tasks...")
    task_groups = cmor_utils.group(tasks, lambda tsk: getattr(tsk, cmor_task.output_path_key, None))
    for filename, task_group in task_groups.iteritems():
        dataset = netCDF4.Dataset(filename, 'r')
        task_sub_groups = cmor_utils.group(task_group, lambda tsk: tsk.target.table)
        for table, task_list in task_sub_groups.iteritems():
            try:
                tab_id = cmor.load_table("_".join([table_root_, table]) + ".json")
                cmor.set_table(tab_id)
            except Exception as e:
                log.error("CMOR failed to load table %s, skipping variables %s. Reason: %s"
                          % (table, ','.join([tsk.target.variable for tsk in task_list]), e.message))
                continue
            if table not in time_axes_:
                log.info("Creating time axes for table %s..." % table)
            create_time_axes(dataset, task_list, table)
            if table not in depth_axes_:
                log.info("Creating depth axes for table %s..." % table)
            create_depth_axes(dataset, task_list, table)
            for task in task_list:
                execute_netcdf_task(dataset, task)
        dataset.close()


def lookup_variables(tasks):
    valid_tasks = []
    for task in tasks:
        file_candidates = select_freq_files(task.target.frequency)
        results = []
        for ncfile in file_candidates:
            ds = netCDF4.Dataset(ncfile)
            if task.source.variable() in ds.variables:
                results.append(ncfile)
            ds.close()
        if len(results) == 0:
            log.error("Variable %s needed for %s in table %s was not found in NEMO output files... skipping task" %
                      (task.source.variable(), task.target.variable, task.target.table))
            task.set_failed()
            continue
        if len(results) > 1:
            log.warning("Variable %s needed for %s in table %s was found in multiple NEMO output files %s... choosing "
                        "the first match %s " % (task.source.variable(), task.target.table, task.target.variable,
                                                 task.target.table, ','.join(results)))
        setattr(task, cmor_task.output_path_key, results[0])
        valid_tasks.append(task)
    return valid_tasks


# Performs a single task.
def execute_netcdf_task(dataset, task):
    global log, grid_ids_, depth_axes_, time_axes_
    task.status = cmor_task.status_cmorizing
    grid_axes = [] if not hasattr(task, "grid_id") else [getattr(task, "grid_id")]
    z_axes = getattr(task, "z_axes", [])
    t_axes = [] if not hasattr(task, "time_axis") else [getattr(task, "time_axis")]
    axes = grid_axes + z_axes + t_axes
    for type_axis in type_axes_:
        if type_axis in getattr(task.target, cmor_target.dims_key):
            axes.append(type_axes_[type_axis])
    varid = create_cmor_variable(task, dataset, axes)
    ncvar = dataset.variables[task.source.variable()]
    missval = getattr(ncvar, "missing_value", getattr(ncvar, "_FillValue", numpy.nan))
    if not any(grid_axes):  # Fix for global averages
        vals = numpy.copy(ncvar[:, :, :])
        vals[vals == missval] = numpy.nan
        ncvar = numpy.mean(vals[:, :, :], axis=(1, 2))
    factor = get_conversion_factor(getattr(task, cmor_task.conversion_key, None))
    log.info("CMORizing variable %s in table %s form %s in "
             "file %s..." % (task.target.variable, task.target.table, task.source.variable(),
                             getattr(task, cmor_task.output_path_key)))
    cmor_utils.netcdf2cmor(varid, ncvar, 0, factor, missval=getattr(task.target, cmor_target.missval_key, missval))
    closed_file = cmor.close(varid, file_name=True)
    log.info("CMOR closed file %s" % closed_file)
    task.status = cmor_task.status_cmorized


# Unit conversion utility method
def get_conversion_factor(conversion):
    global log
    if not conversion:
        return 1.0
    if conversion == "tossqfix":
        return 1.0
    if conversion == "frac2percent":
        return 100.0
    if conversion == "percent2frac":
        return 0.01
    log.error("Unknown explicit unit conversion %s will be ignored" % conversion)
    return 1.0


# Creates a variable in the cmor package
def create_cmor_variable(task, dataset, axes):
    srcvar = task.source.variable()
    ncvar = dataset.variables[srcvar]
    unit = getattr(ncvar, "units", None)
    if (not unit) or hasattr(task, cmor_task.conversion_key):  # Explicit unit conversion
        unit = getattr(task.target, "units")
    if hasattr(task.target, "positive") and len(task.target.positive) != 0:
        return cmor.variable(table_entry=str(task.target.variable), units=str(unit), axis_ids=axes,
                             original_name=str(srcvar), positive="down")
    else:
        return cmor.variable(table_entry=str(task.target.variable), units=str(unit), axis_ids=axes,
                             original_name=str(srcvar))


# Creates all depth axes for the given table from the given files
def create_depth_axes(ds, tasks, table):
    global depth_axes_
    if table not in depth_axes_:
        depth_axes_[table] = {}
    table_depth_axes = time_axes_[table]
    other_nc_axes = ["time_counter", "x", "y", "typesi"]
    for task in tasks:
        z_axes = [d for d in ds.variables[task.source.variable()].dimensions if d not in other_nc_axes]
        z_axis_ids = []
        for z_axis in z_axes:
            if z_axis in table_depth_axes:
                z_axis_ids.append(table_depth_axes[z_axis])
            else:
                depth_coordinates = ds.variables[z_axis]
                depth_bounds = ds.variables[getattr(depth_coordinates, "bounds")]
                units = getattr(depth_coordinates, "units")
                b = depth_bounds[:, :]
                b[b < 0] = 0
                z_axis_id = cmor.axis(table_entry="depth_coord", units=units, coord_vals=depth_coordinates[:],
                                      cell_bounds=b)
                z_axis_ids.append(z_axis_id)
                table_depth_axes[z_axis] = z_axis_id
        setattr(task, "z_axes", z_axis_ids)


# Creates a time axis for the currently loaded table
def create_time_axes(ds, tasks, table):
    global time_axes_
    if table not in time_axes_:
        time_axes_[table] = {}
    table_time_axes = time_axes_[table]
    for task in tasks:
        tgtdims = getattr(task.target, cmor_target.dims_key)
        # TODO: better to check in the table axes if the standard name of the dimension equals "time"
        for time_dim in [d for d in list(set(tgtdims.split())) if d.startswith("time")]:
            if time_dim in table_time_axes:
                tid = table_time_axes[time_dim]
            else:
                time_operator = getattr(task.target, "time_operator", ["point"])
                if time_operator == ["point"]:
                    tid = cmor.axis(table_entry=str(time_dim), units=getattr(ds.variables["time_counter"], "units"),
                                    coord_vals=ds.variables["time_counter"][:])
                else:
                    tid = cmor.axis(table_entry=str(time_dim), units=getattr(ds.variables["time_counter"], "units"),
                                    coord_vals=ds.variables["time_counter"][:],
                                    cell_bounds=ds.variables[getattr(ds.variables["time_counter"], "bounds")][:, :])
                table_time_axes[time_dim] = tid
            setattr(task, "time_axis", tid)
    return table_time_axes


def create_type_axes():
    global type_axes_
    type_axes_["typesi"] = cmor.axis(table_entry="typesi", coord_vals=[1])


# Selects files with data with the given frequency
def select_freq_files(freq):
    global exp_name_, nemo_files_
    nemo_freq = None
    if freq == "monClim":
        nemo_freq = "1m"
    elif freq.endswith("mon"):
        n = 1 if freq == "mon" else int(freq[:-3])
        nemo_freq = str(n) + "m"
    elif freq.endswith("day"):
        n = 1 if freq == "day" else int(freq[:-3])
        nemo_freq = str(n) + "d"
    elif freq.endswith("hr"):
        n = 1 if freq == "hr" else int(freq[:-2])
        nemo_freq = str(n) + "h"
    return [f for f in nemo_files_ if cmor_utils.get_nemo_frequency(f, exp_name_) == nemo_freq]


# Retrieves all NEMO output files in the input directory.
def select_files(path, expname, start, length):
    allfiles = cmor_utils.find_nemo_output(path, expname)
    starttime = cmor_utils.make_datetime(start)
    stoptime = cmor_utils.make_datetime(start + length)
    return [f for f in allfiles if
            cmor_utils.get_nemo_interval(f)[0] <= stoptime and cmor_utils.get_nemo_interval(f)[1] >= starttime]


# Reads the calendar attribute from the time dimension.
def read_calendar(ncfile):
    ds = None
    try:
        ds = netCDF4.Dataset(ncfile, 'r')
        if not ds:
            return None
        timvar = ds.variables["time_centered"]
        if timvar:
            result = getattr(timvar, "calendar")
            return result
        else:
            return None
    finally:
        if ds is not None:
            ds.close()


# Reads all the NEMO grid data from the input files.
def create_grids(tasks):
    global grid_ids_
    cmor.load_table(table_root_ + "_grids.json")
    task_groups = cmor_utils.group(tasks, lambda t: getattr(t, cmor_task.output_path_key, None))
    for filename, task_list in task_groups.iteritems():
        if filename is not None:
            grid = read_grid(filename)
            grid_id = write_grid(grid)
            grid_ids_[grid.name] = grid_id
            for task in task_list:
                setattr(task, "grid_id", grid_id)


# Reads a particular NEMO grid from the given input file.
def read_grid(ncfile):
    ds = None
    try:
        ds = netCDF4.Dataset(ncfile, 'r')
        name = getattr(ds.variables["nav_lon"], "nav_model", os.path.basename(ncfile))
        lons = ds.variables["nav_lon"][:, :]
        lats = ds.variables["nav_lat"][:, :]
        return nemo_grid(name, lons, lats)
    finally:
        if ds is not None:
            ds.close()


# Transfers the grid to cmor.
def write_grid(grid):
    nx = grid.lons.shape[0]
    ny = grid.lons.shape[1]
    i_index_id = cmor.axis(table_entry="j_index", units="1", coord_vals=numpy.array(range(1, nx + 1)))
    j_index_id = cmor.axis(table_entry="i_index", units="1", coord_vals=numpy.array(range(1, ny + 1)))
    if ny == 1:
        return cmor.grid(axis_ids=[i_index_id],
                         latitude=grid.lats[:, 0],
                         longitude=grid.lons[:, 0],
                         latitude_vertices=grid.vertex_lats,
                         longitude_vertices=grid.vertex_lons)
    return cmor.grid(axis_ids=[i_index_id, j_index_id],
                     latitude=grid.lats,
                     longitude=grid.lons,
                     latitude_vertices=grid.vertex_lats,
                     longitude_vertices=grid.vertex_lons)


# Class holding a NEMO grid, including bounds arrays
class nemo_grid(object):

    def __init__(self, name_, lons_, lats_):
        self.name = name_
        flon = numpy.vectorize(lambda x: x % 360)
        flat = numpy.vectorize(lambda x: (x + 90) % 180 - 90)
        self.lons = flon(nemo_grid.smoothen(lons_))
        self.lats = flat(lats_)
        self.vertex_lons = nemo_grid.create_vertex_lons(lons_)
        self.vertex_lats = nemo_grid.create_vertex_lats(lats_)

    @staticmethod
    def create_vertex_lons(a):
        nx = a.shape[0]
        ny = a.shape[1]
        f = numpy.vectorize(lambda x: x % 360)
        if ny == 1:
            b = numpy.zeros([nx, 2])
            b[1:nx, 0] = f(0.5 * (a[0:nx - 1, 0] + a[1:nx, 0]))
            b[0:nx - 1, 1] = b[1:nx, 1]
            return b
        b = numpy.zeros([nx, ny, 4])
        b[1:nx, :, 0] = f(0.5 * (a[0:nx - 1, :] + a[1:nx, :]))
        b[0, :, 0] = b[nx - 1, :, 0]
        b[0:nx - 1, :, 1] = b[1:nx, :, 0]
        b[nx - 1, :, 1] = b[1, :, 1]
        b[:, :, 2] = b[:, :, 1]
        b[:, :, 3] = b[:, :, 0]
        return b

    @staticmethod
    def create_vertex_lats(a):
        nx = a.shape[0]
        ny = a.shape[1]
        f = numpy.vectorize(lambda x: (x + 90) % 180 - 90)
        if ny == 1:  # Longitudes were integrated out
            b = numpy.zeros([nx, 2])
            b[:, 0] = f(a[:, 0])
            b[:, 1] = f(a[:, 0])
            return b
        b = numpy.zeros([nx, ny, 4])
        b[:, 0, 0] = f(1.5 * a[:, 0] - 0.5 * a[:, 1])
        b[:, 1:ny, 0] = f(0.5 * (a[:, 0:ny - 1] + a[:, 1:ny]))
        b[:, :, 1] = b[:, :, 0]
        b[:, 0:ny - 1, 2] = b[:, 1:ny, 0]
        b[:, ny - 1, 2] = f(1.5 * a[:, ny - 1] - 0.5 * a[:, ny - 2])
        b[:, :, 3] = b[:, :, 2]
        return b

    @staticmethod
    def modlon2(x, a):
        if x < a:
            return x + 360.0
        else:
            return x

    @staticmethod
    def smoothen(a):
        nx = a.shape[0]
        ny = a.shape[1]
        if ny == 1:
            return a
        mod = numpy.vectorize(nemo_grid.modlon2)
        b = numpy.empty([nx, ny])
        for i in range(0, nx):
            x = a[i, 1]
            b[i, 0] = a[i, 0]
            b[i, 1] = x
            b[i, 2:] = mod(a[i, 2:], x)
        return b

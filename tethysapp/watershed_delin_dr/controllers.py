import os
import sys
from datetime import datetime, timedelta
import binascii
import subprocess
import tempfile
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from tethys_apps.sdk.gizmos import Button, TextInput, SelectInput
from django.shortcuts import render
from tethys_gizmos.gizmo_options import MapView, MVView


# Apache should have ownership and full permission over this path
DEM_FULL_PATH = "/home/drew/dem/dr_srtm_30_3857.tif"
DEM_NAME = 'dr_srtm_30_3857' # DEM layer name, no extension (no .tif)
DRAINAGE_FULL_PATH = "/home/drew/dem/dr_srtm_30_3857_drain.tif"
DRAINAGE_NAME = 'dr_srtm_30_3857_drain'
GISBASE = "/usr/lib/grass70" # full path to GRASS installation
GRASS7BIN = "grass70" # command to start GRASS from shell
GISDB = os.path.join(tempfile.gettempdir(), 'grassdata')
OUTPUT_DATA_PATH = os.path.join(tempfile.gettempdir(), 'grassdata', "output_data")

@login_required()
def home(request):

    btnDelin = Button(display_text="Delineate Watershed",
                        name="btnDelin",
                        attributes="onclick=run_sc_service()",
                        submit=False)

    context = {'btnDelin': btnDelin
               }

    return render(request,'watershed_delin_dr/home.html', context)

def run_sc(request):

    string_length = 4
    jobid = binascii.hexlify(os.urandom(string_length))
    time_start = datetime.now()
    status = "error"
    message = ""
    input_para = {}

    try:
        if request.GET:
            xlon = request.GET.get("xlon", None)
            ylat = request.GET.get("ylat", None)
            prj = request.GET.get("prj", None)

            input_para["xlon"] = xlon
            input_para["ylat"] = ylat
            input_para["prj"] = prj

            # Run SC()
            basin_GEOJSON, msg = SC(jobid, xlon, ylat, prj)

            #Check results
            if basin_GEOJSON is not None:
                message += msg
            else:
                message += msg
        else:
            raise Exception("Please call this service in a GET request.")

    except Exception as ex:
        message = ex.message

    # Return inputs and results
    finally:

        with open(basin_GEOJSON) as f:
            basin_data = json.load(f)

        return JsonResponse(basin_data)


def SC(jobid, xlon, ylat, prj):

    dem_full_path = DEM_FULL_PATH
    dem = DEM_NAME
    drainage_full_path = DRAINAGE_FULL_PATH
    drainage = DRAINAGE_NAME
    gisbase = GISBASE
    grass7bin = GRASS7BIN

    # Define grass data folder, location, mapset
    gisdb = os.path.join(tempfile.gettempdir(), 'grassdata')
    if not os.path.exists(gisdb):
        os.mkdir(gisdb)
    location = "location_{0}".format(dem)
    mapset = "PERMANENT"
    msg = ""

    # Create log file for each job
    log_name = 'log_{0}.log'.format(jobid)
    log_path = os.path.join(gisdb, log_name)
    f = open(log_path, 'w', 0)

    # Create output_data folder path
    output_data_path = OUTPUT_DATA_PATH
    if not os.path.exists(output_data_path):
        os.mkdir(output_data_path)


    try:
        # Create location
        location_path = os.path.join(gisdb, location)
        if not os.path.exists(location_path):
            f.write('\n---------Create Location from DEM--------------------\n')
            f.write('{0}\n'.format(location_path))
            startcmd = grass7bin + ' -c ' + dem_full_path + ' -e ' + location_path

            print startcmd
            p = subprocess.Popen(startcmd, shell=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            if p.returncode != 0:
                print >>sys.stderr, 'ERROR: %s' % err
                print >>sys.stderr, 'ERROR: Cannot generate location (%s)' % startcmd
                f.write('\n---------Create Location failed--------------------\n')
                sys.exit(-1)
            else:
                f.write('\n---------Create Location done--------------------\n')
                print 'Created location %s' % location_path

        xlon = float(xlon)
        ylat = float(ylat)
        outlet = (xlon, ylat)

        # Set GISBASE environment variable
        os.environ['GISBASE'] = gisbase
        # the following not needed with trunk
        os.environ['PATH'] += os.pathsep + os.path.join(gisbase, 'extrabin')
        # Set GISDBASE environment variable
        os.environ['GISDBASE'] = gisdb

        # define GRASS-Python environment
        gpydir = os.path.join(gisbase, "etc", "python")
        sys.path.append(gpydir)

        f.write('\n---------sys.path--------------------\n')
        f.write('\n'.join(sys.path))
        f.write('\n----------sys.version-------------------\n')
        f.write(sys.version)
        f.write('\n----------os.environ-----------------\n')
        f.write(str(os.environ))

        # import GRASS Python bindings (see also pygrass)
        import grass.script as gscript
        import grass.script.setup as gsetup
        gscript.core.set_raise_on_error(True)

        # launch session
        gsetup.init(gisbase, gisdb, location, mapset)
        f.write(str(gscript.gisenv()))

        # Check the dem file, import if not exist
        dem_mapset_path = location_path = os.path.join(gisdb, location, mapset, "cell", dem)

        if not os.path.exists(dem_mapset_path):
            f.write("\n ---------- import DEM file ------------- \n")
            stats = gscript.read_command('r.in.gdal', input=dem_full_path, output=dem)
        #import drainage
        drainage_mapset_path = location_path = os.path.join(gisdb, location, mapset, "cell", drainage)
        if not os.path.exists(drainage_mapset_path):
            f.write("\n ---------- import Drainage file ------------- \n")
            stats = gscript.read_command('r.in.gdal', input=drainage_full_path, output=drainage)

        # List all files in location to check if the DEM file imported successfully
        f.write("\n ---------- List raster ------------- \n")
        for rast in gscript.list_strings(type='rast'):
            f.write(str(rast))
        f.write("\n ---------- List vector ------------- \n")
        for vect in gscript.list_strings(type='vect'):
            f.write(str(vect))

        f.write("\n ---------------------------JOB START-------------------------------- \n")
        f.write(str(datetime.now()))

        # Project xlon, ylat wgs84 into current
        if prj.lower() != "native" or prj.lower() == "wgs84":
            f.write("\n ---------- Reproject xlon and ylat into native dem projection ------------- \n")
            stats = gscript.read_command('m.proj', coordinates=(xlon, ylat), flags='i')
            coor_list = stats.split("|")
            xlon = float(coor_list[0])
            ylat = float(coor_list[1])
            outlet = (xlon, ylat)

        # Define region
        f.write("\n ---------- Define region ------------- \n")
        stats = gscript.parse_command('g.region', raster=dem, flags='p')
        f.write(str(stats))

        # Read extent of the dem file
        for key in stats:
            if "north:" in key:
                north = float(key.split(":")[1])
            elif "south:" in key:
                south = float(key.split(":")[1])
            elif "west:" in key:
                west = float(key.split(":")[1])
            elif "east:" in key:
                east = float(key.split(":")[1])
            elif "nsres:" in key:
                nsres = float(key.split(":")[1])
            elif "ewres:" in key:
                ewres = float(key.split(":")[1])

        # check if xlon, ylat is within the extent of dem
        if xlon < west or xlon > east:
            f.write("\n ERROR: xlon is out of dem region. \n")
            raise Exception("(xlon, ylat) is out of dem region.")
        elif ylat < south or ylat > north:
            f.write("\n ERROR: ylat is out of dem region. \n")
            raise Exception("(xlon, ylat) is out of dem region.")


        # Flow accumulation analysis
        f.write("\n ---------- Flow accumulation analysis ------------- \n")
        if not os.path.exists(drainage_mapset_path):
            stats = gscript.read_command('r.watershed', elevation=dem, threshold='10000', drainage=drainage, flags='s', overwrite=True)

        # Delineate watershed
        f.write("\n ---------- Delineate watershed ------------- \n")
        basin = "{0}_basin_{1}".format(dem, jobid)
        stats = gscript.read_command('r.water.outlet', input=drainage, output=basin, coordinates=outlet, overwrite=True)

        # output lake
        # r.mapcalc expression="lake_285.7846_all_0 = if( lake_285.7846, 0)" --o
        f.write("\n -------------- Set all values of raster basin to 0 ----------------- \n")
        basin_all_0 = "{0}_all_0".format(basin)
        mapcalc_cmd = '{0} = if({1}, 0)'.format(basin_all_0, basin)
        gscript.mapcalc(mapcalc_cmd, overwrite=True, quiet=True)

        # covert raster lake_rast_all_0 into vector
        # r.to.vect input='lake_285.7846_all_0@drew' output='lake_285_all_0_vec' type=area --o
        f.write("\n -------------- convert raster lake_rast_all_0 into vector ----------------- \n")
        basin_all_0_vect = "{0}_all_0_vect".format(basin)
        f.write("\n -------------- {0} ----------------- \n".format(basin_all_0_vect))
        stats = gscript.parse_command('r.to.vect', input=basin_all_0, output=basin_all_0_vect, type="area", overwrite=True)

        # output GeoJSON
        # v.out.ogr -c input='lake_285_alll_0_vec' output='/tmp/lake_285_all_0_vec.geojson' format=GeoJSON type=area --overwrite
        geojson_f_name = "{0}.GEOJSON".format(basin)
        basin_GEOJSON = os.path.join(output_data_path, geojson_f_name)
        stats = gscript.parse_command('v.out.ogr', input=basin_all_0_vect, output=basin_GEOJSON, \
                                      format="GeoJSON", type="area", overwrite=True, flags="c")

        f.write("\n-------------------------END--------------------------\n")
        f.write(str(datetime.now()))
        f.close()
        return basin_GEOJSON, msg

    except Exception as e:
        print e.message
        msg = e.message
        if f is not None:
            f.write("\n-------------!!!!!!  ERROR  !!!!!!--------------\n")
            f.write(e.message)
            f.close()
        return None, msg



import pandas
import pathlib
import subprocess
import rasterio
import matplotlib.pyplot as plt
import numpy as np

__all__ = ["file_index"]

junea_pic = "juneau2k.jpg"


def do_fetch():
    # See `https://www.usgs.gov/faqs/can-i-get-bulk-order-usgs-topographic-maps-pdf-format-state-or-entire-country`
    # See `http://prd-tnm.s3-website-us-west-2.amazonaws.com/?prefix=StagedProducts/Maps/Metadata/`
    # for all indices of USGS topo maps.
    base_url = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/Metadata/"
    archive_filename = "historicaltopo.zip"
    if not pathlib.Path(archive_filename).exists():
        subprocess.run(f"curl -O {base_url}{archive_filename}".split())

    index_filename = "historicaltopo.csv"
    if not pathlib.Path(index_filename).exists():
        subprocess.run(f"unzip {archive_filename}".split())

    with open(index_filename, "r") as index_file:
        file_index = pandas.read_csv(index_file)

    contains_juneau = file_index["map_name"].str.contains("Juneau")
    high_resolution = file_index["grid_size"].str.contains("7.5 X 7.5 Minute")
    juneau_maps = file_index[contains_juneau & high_resolution]
    for url in juneau_maps["geotiff_url"]:
        command = f"curl -C - -O {url}"
        subprocess.run(command.split())
    filenames = list(pathlib.Path("./").glob("AK_Juneau*.tif"))
    with rasterio.open(filenames[1], "r") as source:
        crs = source.crs
        bounds = source.bounds
        image = source.read()
    fig, ax = plt.subplots(dpi=2000)
    extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)
    ax.imshow(
        np.dstack((image[0, :, :], image[1, :, :], image[2, :, :])), extent=extent
    )
    plt.savefig(junea_pic, dpi=2000, pil_kwargs={"quality": 95})

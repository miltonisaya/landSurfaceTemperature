# -*- coding: utf-8 -*-
"""GDAL raster processing utilities."""

import os

from osgeo import gdal

# Maps common file extensions to their GDAL driver names.
# Extensions not listed here fall back to GeoTIFF.
_EXTENSION_DRIVERS = {
    '.tif':  'GTiff',
    '.tiff': 'GTiff',
    '.img':  'HFA',
    '.asc':  'AAIGrid',
    '.nc':   'netCDF',
    '.vrt':  'VRT',
    '.sdat': 'SAGA',
}


def _driver_for_path(path):
    ext = os.path.splitext(path)[1].lower()
    return _EXTENSION_DRIVERS.get(ext, 'GTiff')


def create_output_raster(path, ref_ds):
    """Create a Float32 output raster matching a reference dataset's geotransform and projection.

    The GDAL driver is chosen from the output file extension; unknown
    extensions fall back to GeoTIFF.

    :param path: Output file path.
    :param ref_ds: Reference GDAL dataset.
    :returns: New GDAL dataset.
    :raises RuntimeError: If GDAL cannot create the output file.
    """
    driver_name = _driver_for_path(path)
    driver = gdal.GetDriverByName(driver_name)
    if driver is None:
        driver = gdal.GetDriverByName('GTiff')

    cols = ref_ds.RasterXSize
    rows = ref_ds.RasterYSize
    out_ds = driver.Create(path, cols, rows, 1, gdal.GDT_Float32)
    if out_ds is None:
        raise RuntimeError(
            'GDAL could not create output raster at "{}". '
            'Check the path and that the format is writable.'.format(path)
        )
    out_ds.SetGeoTransform(ref_ds.GetGeoTransform())
    out_ds.SetProjection(ref_ds.GetProjection())
    return out_ds


def iterate_blocks(rows, cols, block_size=64):
    """Yield (x_offset, y_offset, num_cols, num_rows) for block processing.

    :param rows: Total rows.
    :param cols: Total columns.
    :param block_size: Block size in pixels (default 64).
    """
    for i in range(0, rows, block_size):
        num_rows = min(block_size, rows - i)
        for j in range(0, cols, block_size):
            num_cols = min(block_size, cols - j)
            yield j, i, num_cols, num_rows


def count_blocks(rows, cols, block_size=64):
    """Count the total number of blocks for progress calculation.

    :param rows: Total rows.
    :param cols: Total columns.
    :param block_size: Block size in pixels (default 64).
    :returns: Total number of blocks.
    """
    row_blocks = (rows + block_size - 1) // block_size
    col_blocks = (cols + block_size - 1) // block_size
    return row_blocks * col_blocks


def finalize_raster(ds, nodata=-99):
    """Set NoDataValue and compute histogram for the first band.

    :param ds: GDAL dataset.
    :param nodata: NoData value (default -99).
    """
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(nodata)
    histogram = band.GetDefaultHistogram()
    band.SetDefaultHistogram(histogram[0], histogram[1], histogram[3])

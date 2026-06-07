import os
import textwrap
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.bonds.ConvertibleBondManagerReport import ConvertibleBondManagerReport

logger = CommonLib.logger



if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    report = ConvertibleBondManagerReport()
    report.run("20260101", "20260522")

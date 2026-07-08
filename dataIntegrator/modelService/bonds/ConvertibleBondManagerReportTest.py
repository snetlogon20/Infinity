import pandas as pd

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.bonds.ConvertibleBondManagerReport import ConvertibleBondManagerReport

logger = CommonLib.logger



if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    report = ConvertibleBondManagerReport()
    report.run("20260101", CommonParameters.today)
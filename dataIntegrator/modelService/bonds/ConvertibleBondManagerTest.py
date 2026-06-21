import pandas as pd

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.bonds.ConvertibleBondManager import ConvertibleBondManager

logger = CommonLib.logger

class ConvertibleBondManagerTest:
    """可转债指标管理器：计算、查询、保存可转债指标到 ClickHouse"""

    def __init__(self):
        pass

if __name__ == "__main__":
    # 测试代码
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    manager = ConvertibleBondManager()

    # # 单日测试
    # manager.caculate_single_convertable_bond()
    # manager.calculate_selected_bonds("20260525")
    # manager.calculate_all_bonds("20260525")
    #
    # # 单日保存
    # manager._save_bonds_for_date("20260525")

    # 批量保存: start_date ~ end_date
    #manager.save_calculated_bonds("20260101", "20260524")
    #manager.save_calculated_bonds("20260501", "20260524")
    # manager.save_calculated_bonds("20260101", "20260614")
    manager.save_calculated_bonds("20260601", CommonParameters.today)


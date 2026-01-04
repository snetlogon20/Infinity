import pandas as pd
from dataIntegrator.plotService.ScatterPlotManager import ScatterPlotManager

if __name__ == '__main__':
    test_data = pd.DataFrame({
        'date': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04'],
        'value1': [10, 20, 15, 25],
        'value2': [5, 15, 10, 30]
    })

    # 创建测试参数字典
    param_dict = {
        "isPlotRequired": "yes",
        "results": test_data,
        "plotRequirement": {
            "PlotX": "date",
            "PlotY": "value1",
            "PlotTitle": "Test Line Plot",
            "xlabel": "Date",
            "ylabel": "Value"
        }
    }

    plotManager = ScatterPlotManager()
    plotManager.draw_plot(param_dict)
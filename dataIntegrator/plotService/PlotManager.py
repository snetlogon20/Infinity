from dataIntegrator import CommonLib
from dataIntegrator.plotService.LinePlotManager import LinePlotManager
from dataIntegrator.plotService.ScatterPlotManager import ScatterPlotManager

logger = CommonLib.logger
commonLib = CommonLib()

class PlotManager:

    @classmethod
    def draw_plot(self, param_dict):
        logger.info(rf"start - draw_plot, param_dict: {param_dict} ")

        if param_dict.get("isPlotRequired", "no") == "no":
            logger.info(rf"isPlotRequired == no, so just skipped")
            return

        try:
            plotType = param_dict.get("plotType", "lineChart")
            logger.info(rf"plotType: {plotType}")

            match plotType:
                case "lineChart":
                    plotManager = LinePlotManager()
                case "scatterChart":
                    plotManager = ScatterPlotManager()
                case _:
                    raise commonLib.raise_custom_error(error_code="000102",custom_error_message=rf"Wrong plotType given: {param_dict}")

            plotManager.draw_plot(param_dict)
        except:
            raise commonLib.raise_custom_error(error_code="000102",custom_error_message=rf"Wrong plotType given: {param_dict}")

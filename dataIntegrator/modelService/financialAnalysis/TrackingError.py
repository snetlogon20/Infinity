from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.statistics.MathmaticManger import MathmaticManager

class TrackingError:

    mathManager = MathmaticManager()

    @classmethod
    def calculate_rho(self, portfolio_data, column_a, column_b):
        rho = self.mathManager.get_rho_ab(portfolio_data, column_a, column_b)
        print("相关系数矩阵：", rho)
        return rho

    ########################################
    # caculate_TEV with SQL
    ########################################
    @classmethod
    def caculate_tev_with_sql(self, sql, portfolio_columns, portfolio_column, benchmark_column):
        clickhouClickhouseService = ClickhouseService()
        portfolio_data = clickhouClickhouseService.getDataFrame(sql, portfolio_columns)
        tev = self.caculate_TEV_with_dataframe(portfolio_data, portfolio_column, benchmark_column)

        return portfolio_data, tev

    ########################################
    # caculate_TEV with portfolio dataframe
    ########################################
    @classmethod
    def caculate_TEV_with_dataframe(self, tev_data, portfolio_column, benchmark_column):
        rho = self.calculate_rho(tev_data, portfolio_column, benchmark_column)
        print("rho:", rho)

        portfolio_segma = tev_data[portfolio_column].std()
        print("portfolio_segma:", portfolio_segma)

        benchmark_segma = tev_data[benchmark_column].std()
        print("benchmark_segma:",benchmark_segma)

        tev = self.caculate_TEV_with_number(benchmark_segma, portfolio_segma, rho)

        return tev

    ########################################
    # caculate_TEV with pure parameter
    ########################################
    @classmethod
    def caculate_TEV_with_number(self, benchmark_segma, portfolio_segma, rho):
        w2 = portfolio_segma ** 2 - 2 * rho * portfolio_segma * benchmark_segma + benchmark_segma ** 2
        tev = w2 ** 0.5
        print(f"TEV 百分比: {tev * 100:.2f}%")
        return tev

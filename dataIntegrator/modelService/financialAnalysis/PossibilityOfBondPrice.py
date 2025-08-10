from operator import itemgetter

import pandas as pd
from parso.python.tree import Class

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.distribution.NormalDistribution import NormalDistribution
from dataIntegrator.modelService.financialAnalysis.TrackingError import TrackingError
import matplotlib.pyplot as plt

class PossibilityOfBondPrice:
    def caculate_bond_price_by_rate_time(self,rate, time):

        value = 100/(1+rate)**time
        print(value)

        return value

    def caculate_bond_rate_by_value_time(self,value, time):

        rate = (100/value)**(1/time)-1
        print(rate)
        return rate

    def caculate_possibility_of_bond_price_by_value_time(self,
        expected_value,current_rate, bond_segma, time_year, current_value):

        normalDistribution = NormalDistribution(0, 1)
        if expected_value <= current_value:
            rate_of_expected_value = self.caculate_bond_rate_by_value_time(expected_value, time_year)
            rate_gap = rate_of_expected_value * 100 - current_rate * 100
            z = rate_gap / bond_segma
            cdf_value = normalDistribution.cdf(z * -1)
            possibilityOfBondPrice = cdf_value
        else:
            rate_of_expected_value = self.caculate_bond_rate_by_value_time(expected_value, time_year)
            rate_gap = current_rate * 100 - rate_of_expected_value * 100
            z = rate_gap / bond_segma
            cdf_value = normalDistribution.cdf(z * -1)
            possibilityOfBondPrice = cdf_value

        print(f"{cdf_value * 100:6f}%")

        return possibilityOfBondPrice

def test_possibility_of_bond_rate_p41():
    # P41 债券收益率概率

    global value
    possibilityOfBondPrice = PossibilityOfBondPrice()

    rate = 0.06
    time = 30
    possibilityOfBondPrice.caculate_bond_price_by_rate_time(rate, time)
    value = 15
    time = 30
    rate0 = possibilityOfBondPrice.caculate_bond_rate_by_value_time(value, time)
    value = 17.41
    time = 30
    rate1 = possibilityOfBondPrice.caculate_bond_rate_by_value_time(value, time)
    normalDistribution = NormalDistribution(0, 1)
    segma = 0.8
    rate_gap = rate0 * 100 - rate1 * 100
    z = rate_gap / segma
    cdf_value = normalDistribution.cdf(z * -1)
    possibility_of_bond_price = cdf_value
    print(f"{cdf_value * 100:6f}%")

    return possibility_of_bond_price


def test_possibility_of_bond_rate_by_given_price_range():

    expected_values = [round(i * 0.01, 1) for i in range(1000, 2840)]
    current_rate = 0.06
    bond_segma = 0.8
    time_year = 30
    current_value = 17.41

    results_of_dict = []
    results_of_possibility_of_bond_price = []

    # 遍历列表并调用方法
    possibilityOfBondPrice = PossibilityOfBondPrice()
    for expected_value in expected_values:
        possibility_of_bond_price = possibilityOfBondPrice.caculate_possibility_of_bond_price_by_value_time(
            expected_value,
            current_rate,
            bond_segma,
            time_year,
            current_value
        )

        results_of_dict.append({
            'expected_value': expected_value,
            'possibilityOfBondPrice': possibility_of_bond_price
        })

        results_of_possibility_of_bond_price.append(possibility_of_bond_price)
    print(results_of_possibility_of_bond_price)

    # 计算可能性的百分比
    possibility_percentages = [value * 100 for value in results_of_possibility_of_bond_price]
    # 创建柱状图
    bars = plt.bar(expected_values, possibility_percentages, color='blue', label='Possibility of Bond Price (%)')
    # highlight_x = [15, 17.41, 18.1]
    highlight_x = [15, 17.1, 20.1]
    for i, bar in enumerate(bars):
        if expected_values[i] in highlight_x:
            bar.set_color('red')
            plt.text(expected_values[i], possibility_percentages[i] + 1,
                     f'{possibility_percentages[i]:.2f}%', ha='center', va='bottom', color='red')
    # 在每个柱子上显示百分比
    for i, v in enumerate(possibility_percentages):
        if expected_values[i].is_integer():  # 判断 expected_values 是否为整数
            plt.text(expected_values[i], v + 1, f'{v:.2f}%', ha='center', va='bottom')
    # 设置图表标签和标题
    plt.xlabel('Expected Value')
    plt.ylabel('Possibility of Bond Price (%)')
    plt.title('Bar Chart of Expected Value vs Possibility of Bond Price Percentage')
    # 显示图表
    plt.legend()
    plt.show()


if __name__ == "__main__":

    print("# test 1")
    test_possibility_of_bond_rate_p41()

    print("# test 2")
    expected_value = 15
    current_rate = 0.06
    bond_segma = 0.8
    time_year = 30
    current_value = 17.41
    possibilityOfBondPrice = PossibilityOfBondPrice()
    possibilityOfBondPrice.caculate_possibility_of_bond_price_by_value_time(
        expected_value,
        current_rate,
        bond_segma,
        time_year,
        current_value
    )

    print("# test 3")
    test_possibility_of_bond_rate_by_given_price_range()

import pandas as pd
import numpy as np
from dataIntegrator.modelService.bonds.BondsManager import BondsManager
from dataIntegrator.utility.FileUtility import FileUtility
import matplotlib.pyplot as plt

def bond_yield_price_figure_6_1():
    #global params, bond_params_pd, bond_information_pd, bond_params
    params = BondsManager.init_params()
    params['bond_name'] = 'Test_12_求证 P131上Example计算不同Yield下的presentation value'
    params['bond_yield'] = 50 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 10
    params['T_unit'] = 'Y'
    params['semester'] = 1

    # calculate the year and price
    bond_yield_price_list = []
    for bond_yield in range(0, 51, 1):
        params['bond_yield'] = bond_yield / 100
        bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
        print(rf": {bond_params['bond_yield']}, {bond_params['present_value_total_sum']}")
        bond_yield_price_list.append((bond_params['bond_yield'], bond_params['present_value_total_sum']))

    # convert the data list to pd
    bond_yield_price_pd = pd.DataFrame(bond_yield_price_list, columns=['bond_yield', 'market_price'])
    print(bond_yield_price_pd)

    # plot the graph
    plt.plot(bond_yield_price_pd['bond_yield'], bond_yield_price_pd['market_price'])
    plt.xlabel('Bond Yield')
    plt.ylabel('Market Price')
    plt.title('Bond Yield vs Market Price')
    plt.grid(True)
    plt.show()

def bond_yield_price_duration_convexity_figure_6_2():

    params = BondsManager.init_params()
    params['bond_name'] = 'Test_13_求证 P136上Example计算不同Yield下的pv/duration/convexity'
    params['bond_yield'] = 50 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 10
    params['T_unit'] = 'Y'
    params['semester'] = 1
    # calculate the year and price
    bond_yield_price_list = []
    for bond_yield in range(0, 15, 1):
        params['bond_yield'] = bond_yield / 100
        bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
        # print(rf": {bond_params['bond_yield']}, {bond_params['present_value_total_sum']}")
        bond_yield_price_list.append((bond_params['bond_yield'],
                                      bond_params['present_value_total_sum'],
                                      bond_params['modified_duration'],
                                      bond_params['duration'],
                                      bond_params['convexity']))
    # convert the data list to pd
    bond_yield_price_pd = pd.DataFrame(bond_yield_price_list,
                                       columns=['bond_yield', 'present_value_total_sum', 'modified_duration',
                                                'duration', 'convexity'])
    print(bond_yield_price_pd)
    fig, ax1 = plt.subplots()
    ax1.plot(bond_yield_price_pd['bond_yield'], bond_yield_price_pd['present_value_total_sum'],
             label='present_value_total_sum', color='blue')
    ax1.set_xlabel('Bond Yield')
    ax1.set_ylabel('Present Value Total Sum', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    # Set limits for the first y-axis
    ax1.set_ylim(0, 200)
    # Create the second axis that shares the same x-axis
    ax2 = ax1.twinx()
    # Plot duration, modified_duration, and convexity on the second axis
    ax2.plot(bond_yield_price_pd['bond_yield'], bond_yield_price_pd['duration'] * 7.5, label='duration', color='green')
    ax2.plot(bond_yield_price_pd['bond_yield'], bond_yield_price_pd['modified_duration'] * 7.5,
             label='modified_duration',
             color='orange')
    ax2.plot(bond_yield_price_pd['bond_yield'], bond_yield_price_pd['convexity'], label='convexity', color='red')
    # Set the second y-axis labels and limits
    ax2.set_ylabel('Duration / Modified Duration / Convexity', color='green')
    ax2.tick_params(axis='y', labelcolor='green')
    ax2.set_ylim(0, 100)
    # Add legend for both axes
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.grid(True)
    plt.show()

def bond_convexity_yield_bond_price_figure_6_3():
    global params, bondsManager, estimated_yield, bond_params_pd, bond_information_pd, bond_params, file_full_name
    params = BondsManager.init_params()
    bondsManager = BondsManager(params)
    params['market_price'] = 80
    params['face_value'] = 100
    # params['coupon_rate'] = 0.0252
    params['coupon_rate'] = 0.10
    params['coupon_payment'] = params['face_value'] * params['coupon_rate']
    params['periods'] = 20
    params['tenor'] = 20
    params['T_unit'] = 'Y'
    params['semester'] = 1
    periods_list = np.arange(10, 20, 1)
    periods_market_price_estimated_yield_list = []
    for periods in periods_list:
        params['periods'] = periods

        params['market_price'] = 100
        market_price_range = np.arange(params['market_price'] - 30, params['market_price'] + 30, 0.1)
        market_price_list = []

        for market_price in market_price_range:
            params['market_price'] = market_price
            estimated_yield = bondsManager.calculate_bond_yield(params)
            params['bond_yield'] = estimated_yield

            market_price_list.append((params['market_price'], estimated_yield))
            periods_market_price_estimated_yield_list.append(
                (params["convexity"], params['market_price'], estimated_yield))

        market_price_pd = pd.DataFrame(market_price_list, columns=['market_price', 'estimated_yield'])

        bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
        print(rf"convexity = {params['convexity']}")

        plt.plot(market_price_pd['estimated_yield'], market_price_pd['market_price'],
                 label=rf'Tenor = {periods}, Covexity={float(params["convexity"]):2f}')
    periodsn_market_price_estimated_yield_pd = pd.DataFrame(periods_market_price_estimated_yield_list,
                                                            columns=['coupon_rate', 'market_price', 'estimated_yield'])
    print(periodsn_market_price_estimated_yield_pd)
    file_full_name = FileUtility.get_full_filename_by_timestamp(rf"bonds_figure_6_6_bond_coupon_rate_duration_tenor",
                                                                "xlsx")
    periodsn_market_price_estimated_yield_pd.to_excel(file_full_name)
    plt.xlabel('Bond Yield')
    plt.ylabel('Present Value')
    plt.title('Bond Yield vs Present Value')
    plt.legend()
    plt.grid(True)
    plt.show()

def bond_yield_and_delta_price__figure_6_4():
    # global params, bond_params_pd, bond_information_pd, bond_params, delta_p, predicted_price_with_delta_p
    params = BondsManager.init_params()
    params['bond_name'] = 'Test_14_求证 P138上Example计算30年期零息债券Delta P'
    params['bond_yield'] = 6 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 30
    params['T_unit'] = 'Y'
    params['semester'] = 1
    params['is_zero_coupon'] = True
    bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
    print(rf"duration: {bond_params['duration']}")
    print(rf"bond_yield: {bond_params['bond_yield']}")
    params = bond_params
    # params['modified_duration'] = 19.42/2  # Modified duration
    # params['convexity'] = 395.89/4  # Convexity
    params['delta_y'] = 0.01  # 1% change in yield
    params["market_price"] = 55.368  # Current price of the bond
    bond_delta_price_list = []
    for delta_y in range(0, 10, 1):
        params['delta_y'] = -1 * (delta_y / 100)

        delta_p, predicted_price_with_delta_p = bondsManager.calculate_delta_p_with_modified_duration_and_convexity(params)
        print(
            rf"market_price: {params['market_price']}, delta_p: {delta_p:.8f}, predicted_price_with_delta_p: {predicted_price_with_delta_p:.8f}")
        bond_delta_price_list.append((params['delta_y'],
                                      bond_params['bond_yield'] + params['delta_y'],
                                      bond_params['delta_p'],
                                      bond_params['predicted_price_with_delta_p']))
    for delta_y in range(0, 10, 1):  # 这里仅作理论计算
        # for delta_y in range(30, 31, 1):
        params['delta_y'] = delta_y / 100

        delta_p, predicted_price_with_delta_p = bondsManager.calculate_delta_p_with_modified_duration_and_convexity(
            params)
        print(
            rf"market_price: {params['market_price']}, delta_p: {delta_p:.8f}, predicted_price_with_delta_p: {predicted_price_with_delta_p:.8f}")
        bond_delta_price_list.append((params['delta_y'],
                                      bond_params['bond_yield'] + params['delta_y'],
                                      bond_params['delta_p'],
                                      bond_params['predicted_price_with_delta_p']))
    # convert the data list to pd
    bond_delta_price_pd = pd.DataFrame(bond_delta_price_list,
                                       columns=['delta_y', 'bond_yield', 'delta_p', 'predicted_price_with_delta_p'])
    bond_delta_price_pd = bond_delta_price_pd.sort_values(by='bond_yield')
    print(bond_delta_price_pd)
    # plot the graph
    plt.plot(bond_delta_price_pd['bond_yield'], bond_delta_price_pd['predicted_price_with_delta_p'])
    plt.plot(bond_delta_price_pd['bond_yield'], bond_delta_price_pd['delta_p'])
    plt.xlabel('Bond Yield')
    plt.ylabel('Market Price')
    plt.title('Bond Yield vs Market Price')
    plt.grid(True)
    plt.show()

def portfolio_yield_coupon_maturity_figure_6_6():
    global params, bond_params_pd, bond_information_pd, bond_params, file_full_name
    params = BondsManager.init_params()
    params['bond_name'] = 'Test_2.6_Figure 6.6 P142'
    params['bond_yield'] = 6 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 10
    params['semester'] = 2
    bond_tenor_coupon_rate_duration_list = []
    for tenor in range(1, 11, 1):
        params['tenor'] = tenor
        bond_coupon_rate_duration_list = []

        for coupon_rate in range(0, 21, 1):
            params['coupon_rate'] = coupon_rate / 100
            bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
            print(rf"tenor: {bond_params['tenor']}, bond_yield: {bond_params['coupon_rate']}, duration: {bond_params['duration']}")

            bond_coupon_rate_duration_list.append((bond_params['coupon_rate'], bond_params['duration']))
            bond_tenor_coupon_rate_duration_list.append((bond_params['tenor'], bond_params['coupon_rate'], bond_params['duration']))

        # convert the data list to pd
        bond_coupon_rate_duration_pd = pd.DataFrame(bond_coupon_rate_duration_list, columns=['coupon_rate', 'duration'])
        bond_coupon_rate_duration_pd = bond_coupon_rate_duration_pd.sort_values(by='duration')
        bond_tenor_coupon_rate_duration_pd = pd.DataFrame(bond_tenor_coupon_rate_duration_list,columns=['tenor', 'coupon_rate', 'duration'])
        bond_tenor_coupon_rate_duration_pd = bond_tenor_coupon_rate_duration_pd.sort_values(by=['tenor','coupon_rate','duration'])

        plt.plot(bond_coupon_rate_duration_pd['coupon_rate'], bond_coupon_rate_duration_pd['duration'], label=rf"tenor:{params['tenor']}")

    print(bond_tenor_coupon_rate_duration_pd)
    file_full_name = FileUtility.get_full_filename_by_timestamp(rf"bonds_figure_6_6_bond_coupon_rate_duration_tenor", "xlsx")
    bond_tenor_coupon_rate_duration_pd.to_excel(file_full_name)
    plt.xlabel('Bond Yield')
    plt.ylabel('Duration')
    plt.ylim(0, 10)
    plt.title('coupon_rate vs Duration')
    plt.legend()
    plt.grid(True)
    plt.show()

def portfolio_yield_duration_maturity_figure_6_7():
    global params, bond_params_pd, bond_information_pd, bond_params, file_full_name
    params = BondsManager.init_params()
    params['bond_name'] = 'Test_2.6_Figure 6.7 P142'
    params['bond_yield'] = 6 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 10
    params['semester'] = 2
    bond_tenor_yield_duration_list = []
    for tenor in range(1, 11, 1):
        params['tenor'] = tenor
        bond_yield_duration_list = []

        for bond_yield in range(0, 21, 1):
            params['bond_yield'] = bond_yield / 100
            bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
            print(
                rf"tenor: {bond_params['tenor']}, bond_yield: {bond_params['bond_yield']}, duration: {bond_params['duration']}")

            bond_yield_duration_list.append((bond_params['bond_yield'], bond_params['duration']))
            # bond_tenor_yield_duration_list.append((int(bond_params['tenor']),(bond_params['bond_yield'],bond_params['duration'])))
            bond_tenor_yield_duration_list.append(
                (bond_params['tenor'], bond_params['bond_yield'], bond_params['duration']))

        # convert the data list to pd
        bond_yield_duration_pd = pd.DataFrame(bond_yield_duration_list, columns=['bond_yield', 'duration'])
        bond_yield_duration_pd = bond_yield_duration_pd.sort_values(by='bond_yield')
        bond_tenor_yield_duration_pd = pd.DataFrame(bond_tenor_yield_duration_list,columns=['tenor', 'bond_yield', 'duration'])
        bond_tenor_yield_duration_pd = bond_tenor_yield_duration_pd.sort_values(by=['tenor','bond_yield','bond_yield'])

        plt.plot(bond_yield_duration_pd['bond_yield'], bond_yield_duration_pd['duration'],
                 label=rf"tenor:{params['tenor']}")
    print(bond_tenor_yield_duration_pd)
    file_full_name = FileUtility.get_full_filename_by_timestamp(rf"bonds_figure_6_7_bond_tenor_yield_duration", "xlsx")
    bond_tenor_yield_duration_pd.to_excel(file_full_name)
    plt.xlabel('Bond Yield')
    plt.ylabel('Duration')
    plt.ylim(0, 10)
    plt.title('Bond Yield vs Duration')
    plt.legend()
    plt.grid(True)
    plt.show()


def portfolio_maturity_duration_figure_6_8():
    # global params, bond_params_pd, bond_information_pd, bond_params, file_full_name
    params = BondsManager.init_params()
    # 先计算永续债
    params['bond_name'] = 'Test_8_Table 6.2 P145'
    params['bond_yield'] = 6 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 2
    params['semester'] = 2
    params['is_perpetual_bonds'] = True
    bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
    print(rf"duration: {bond_params['duration']:.8f}, modified_duration: {bond_params['modified_duration']:.8f}")
    maturity_years = range(100)
    durations = [bond_params['duration'] for _ in range(100)]
    plt.plot(maturity_years, durations, label='consel')
    # 再计算其他Bonds
    params = BondsManager.init_params()
    params['bond_name'] = 'Test_8_Table 6.2 P145'
    params['bond_yield'] = 6 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 2
    params['semester'] = 2
    params['is_zero_coupon'] = False
    coupon_rate_dict = {}
    coupon_rate_list = [0, 2, 6, 8, 10, 20]
    for coupon_rate in coupon_rate_list:
        params['coupon_rate'] = coupon_rate / 100
        # params['bond_yield'] = coupon_rate / 100 + 1
        params['bond_name'] = rf"coupon_rate:{params['coupon_rate']}, bond_yield:{params['bond_yield']}"

        duration_list = []
        maturity_years = range(100)
        for maturity_year in maturity_years:
            params['tenor'] = maturity_year + 1
            bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
            duration_list.append(bond_params['modified_duration'])

        coupon_rate_dict[params['bond_name']] = duration_list

        # Plotting
        plt.plot(maturity_years, duration_list, label=params['bond_name'])
    coupon_rate_dict_pd = pd.DataFrame(coupon_rate_dict)
    file_full_name = FileUtility.get_full_filename_by_timestamp(rf"Figure-Maturity-Duration Figure 6.8", "xlsx")
    coupon_rate_dict_pd.to_excel(file_full_name)
    plt.xlabel('Maturity Years')
    plt.ylabel('Duration')
    plt.title('Maturity Years vs Duration')
    plt.grid(True)
    plt.legend()
    plt.ylim(0, 20)
    plt.show()

def bond_duration_table_6_3():
    params_list = [
        {
            'bond_name': 'T=10Y, Coupon Rate=6%, Yield=6%',
            'bond_yield': 6 / 100,
            'face_value': 100,
            'coupon_rate': 6 / 100,
            'tenor': 10,
            'semester': 2,
            'market_price': 100,
            'number_of_bonds': 10000,
            'weight_of_bonds_portfolio': 75.83 / 100,
            'is_zero_coupon': False,
        },
        {
            'bond_name': 'T=1Y, Coupon Rate=0%, Yield=6%',
            'bond_yield': 6 / 100,
            'face_value': 100,
            'coupon_rate': 0 / 100,
            'tenor': 1,
            'semester': 2,
            'market_price': 94.26,
            'number_of_bonds': 5000,
            'weight_of_bonds_portfolio': 36.21 / 100,
            'is_zero_coupon': False,
        },
        {
            'bond_name': 'T=30Y, Coupon Rate=6%, Yield=6%',
            'bond_yield': 6 / 100,
            'face_value': 100,
            'coupon_rate': 0 / 100,
            'tenor': 30,
            'semester': 1,
            'market_price': 16.97,
            'number_of_bonds': -10000,
            'weight_of_bonds_portfolio': -13.04 / 100,
            'is_zero_coupon': True,
        },
    ]
    params_specific_bond_list = []
    for params_specific_bond in params_list:
        params = BondsManager.init_params()
        params.update(params_specific_bond)

        # 计算基本指标
        bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
        print(
            rf"bond_name: {bond_params['bond_name']}, market_price: {bond_params['market_price']:6f}, duration: {bond_params['duration']:6f}, modified_duration: {bond_params['modified_duration']:6f}, convexity: {bond_params['convexity']:6f}")

        # 计算portfolio 收益
        bond_params = bondsManager.calculate_bond_portfolio_information(params)
        print(
            rf"dollar_amounts: {bond_params['dollar_amounts']}, dollar_duration: {bond_params['dollar_duration']}, portfolio_dollar_duration: {bond_params['portfolio_dollar_duration']}, portfolio_dollar_convexity: {bond_params['portfolio_dollar_convexity']}")

        bond_params['bond_information_pd'] = None
        params_specific_bond_list.append(bond_params)
    params_specific_bond_df = pd.DataFrame(params_specific_bond_list)
    file_full_name = FileUtility.get_full_filename_by_timestamp(rf"Bond_portfolio_analysis", "xlsx")
    bond_params_pd_T = params_specific_bond_df.T
    bond_params_pd_T.to_excel(file_full_name)
    print(bond_params_pd_T)


if __name__ == "__main__":
    pd.set_option('display.max_columns', None)  # 设置为None表示不限制列数
    pd.set_option('display.width', None)  # 自动检测控制台的宽度
    pd.set_option('display.max_colwidth', None)  # 设置列的最大宽度

    params = BondsManager.init_params()
    bondsManager = BondsManager(params)

    ###################################
    # 1.1 Calculate Present Value (6.1)
    ###################################
    params['T'] = 10
    params['T_unit'] = 'Y'
    params['payment'] = 100
    params['bond_yield'] = 0.06
    params['face_value'] = 1000

    bondsManager.set_params(params)
    present_value = bondsManager.calculate_present_value(params)
    print(rf"Calculate Present Value: params['present_value'] = {params['present_value']:6f}")

    ###################################
    # 1.2. Calculate Future Value (6.2)
    ###################################
    params = BondsManager.init_params()

    params['T'] = 10
    params['T_unit'] = 'Y'
    params['bond_yield'] = 0.06
    params['present_value'] = 100

    future_value = bondsManager.calculate_future_value(params)
    print(rf"Calculate Future Value: params['future_value'] = {params['future_value']:6f}")
    future_value = bondsManager.calculate_future_value_with_continues_compounded(params)
    print(rf"Calculate Future Value with continues compounded: params['future_value'] = {params['future_value']:6f}")

    ##################################################
    # 1.3. Calculate Present Value with semesters (6.3)
    ##################################################
    params = BondsManager.init_params()

    params['T'] = 10
    params['T_unit'] = 'Y'
    params['payment'] = 100
    params['bond_yield'] = 0.06
    params['face_value'] = 1000
    params['semesters'] = 2

    present_value = bondsManager.calculate_present_value_with_semesters(params)
    print(rf"Calculate Present Value with semesters: params['present_value'] = {params['present_value']:6f}")

    ################################################################
    # 1.4. Calculate Presentation with continues compounding (6.5)
    ################################################################
    params = BondsManager.init_params()

    params['T'] = 10
    params['T_unit'] = 'Y'
    params['payment'] = 100
    params['bond_yield'] = 0.06

    present_value = bondsManager.calculate_present_value_with_continues_compounded(params)
    print(rf"Presentation with continues compounding: params['present_value'] = {params['present_value']:6f}")

    ################################################################
    # 1.5. Calculate EAR(effective annual rate) (Example 6.1)
    ################################################################
    params = BondsManager.init_params()

    params['T'] = 1
    params['T_unit'] = 'M'
    params['present_value'] = 987
    params['future_value'] = 1000

    EAR = bondsManager.calculate_EAR(params)
    print(rf"Calculate EAR: params['EAR'] = {params['EAR']:6f}")

    ################################################################
    # 1.6. Convert the given rate to EAR (Example 6.2)
    ################################################################
    params = BondsManager.init_params()
    params_list = [{'T_unit': 'M', 'bond_yield': 7.82 / 100},
                   {'T_unit': 'Q', 'bond_yield': 8.00 / 100},
                   {'T_unit': 'H', 'bond_yield': 8.05 / 100},
                   {'T_unit': 'C', 'bond_yield': 7.95 / 100}]

    for params in params_list:
        EAR = bondsManager.convert_to_annual_rate(params)
        print(rf"Calculate effecitve EAR:{params['T_unit']}:{params['bond_yield']}: {EAR:6f}")


    ################################################################
    # 1.6. 计算收delta P , p140, exmaple 6.6
    ################################################################
    params = BondsManager.init_params()
    params['bond_name'] = '计算收delta P , p140, exmaple 6.6'
    params['modified_duration'] =8
    params['convexity']=150
    params['delta_y'] = 25/10000
    params["market_price"] = 100 * 1000000

    delta_p, predicted_price_with_delta_p = bondsManager.calculate_delta_p_with_modified_duration_and_convexity(params)
    print(rf"delta_p={delta_p}, predicted_price_with_delta_p={predicted_price_with_delta_p}")

    params = BondsManager.init_params()
    params['bond_name'] = '计算收delta P , p140, exmaple 6.6'
    params['modified_duration'] =8
    params['convexity']=150
    params['delta_y'] = 50/10000
    params["market_price"] = 100 * 1000000

    delta_p, predicted_price_with_delta_p = bondsManager.calculate_delta_p_with_modified_duration_and_convexity(params)
    print(rf"delta_p={delta_p}, predicted_price_with_delta_p={predicted_price_with_delta_p}")


    ################################################################
    # 1.7. 计算收益率 calculate_bond_yield
    ################################################################
    params = BondsManager.init_params()
    params['market_price'] = 99.265
    params['face_value'] = 100
    params['coupon_rate'] = 0.0252
    params['coupon_payment'] = params['face_value'] * params['coupon_rate']
    params['periods'] = 20

    estimated_yield = bondsManager.calculate_bond_yield(params)
    print(rf"calculate_bond_yield: {estimated_yield:.8f}")

    ################################################################
    # 1.8. Calculate bond information - Pandas 上的实验
    #    计算 duration/久期
    ################################################################
    params = BondsManager.init_params()

    params['bond_name'] = 'Test_7'
    params['bond_yield'] = 5 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 3
    params['semester'] = 2

    bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)

    file_full_name = FileUtility.get_full_filename_by_timestamp(rf"{params['bond_name']}_bond_yield({params['bond_yield']})_face_value({params['face_value']})_coupon_rate({params['coupon_rate']})_tenor({params['tenor']})_semester({params['semester']})", "xlsx")
    bond_information_pd.to_excel(file_full_name)
    print(bond_information_pd)

    file_full_name = FileUtility.get_full_filename_by_timestamp(rf"All_params_{params['bond_name']}_bond_yield({params['bond_yield']})_face_value({params['face_value']})_coupon_rate({params['coupon_rate']})_tenor({params['tenor']})_semester({params['semester']})", "xlsx")
    bond_params_pd.to_excel(file_full_name)
    print(bond_params_pd)
    print(bondsManager.params)


    ################################################################
    # 1.9. Calculate bond information - Table 6.2 P145
    #    计算 duration/久期
    ################################################################
    params = BondsManager.init_params()

    params['bond_name'] = 'Test_8_Table 6.2 P145'
    params['bond_yield'] = 6 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 2
    params['semester'] = 2

    bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)

    # 写债券的摘要信息
    file_full_name = FileUtility.get_full_filename_by_timestamp(rf"All_params_{params['bond_name']}_bond_yield({params['bond_yield']})_face_value({params['face_value']})_coupon_rate({params['coupon_rate']})_tenor({params['tenor']})_semester({params['semester']})", "xlsx")
    bond_params_pd.to_excel(file_full_name)
    print(bond_params_pd)
    print(bondsManager.params)

    #写债券的每期信息 bond_information_pd
    file_full_name = FileUtility.get_full_filename_by_timestamp(rf"{params['bond_name']}_bond_yield({params['bond_yield']})_face_value({params['face_value']})_coupon_rate({params['coupon_rate']})_tenor({params['tenor']})_semester({params['semester']})", "xlsx")
    bond_information_pd.to_excel(file_full_name)
    print(bond_information_pd)

    ################################################################
    # 1.10. Calculate modified duration/久期
    ################################################################
    # 参数直接传入
    modified_duration = bondsManager.calculate_modified_duration(bond_params['duration'], bond_params['bond_yield'], bond_params['semester'])
    print(rf"modified_duration: {modified_duration:.8f}")

    # 不传入参数， 直接用self.params
    modified_duration = bondsManager.calculate_modified_duration(duration=None, bond_yield=None, semester=None )
    print(rf"modified_duration: {modified_duration:.8f}")

    ################################################################
    # 1.11. Calculate modified duration/久期 + dvbp
    ################################################################
    # 参数直接传入
    bond_params['market_price'] = 90
    dollar_duration, dvbp = bondsManager.calculate_dollar_duration_DVBP(bond_params['modified_duration'], bond_params['market_price'])
    print(rf"dollar_duration: {dollar_duration:.8f}, dvbp: {dvbp:.8f}")

    # 不传入参数， 直接用self.params
    dollar_duration, dvbp = bondsManager.calculate_dollar_duration_DVBP(duration=None, market_price=None)
    print(rf"dollar_duration: {dollar_duration:.8f}, dvbp: {dvbp:.8f}")

    ################################################################
    # 1.12. Calculate Delta p - 6.19/P135 Example
    ################################################################
    params['modified_duration'] = 19.42/2  # Modified duration
    params['convexity'] = 395.89/4  # Convexity
    params['delta_y'] = 0.01  # 1% change in yield
    params["market_price"] = 55.368  # Current price of the bond

    delta_p, predicted_price_with_delta_p = bondsManager.calculate_delta_p_with_modified_duration_and_convexity(params)
    print(rf"market_price: {params['market_price']}, delta_p: {delta_p:.8f}, predicted_price_with_delta_p: {predicted_price_with_delta_p:.8f}")

    # 求证 P135上Example计算10年期债券Duration
    params = BondsManager.init_params()
    params['bond_name'] = 'Test_9_求证 P135上Example计算10年期债券Duration'
    params['bond_yield'] = 6 / 100
    params['face_value'] = 100
    params['coupon_rate'] = 6 / 100
    params['tenor'] = 20
    params['T_unit'] = 'Y'
    params['semester'] = 2
    params['is_zero_coupon'] = True

    bond_params_pd, bond_information_pd, bond_params = bondsManager.calculate_bond_information(params)
    print(rf"duration: {bond_params['duration']}")
    params['market_price'] = 55.368
    dollar_duration, dvbp = bondsManager.calculate_dollar_duration_DVBP(bond_params['modified_duration'], params['market_price'])
    print(rf"dollar_duration: {dollar_duration:.8f}, dvbp: {dvbp:.8f}")

    ################################################################
    # 2.1. Calculate bond present vale figur 6.1
    #    计算不同yield下的present value
    ################################################################
    # bond_yield_price_figure_6_1()

    ################################################################
    # 2.2. Calculate bond present vale figur 6.2
    #    计算不同yield下的present value, duration, convexity
    ################################################################
    # bond_yield_price_duration_convexity_figure_6_2()

    ################################################################
    # 2.3. Calculate bond present vale figur 6.3
    #    计算不同Covexity下的Yield和Bond price 的关系
    ################################################################
    bond_convexity_yield_bond_price_figure_6_3()

    ################################################################
    # 2.4. Calculate delta_p with delta_yield
    ################################################################
    # bond_yield_and_delta_price__figure_6_4()

    ################################################################
    # 2.5. Calculate delta_p with delta_yield
    ################################################################
    # portfolio_yield_coupon_maturity_figure_6_6()

    ################################################################
    # 2.6. Calculate bond information - Figure 6.7
    #    计算 不同Yield 下的 duration
    ################################################################
    # portfolio_yield_duration_maturity_figure_6_7()

    ################################################################
    # 2.7. Calculate bond information - Figure 6.8
    #    计算 不同Maturity Date 下的 duration/久期
    ################################################################
    # portfolio_maturity_duration_figure_6_8()

    ################################################################
    # 2.8. Compare Dollar Duration of different bonds  Table 6.3 p149
    #    计算 duration/久期
    ################################################################
    # bond_duration_table_6_3()


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mplcursors
import numpy_financial as npf

class RateManager:
    def __init__(self, interest_rate):
        self.interest_rate = interest_rate  # compounding interest_rate (annual)

    def calculate_FV(self, PV, periods, interest_rate=0.00, method='compounding'):

        if method == 'compounding':
            FV = PV * (1 + interest_rate) ** periods
        elif method == 'exponential':
            FV = PV * np.exp(interest_rate * periods)
        else:
            raise ValueError("Invalid method. Choose 'compounding' or 'exponential'.")
        return FV

    def calculate_PV(self, FV, periods, interest_rate=0.00, method='compounding'):
        if method == 'compounding':
            PV = FV / (1 + interest_rate) ** periods
        elif method == 'exponential':
            PV = FV / np.exp(interest_rate * periods)
        else:
            raise ValueError("Invalid method. Choose 'compounding' or 'exponential'.")
        return PV

    def calculate_interest_rate(self, PV, FV, periods, method='compounding'):
        if method == 'compounding':
            interest_rate = (FV / PV) ** (1 / periods) - 1
        elif method == 'exponential':
            interest_rate = np.log(FV / PV) / periods
        else:
            raise ValueError("Invalid method. Choose 'compounding' or 'exponential'.")
        return interest_rate

    def calculate_IRR(self, cash_flows):
        irr = np.irr(cash_flows)
        return irr

    ###################################################
    # np.npf function for caculating FV/PV/NPV/IRR
    ###################################################
    def npf_fv(self, rate = 0.05,number_of_periods = 5, pmt = 0,pv = -1000 ):
        FV = npf.fv(rate, number_of_periods, pmt, pv)

        return FV

    def npf_pv(self, rate=0.05, number_of_periods=5, pmt=0, fv=1000, when='end'):
        PV = npf.pv(rate, number_of_periods, pmt, fv, when)
        return PV

    def npf_npv(self, rate=0.05, cash_flows=[-1000, 200, 300, 400, 500]):
        NPV = npf.npv(rate, cash_flows)
        return NPV

    def npf_irr(self, cash_flows=[-1000, 200, 300, 400, 500]):
        IRR = npf.irr(cash_flows)
        return IRR

    def npf_calculate_loan_cashflows(self, interest_rate, loan_amount, periods):
        # Initialize empty lists to hold the cash flows
        payments = []
        interest_payments = []
        principal_payments = []
        period_list = list(range(1, periods + 1))

        for period in period_list:
            payment = npf.pmt(interest_rate / 12, periods, loan_amount)
            interest_payment = npf.ipmt(interest_rate / 12, period, periods, loan_amount)
            principal_payment = npf.ppmt(interest_rate / 12, period, periods, loan_amount)

            payments.append(payment)
            interest_payments.append(interest_payment)
            principal_payments.append(principal_payment)

        # Create a DataFrame
        loan_df = pd.DataFrame({
            'period': period_list,
            'payment': payments,
            'interest_payment': interest_payments,
            'principal_payment': principal_payments
        })

        return loan_df

if __name__ == '__main__':
    rate_manager = RateManager(interest_rate=0.00)

    ####################################
    #Test 1.1 Calculate FV
    ####################################
    PV = 1000
    periods = 5
    interest_rate = 0.05
    FV_compounding = rate_manager.calculate_FV(PV, periods, interest_rate, method='compounding')
    FV_exponential = rate_manager.calculate_FV(PV, periods, interest_rate, method='exponential')
    print(rf"FV_compounding:{FV_compounding:6f}")
    print(rf"FV_exponential:{FV_exponential:6f}")

    ####################################
    #Test 1.2 Calculate PV
    ####################################
    FV = 1276.281563
    periods = 5
    interest_rate = 0.05
    PV_compounding = rate_manager.calculate_PV(FV, periods, interest_rate, method='compounding')
    print(rf"PV_compounding:{PV_compounding:6f}")

    FV = 1284.025417
    periods = 5
    interest_rate = 0.05
    PV_exponential = rate_manager.calculate_PV(FV, periods, interest_rate, method='exponential')
    print(rf"PV_exponential:{PV_exponential:6f}")

    ####################################
    # Test 1.3 Calculate interest_rate
    ####################################
    PV = 1000
    FV = 1276.281563
    periods = 5
    interest_rate_compounding = rate_manager.calculate_interest_rate(PV, FV, periods, method='compounding')
    print(rf"interest_rate_compounding:{interest_rate_compounding:6f}")

    PV = 1000
    FV = 1284.025417
    periods = 5
    interest_rate_exponential = rate_manager.calculate_interest_rate(PV, FV, periods, method='exponential')
    print(rf"interest_rate_exponential:{interest_rate_exponential:6f}")

    ####################################
    # Test 1.4 Plot yield curve
    ####################################
    PV = 1000
    interest_rate_range = np.arange(0.01, 0.07, 0.02)  # Rates from 0.05 to 0.15
    period_range = np.arange(1, 31)  # Periods from 1 to 30

    # Initialize lists to store results
    data_FV_compounding = []
    data_FV_exponential = []
    data_FV = []

    # Calculate FV for each combination of interest_rate and period using both methods
    for interest_rate in interest_rate_range:
        for period in period_range:
            FV_compounding = PV * (1 + interest_rate) ** period  # Compounding method
            FV_exponential = PV * np.exp(interest_rate * period)  # Exponential method

            # Append results to respective lists
            data_FV_compounding.append([f"compounding_{interest_rate:.2f}", period, FV_compounding])
            data_FV_exponential.append([f"exponential_{interest_rate:.2f}", period, FV_exponential])

    # Create DataFrames from the data
    df_compounding = pd.DataFrame(data_FV_compounding, columns=['interest_rate', 'period', 'FV'])
    df_exponential = pd.DataFrame(data_FV_exponential, columns=['interest_rate', 'period', 'FV'])
    #data_FV.extend(data_FV_exponential)

    data_combined = data_FV_compounding + data_FV_exponential
    df_combined = pd.DataFrame(data_combined, columns=['interest_rate', 'period', 'FV'])

    # Display the DataFrames
    print("Compounding Method DataFrame:")
    print(df_compounding)
    df_compounding.to_excel(rf"e:\tmp\df_compounding.xlsx")
    print("\nExponential Method DataFrame:")
    print(df_exponential)
    df_exponential.to_excel(rf"e:\tmp\df_exponential.xlsx")

    df_combined.to_excel(rf"e:\tmp\df_combined.xlsx")

    # Plot the frame
    for interest_rate, group in df_combined.groupby('interest_rate'):
        plt.plot(group['period'], group['FV'], label=interest_rate)
    plt.xlabel('Period')
    plt.ylabel('Future Value (FV)')
    plt.title('FV vs Period for Different Rates')
    plt.legend()

    mplcursors.cursor(hover=True).connect("add", lambda sel: sel.annotation.set_text(f'Rate: {sel.artist.get_label()}'))

    # Show the plot
    # plt.show() # 注释此处，只是为了让测试快点

    #################################################
    # Test 2.1 use npf.fv calculate the future value
    #################################################
    rate_manager = RateManager(interest_rate=0.00)

    rate = 0.05  # Interest rate per period
    number_of_periods = 5  # Number of periods
    pmt = 0  # No periodic payment
    pv = -1000  # Present value (initial investment)
    fv = rate_manager.npf_fv(rate, number_of_periods, pmt, pv)

    print(f"Future Value: {fv:.2f}")

    #################################################
    # Test 2.2 use npf.fv calculate the present value
    #################################################
    rate_manager = RateManager(interest_rate=0.00)

    rate = 0.05  # Interest rate per period
    number_of_periods = 5  # Number of periods
    pmt = 0  # No periodic payment
    fv = 1276.28  # Future value (the amount you want to discount)

    pv = rate_manager.npf_pv(rate, number_of_periods, pmt, fv)

    print(f"Present Value: {pv:.2f}")

    #################################################
    # Test 2.3 use npf_npv calculate the npv
    #################################################
    rate_manager = RateManager(interest_rate=0.00)

    rate = 0.05  # Discount rate per period
    cash_flows = [-1000, 200, 300, 400, 500]  # Cash flows (initial investment + future returns)

    npv = rate_manager.npf_npv(rate, cash_flows)

    print(f"Net Present Value: {npv:.2f}")

    ####################################
    # Test 2.4 Calculate IRR
    ####################################
    cash_flows = [-1000, 200, 300, 400, 500]  # Cash flows (initial investment + future returns)
    irr = rate_manager.npf_irr(cash_flows)
    print(f"Internal Rate of Return: {irr:.2f}")

    ####################################
    # Test 2.5 Calculate Cashflow
    ####################################
    rate_manager = RateManager(interest_rate=0.05)

    interest_rate = 0.05
    loan_amount = 10000
    periods = 12

    loan_cashflows_df = rate_manager.npf_calculate_loan_cashflows(interest_rate, loan_amount, periods)
    print(loan_cashflows_df)

    plt.figure(figsize=(10, 6))

    # Plot each of the required columns
    plt.plot(loan_cashflows_df['period'], loan_cashflows_df['payment'], label='Payment', color='blue')
    plt.plot(loan_cashflows_df['period'], loan_cashflows_df['interest_payment'], label='Interest Payment', color='red')
    plt.plot(loan_cashflows_df['period'], loan_cashflows_df['principal_payment'], label='Principal Payment', color='green')

    # Add labels and title
    plt.xlabel('Period')
    plt.ylabel('Amount')
    plt.title('Loan Cashflows Over Periods')

    # Add a legend
    plt.legend()

    # Show the plot
    plt.grid(True)
    plt.show()
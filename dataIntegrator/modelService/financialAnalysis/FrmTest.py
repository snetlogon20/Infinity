from dataIntegrator.modelService.financialAnalysis.InformationRatio import InformationRatio
from dataIntegrator.modelService.financialAnalysis.SharpRatio import SharpRatio
from dataIntegrator.modelService.financialAnalysis.TrackingError import TrackingError

if __name__ == "__main__":
    #Example 1.6
    sharp_ratio_caculator = SharpRatio()
    sharpe_ratio_rate = sharp_ratio_caculator.caculate_sharp_ratio(10/100,20/100,3/100)
    print(f'sharpe_ratio_rate: {sharpe_ratio_rate}')

    trackingError = TrackingError()
    tev = trackingError.caculate_TEV_with_number(0.14,0.2,0.98)
    print(f'tev: {tev}')

    informationRatio = InformationRatio()
    information_ratio = informationRatio.caculate_information_ratio(0.08, 0.1, tev)

    print(f'information_ratio: {information_ratio:.6f}')
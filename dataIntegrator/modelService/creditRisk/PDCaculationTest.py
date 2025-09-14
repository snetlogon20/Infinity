from dataIntegrator.modelService.creditRisk.PDCaculation import PDCaculation


def test_caculate_pd_by_yield_lgd():
    '''
    P505 Example
    '''
    global T
    recover_rate = 0.45
    risk_free_rate = 0.06
    yield_rate = 0.07
    T = 10
    interest_payment_times_in_one_year = 2
    tenor = T * interest_payment_times_in_one_year
    r = risk_free_rate / interest_payment_times_in_one_year
    y = yield_rate / interest_payment_times_in_one_year
    LGD = 1 - recover_rate
    pi = PDCaculation().caculate_pd_with_yield(LGD, r, y, tenor)
    print(pi)

def test_caculate_EDF_with_Merton_model():
    # Page 517 21.2.4 Example

    # 使用自定义参数计算
    print("\n使用自定义参数计算:")
    pdCaculation = PDCaculation()

    results = pdCaculation.caculate_EDF_with_Merton_model(
        Asset_V=100,
        sigma=0.2,
        T=1,
        risk_free_rate=0.1,
        Bond_Face_Value_K=99.46,
        S=13.59,
        Leverage_Rate=0.9
    )
    for key, value in results.items():
        print(f"{key}: {value}")

if __name__ == '__main__':

    #test_caculate_pd_by_yield_lgd()

    test_caculate_EDF_with_Merton_model()


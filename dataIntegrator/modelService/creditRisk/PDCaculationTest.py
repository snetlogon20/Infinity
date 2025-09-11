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


if __name__ == '__main__':

    test_caculate_pd_by_yield_lgd()


class PDCaculation:
    def __init__(self):
       pass
    def caculate_pd_with_yield(self,LGD, r, y, tenor):
        pd = 1 - (1 + r)**tenor / (1 + y)**tenor

        pi = pd/LGD
        return pi

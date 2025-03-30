import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from sklearn.isotonic import IsotonicRegression
from sklearn.utils import check_random_state
import tushare as ts
from dataIntegrator.TuShareService.TuShareService import TuShareService
import pandas
from clickhouse_driver import Client as ClickhouseClient
import tushare as ts
from pandas import DataFrame
from dataIntegrator.common import CommonLib
from dataIntegrator.common.CommonParameters import CommonParameters


def main():
    print("callTushareUSStockBasicService started...")

    start_date = '20180101'
    end_date = '20230924'

    dataFrame = pandas.core.frame.DataFrame
    jsonString = ""
    token = CommonParameters.tuShareToken

    pro = ts.pro_api()

    dataFrame = pro.us_daily(ts_code='C', start_date=start_date, end_date=end_date)
    dataFrame.columns = ['ts_code',
                              'trade_date',
                              'close_point',
                              'open_point',
                              'high_point',
                              'low_point',
                              'pre_close',
                              'pct_change',
                              'vol',
                              'amount',
                              'vwap']
    dataFrame.sort_values('trade_date', ascending=True)
    print(dataFrame)
    #一天只能5次。先保存
    dataFrame.to_excel(r"D:\workspace_python\practice\data\citistock\citistock.xlsx", index=False, header=None, mode='w', encodeing='gbk')

    data = dataFrame.to_numpy()
    x=data[:,1]

    #data = np.loadtxt(open(r"D:\workspace_python\practice\data\sofr\sofr_3.csv","rb"),delimiter=",",skiprows=0)
    y=data[:,2]

    n = len(data)

    # ##产生一个0-99的列表
    # x = np.arange(n)
    # print(type(x))
    # ##实例化一个np.random.RandomState的实例，作用是每次取的随机值相同
    # rs = check_random_state(0)
    # ##randint(-50, 50)：产生-50到50之间的整数
    # ##np.log  求以e为低的对数
    # y = rs.randint(-50, 50, size=(n,)) + 50. * np.log(1 + np.arange(n))
    # print(type(y))

    ##设置保序回归函数
    ir = IsotonicRegression()
    ##训练数据
    y_ = ir.fit_transform(x, y)
    print(y_)
    for i in range(len(y_)):
        print(y_[i])

    ##绘图
    segments = [[[i, y[i]], [i, y_[i]]] for i in range(n)]
    ##plt.gca().add_collection(lc),这两步就是画点与平均直线的连线
    lc = LineCollection(segments)

    fig = plt.figure()
    plt.plot(x, y, 'r.', markersize=12)
    plt.plot(x, y_, 'g.-', markersize=12)
    plt.gca().add_collection(lc)
    plt.legend(('Data', 'Isotonic Fit'), loc='lower right')
    plt.title('Isotonic regression')
    plt.show()

if __name__ == '__main__':
    main()



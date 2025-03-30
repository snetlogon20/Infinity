import importlib
import pandas as pd

def test_import():
    module_name = "dataIntegrator.TuShareService.TuShareServiceManager"
    my_module = __import__(module_name)
    print("test_import imported module: ", my_module)
    print("test_import module: ", dir(my_module))

    class_name = "TuShareServiceManager"
    class_ = getattr(my_module, class_name)
    print("test_import get class: ", class_)

    obj = class_()
    #for attr in dir(obj):
    print("test_import obj attr: ", dir(obj))

    func = getattr(obj, "callTuShareChinaStockIndexService")
    func()


def test_import_class():
    module_name = "dataIntegrator.TuShareService.TuShareServiceManager"
    class_name = "TuShareServiceManager"
    my_module = __import__(module_name, globals(), locals(), fromlist=[class_name])
    print("test_import_class imported module: ", my_module)
    print("test_import_class module: ", dir(my_module))


def test_importlib():
    module_name = "dataIntegrator.TuShareService.TuShareServiceManager"
    class_name = "TuShareServiceManager"
    my_module = importlib.import_module(".", module_name)
    print("test_importlib imported module: ", my_module)
    print("test_importlib module: ", dir(my_module))

    importlib.reload(my_module)


def test_plot():
    import statsmodels.tsa.api as smt
    import tushare as ts
    import pandas as pd
    import matplotlib.pyplot as plt

    pro = ts.pro_api()

    df = pro.daily(ts_code='000001.SZ', start_date='20220101', end_date='20220528')
    df.index = pd.to_datetime(df['trade_date'], format="%Y%m%d")

    # 自相关 atuo-correlation coefficient
    ac = smt.acf(df['close'], nlags=30)
    print(ac)

    # 偏自相关 atuo-correlation coefficient
    pac = smt.pacf(df['close'], nlags=20)
    print(ac)

    fg = plt.figure()

    # 设置子图
    # 此处add_subplot方法的参数是一个三位数
    # 百位上的数代表画布上下分成几块
    # 十位上的数代表画布左右分成几块
    # 个位上的数代表该块副画布的编号
    ts_ax = fg.add_subplot(311)
    acf_ax = fg.add_subplot(311)
    pacf_ax = fg.add_subplot(313)

    # 绘制图像
    ts_ax.set_title('time series')
    acf_ax.set_title('autocorrelation coecient')
    pacf_ax.set_title('partial autocorrelation coefhcient')
    ts_ax.plot(df['close'])

    smt.graphics.plot_acf(df['close'], lags=10, ax=acf_ax)
    smt.graphics.plot_pacf(df['close'], lags=5, ax=pacf_ax)

    # 自适应布局
    plt.tight_layout()
    plt.show()

    def test_exec1():
        # 样本数
        n_sample = 1000
        # 白噪声过程
        w = np.random.normal(size=n_sample)
        # 随机游走过程
        x = np.zeros(n_sample)

        for t in range(n_sample):
            x[t] = x[t - 1] + w[t]

        # 可视化
        fg = plt.figure()
        ax_w = fg.add_subplot(211)
        ax_x = fg.add_subplot(212)
        ax_w.set_title('White Noise')
        ax_x.set_title('Random Walk')
        ax_w.plot(w)
        ax_x.plot(x)
        plt.show()

    import statsmodels.tsa.api as smt
    import pandas as pd
    import matplotlib.pyplot as plt
    def draw_ac_pac(series, nlags = 30):
        fg = plt.figure()
        # 设置子图
        ts_ax = fg.add_subplot(311)
        acf_ax = fg.add_subplot(312)
        pacf_ax = fg.add_subplot(313)
        # 绘制图像
        ts_ax.settitle('time series')

        acf_ax.set_title('autocorrelation coeficient')
        pacf_ax.set_title('partial autocorrelation coefcient')
        ts_ax.plot(series)
        smt.graphics.plot_acf(series, lags=nlags, ax=acf_ax)
        smt.graphics.plot_pacf(series, lags=nlags, ax=pacf_ax)
        #自适应布局
        plt.tight_layout()
        plt.show()

    def test_exec2():
        df = pro.daily(ts_code='000001.SZ', start_date='20220101', end_date='20220528')
        df.index = pd.to_datetime(df['trade_date'], format="%Y%m%d")
        # 可视化自相关和偏自相关系数
        draw_ac_pac(df['close'])

def test_exec():
    lo = locals()
    module_name = "dataIntegrator.TuShareService.TuShareServiceManager"
    class_name = "TuShareServiceManager"
    import_str = "import {}".format(module_name)

    my_module = exec(import_str)
    print("test_exec imported module: ", lo[module_name])
    print("test_exec module: ", dir(lo[module_name]))


def test_read_excel():
    df = pd.read_excel("D:\workspace_python\practice\data\Book1.xlsx",sheet_name=None)
    for sheet in df:
        print(sheet)

    for sheet_name, df in pd.read_excel(r"D:\workspace_python\practice\data\Book1.xlsx", index_col=0, sheet_name=None).items():
        df.to_csv(f'D:\workspace_python\practice\data\output_{sheet_name}.csv', index=True, encoding='utf-8')

if __name__ == "__main__":
    test_read_excel()
    test_plot()
    test_import()
    test_import_class()
    test_importlib()
    test_exec()
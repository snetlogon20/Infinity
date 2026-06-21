import os
import datetime

from dataIntegrator import CommonParameters
from dataIntegrator.common.MyTokens import MyTokens
from dataIntegrator.modelService.commonService.CalendarService import CalendarService


class CommonDataParameters():

    @classmethod
    def get_start_date(cls, days=360):
        """
        动态获取起始日期（从今天往前推算指定天数）

        参数:
        - days: 往前推算的天数，默认360天

        返回:
        - start_date: 起始日期字符串，格式 'YYYYMMDD'
        """
        calendarService = CalendarService()
        return calendarService.calculate_T_minus_n_days(CommonParameters.today, days=days)

    CN_INDEX_LIST = [
        '000001.SH',  # 上证指数
        '399001.SZ',  # 深证成指
        '000300.SH',  # 沪深300
        '000905.SH',  # 中证500
        '000852.SH',  # 中证1000
        '399006.SZ',  # 创业板指
    ]

    # STOCK_LIST=[
    #         {'ts_code': '002093.SZ', 'name': '国脉科技'},
    #         {'ts_code': '600490.SH', 'name': '鹏欣资源'},
    #         {'ts_code': '000902.SZ', 'name': '新洋丰'},
    #         {'ts_code': '601368.SH', 'name': '绿城水务'},
    #         {'ts_code': '603839.SH', 'name': '安正时尚'},
    #         {'ts_code': '000546.SZ', 'name': '金圆股份'},
    #         {'ts_code': '600470.SH', 'name': '六国化工'},
    #         {'ts_code': '600519.SH', 'name': '贵州茅台'},
    #         {'ts_code': '688498.SH', 'name': '源杰科技'},
    #     ]
    # STOCK_LIST = [
    #     {'ts_code': '002093.SZ', 'name': '国脉科技'},
    #     {'ts_code': '600490.SH', 'name': '鹏欣资源'},
    #     {'ts_code': '000902.SZ', 'name': '新洋丰'},
    #     {'ts_code': '601368.SH', 'name': '绿城水务'},
    #     {'ts_code': '603839.SH', 'name': '安正时尚'},
    #     {'ts_code': '000546.SZ', 'name': '金圆股份'},
    #     {'ts_code': '600470.SH', 'name': '六国化工'},
    #     {'ts_code': '600519.SH', 'name': '贵州茅台'},
    #     {'ts_code': '688498.SH', 'name': '源杰科技'},
    #     {'ts_code': '601318.SH', 'name': '中国平安'},
    #     {'ts_code': '600036.SH', 'name': '招商银行'},
    #     {'ts_code': '601012.SH', 'name': '隆基绿能'},
    #     {'ts_code': '000858.SZ', 'name': '五粮液'},
    #     {'ts_code': '000333.SZ', 'name': '美的集团'},
    #     {'ts_code': '600276.SH', 'name': '恒瑞医药'},
    #     {'ts_code': '601888.SH', 'name': '中国中免'},
    # ]
    STOCK_LIST = [
        # ==================== 1. 高科技（半导体/AI芯片/光模块）====================
        {'ts_code': '688498.SH', 'name': '源杰科技'},
        {'ts_code': '688256.SH', 'name': '寒武纪-U'},
        {'ts_code': '688041.SH', 'name': '海光信息'},
        {'ts_code': '300308.SZ', 'name': '中际旭创'},
        {'ts_code': '603986.SH', 'name': '兆易创新'},
        {'ts_code': '600584.SH', 'name': '长电科技'},

        # ==================== 2. 制造业（高端装备/PCB新材料）====================
        {'ts_code': '301377.SZ', 'name': '鼎泰高科'},
        {'ts_code': '301217.SZ', 'name': '铜冠铜箔'},
        {'ts_code': '603256.SH', 'name': '宏和科技'},
        {'ts_code': '688519.SH', 'name': '南亚新材'},
        {'ts_code': '688308.SH', 'name': '欧科亿'},
        {'ts_code': '003036.SZ', 'name': '泰坦股份'},

        # ==================== 3. 银行 ====================
        {'ts_code': '002948.SZ', 'name': '青岛银行'},
        {'ts_code': '601838.SH', 'name': '成都银行'},
        {'ts_code': '002142.SZ', 'name': '宁波银行'},
        {'ts_code': '600919.SH', 'name': '江苏银行'},
        {'ts_code': '601939.SH', 'name': '建设银行'},
        {'ts_code': '601288.SH', 'name': '农业银行'},

        # ==================== 4. 电动汽车/新能源电池 ====================
        {'ts_code': '300750.SZ', 'name': '宁德时代'},
        {'ts_code': '002594.SZ', 'name': '比亚迪'},
        {'ts_code': '300014.SZ', 'name': '亿纬锂能'},
        {'ts_code': '002460.SZ', 'name': '赣锋锂业'},
        {'ts_code': '002466.SZ', 'name': '天齐锂业'},
        {'ts_code': '300124.SZ', 'name': '汇川技术'},

        # ==================== 5. 化工 ====================
        {'ts_code': '600309.SH', 'name': '万华化学'},
        {'ts_code': '600426.SH', 'name': '华鲁恒升'},
        {'ts_code': '002493.SZ', 'name': '荣盛石化'},
        {'ts_code': '600346.SH', 'name': '恒力石化'},
        {'ts_code': '600486.SH', 'name': '扬农化工'},
        {'ts_code': '605589.SH', 'name': '圣泉集团'},

        # ==================== 6. IT/软件/AI应用 ====================
        {'ts_code': '688227.SH', 'name': '品高股份'},
        {'ts_code': '301269.SZ', 'name': '华大九天'},
        {'ts_code': '300339.SZ', 'name': '润和软件'},
        {'ts_code': '300454.SZ', 'name': '深信服'},
        {'ts_code': '601360.SH', 'name': '三六零'},
        {'ts_code': '300666.SZ', 'name': '江丰电子'},

        # ==================== 7. 有色金属/稀土/小金属 ====================
        {'ts_code': '603045.SH', 'name': '福达合金'},
        {'ts_code': '600961.SH', 'name': '株冶集团'},
        {'ts_code': '001337.SZ', 'name': '四川黄金'},
        {'ts_code': '300139.SZ', 'name': '晓程科技'},
        {'ts_code': '600497.SH', 'name': '驰宏锌锗'},
        {'ts_code': '600459.SH', 'name': '贵研铂业'},

        # ==================== 8. 医药生物/创新药 ====================
        {'ts_code': '600276.SH', 'name': '恒瑞医药'},
        {'ts_code': '603259.SH', 'name': '药明康德'},
        {'ts_code': '300122.SZ', 'name': '智飞生物'},
        {'ts_code': '002007.SZ', 'name': '华兰生物'},
        {'ts_code': '300347.SZ', 'name': '泰格医药'},
        {'ts_code': '603392.SH', 'name': '万泰生物'},

        # ==================== 9. 国防军工/商业航天 ====================
        {'ts_code': '600118.SH', 'name': '中国卫星'},
        {'ts_code': '600879.SH', 'name': '航天电子'},
        {'ts_code': '688297.SH', 'name': '中无人机'},
        {'ts_code': '002179.SZ', 'name': '中航光电'},
        {'ts_code': '001270.SZ', 'name': '铖昌科技'},
        {'ts_code': '603678.SH', 'name': '火炬电子'},

        # ==================== 10. 食品饮料/白酒 ====================
        {'ts_code': '600519.SH', 'name': '贵州茅台'},
        {'ts_code': '000858.SZ', 'name': '五粮液'},
        {'ts_code': '600809.SH', 'name': '山西汾酒'},
        {'ts_code': '000568.SZ', 'name': '泸州老窖'},
        {'ts_code': '603369.SH', 'name': '今世缘'},
        {'ts_code': '002304.SZ', 'name': '洋河股份'},

        # ==================== 11. 光伏/储能 ====================
        {'ts_code': '600438.SH', 'name': '通威股份'},
        {'ts_code': '601012.SH', 'name': '隆基绿能'},
        {'ts_code': '300274.SZ', 'name': '阳光电源'},
        {'ts_code': '002459.SZ', 'name': '晶澳科技'},
        {'ts_code': '688411.SH', 'name': '海博思创'},
        {'ts_code': '300693.SZ', 'name': '盛弘股份'},

        # ==================== 12. 电力/公用事业 ====================
        {'ts_code': '600900.SH', 'name': '长江电力'},
        {'ts_code': '601991.SH', 'name': '大唐发电'},
        {'ts_code': '600396.SH', 'name': '华电辽能'},
        {'ts_code': '600795.SH', 'name': '国电电力'},
        {'ts_code': '601985.SH', 'name': '中国核电'},
        {'ts_code': '600023.SH', 'name': '浙能电力'},

        # ==================== 13. 石油石化/能源 ====================
        {'ts_code': '601857.SH', 'name': '中国石油'},
        {'ts_code': '600028.SH', 'name': '中国石化'},
        {'ts_code': '600938.SH', 'name': '中国海油'},
        {'ts_code': '300164.SZ', 'name': '通源石油'},
        {'ts_code': '002207.SZ', 'name': '准油股份'},
        {'ts_code': '300191.SZ', 'name': '潜能恒信'},

        # ==================== 14. 机械设备/机器人 ====================
        {'ts_code': '300124.SZ', 'name': '汇川技术'},
        {'ts_code': '688017.SH', 'name': '绿的谐波'},
        {'ts_code': '300276.SZ', 'name': '三丰智能'},
        {'ts_code': '002008.SZ', 'name': '大族激光'},
        {'ts_code': '300450.SZ', 'name': '先导智能'},
        {'ts_code': '603290.SH', 'name': '斯达半导'},

        # ==================== 15. 消费零售/百货 ====================
        {'ts_code': '600785.SH', 'name': '新华百货'},
        {'ts_code': '601116.SH', 'name': '三江购物'},
        {'ts_code': '600828.SH', 'name': '茂业商业'},
        {'ts_code': '600814.SH', 'name': '杭州解百'},
        {'ts_code': '000419.SZ', 'name': '通程控股'},
        {'ts_code': '600697.SH', 'name': '欧亚集团'},

        # ==================== 16. 家电/消费品 ====================
        {'ts_code': '000651.SZ', 'name': '格力电器'},
        {'ts_code': '000333.SZ', 'name': '美的集团'},
        {'ts_code': '300672.SZ', 'name': '国轩高科'},
        {'ts_code': '002508.SZ', 'name': '老板电器'},
        {'ts_code': '002035.SZ', 'name': '华帝股份'},
        {'ts_code': '688169.SH', 'name': '石头科技'},

        # ==================== 17. 房地产/建筑 ====================
        {'ts_code': '600048.SH', 'name': '保利发展'},
        {'ts_code': '000002.SZ', 'name': '万科A'},
        {'ts_code': '001979.SZ', 'name': '招商蛇口'},
        {'ts_code': '600683.SH', 'name': '京投发展'},
        {'ts_code': '000608.SZ', 'name': '阳光股份'},
        {'ts_code': '601668.SH', 'name': '中国建筑'},

        # ==================== 18. 传媒/游戏 ====================
        {'ts_code': '300418.SZ', 'name': '昆仑万维'},
        {'ts_code': '002555.SZ', 'name': '三七互娱'},
        {'ts_code': '002624.SZ', 'name': '完美世界'},
        {'ts_code': '002602.SZ', 'name': '世纪华通'},
        {'ts_code': '300459.SZ', 'name': '汤姆猫'},
        {'ts_code': '002517.SZ', 'name': '恺英网络'},

        # ==================== 19. 农林牧渔/猪肉 ====================
        {'ts_code': '002714.SZ', 'name': '牧原股份'},
        {'ts_code': '300498.SZ', 'name': '温氏股份'},
        {'ts_code': '000876.SZ', 'name': '新希望'},
        {'ts_code': '002100.SZ', 'name': '天康生物'},
        {'ts_code': '000895.SZ', 'name': '双汇发展'},
        {'ts_code': '605296.SH', 'name': '神农集团'},

        # ==================== 20. 通信/电子元器件 ====================
        {'ts_code': '600183.SH', 'name': '生益科技'},
        {'ts_code': '002916.SZ', 'name': '深南电路'},
        {'ts_code': '300476.SZ', 'name': '胜宏科技'},
        {'ts_code': '002384.SZ', 'name': '东山精密'},
        {'ts_code': '300408.SZ', 'name': '三环集团'},
        {'ts_code': '603228.SH', 'name': '景旺电子'},
    ]

    REFRESH_US_STOCK_LIST = [
        "SPY", "C", "JPM", "AAPL", "NVDA", "GS", "MS", "GE",  # 你原有的代码
        "MSFT", "AVGO", "ADBE", "UNH", "JNJ", "LLY", "PFE", "MRK", "AMZN",
        "TSLA", "MCD", "NFLX", "HD", "GOOGL", "META", "DIS", "CMCSA", "T",
        "CAT", "UPS", "BA", "HON", "PG", "KO", "PEP", "WMT", "COST", "XOM",
        "CVX", "COP", "SLB", "EOG", "AMT", "PLD", "EQIX", "SPG", "O", "NEE",
        "DUK", "SO", "D", "EXC", "LIN", "APD", "FCX", "NEM", "SHW"
    ]

    #US_STOCK_LIST=["SPY", "C", "JPM", "AAPL","NVDA","GS","MS","GE"]
    #US_STOCK_LIST=["C", "JPM", "AAPL", "NVDA", "MSFT"]
    US_STOCK_LIST = [
        "SPY", "C", "JPM", "AAPL", "NVDA", "GS", "MS", "GE",  # 你原有的代码
        "MSFT", "AVGO", "ADBE", "UNH", "JNJ", "LLY", "PFE", "MRK", "AMZN",
        "TSLA", "MCD", "NFLX", "HD", "GOOGL", "META", "DIS", "CMCSA", "T",
        "CAT", "UPS", "BA", "HON", "PG", "KO", "PEP", "WMT", "COST", "XOM",
        "CVX", "COP", "SLB", "EOG", "AMT", "PLD", "EQIX", "SPG", "O", "NEE",
        "DUK", "SO", "D", "EXC", "LIN", "APD", "FCX", "NEM", "SHW"
    ]




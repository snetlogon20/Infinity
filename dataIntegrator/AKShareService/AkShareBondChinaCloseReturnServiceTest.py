from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareBondChinaCloseReturnService import AkShareBondChinaCloseReturnService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

class AkShareBondChinaCloseReturnServiceTest:

    def test1_callAkShareBondChinaCloseReturnService(cls, start_date=None, end_date=None, period="1"):
        """
        测试完整的债券收益率数据ETL流程
        
        Args:
            start_date: 开始日期 (YYYYMMDD)，默认为当前日期前30天
            end_date: 结束日期 (YYYYMMDD)，默认为当前日期
            period: 期限间隔 ('0.1', '0.5', '1')，默认为'1'
        """
        logger.info("callAkShareBondChinaCloseReturnService started...")

        file_path = os.path.join(CommonParameters.outBoundPath, 'akshare_bond_china_close_return.xlsx')

        try:
            akShareService = AkShareBondChinaCloseReturnService()

            # 获取原始数据（从API直接获取）
            dataFrame = akShareService.prepareDataFrame(start_date=start_date, end_date=end_date, period=period)
            
            if dataFrame.empty:
                logger.error("没有获取到任何数据，退出")
                return
            
            # 保存到本地磁盘（可选，用于验证）
            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)
            
            # 从磁盘读取（可选，用于验证）
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)
            
            # 删除ClickHouse中的旧数据（按债券类型删除）
            # 注意：这里可以根据需要选择是否删除旧数据
            # 如果要全量刷新，可以注释掉下面的代码
            bond_types = dataFrame['债券类型'].unique() if '债券类型' in dataFrame.columns else []
            for bond_type in bond_types:
                logger.info(f"正在删除债券类型 '{bond_type}' 的旧数据...")
                akShareService.deleteDateFromClickHouse(bond_type=bond_type)
            
            # 转换数据
            dataFrame = akShareService.transformDataFrame(dataFrame)
            
            # 保存到 ClickHouse
            akShareService.saveDateToClickHouse(dataFrame)
            
            logger.info(f"✅ 成功保存 {len(dataFrame)} 条记录到ClickHouse")

        except Exception as e:
            logger.error('Exception: %s', e)
            raise e

        logger.info("callAkShareBondChinaCloseReturnService ended...")

if __name__ == '__main__':
    akShareBondChinaCloseReturnServiceTest = AkShareBondChinaCloseReturnServiceTest()

    try:
        logger.info("开始处理债券收益率数据...")
        
        # 计算最近30天的日期范围
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - relativedelta(days=30)).strftime("%Y%m%d")
        
        logger.info(f"查询日期范围: {start_date} ~ {end_date}")
        
        # 执行完整的ETL流程
        akShareBondChinaCloseReturnServiceTest.test1_callAkShareBondChinaCloseReturnService(
            start_date=start_date,
            end_date=end_date,
            period="1"  # 可以选择 '0.1', '0.5', 或 '1'
        )
        
        logger.info("债券收益率数据处理完成")
        
    except Exception as e:
        logger.error(f"债券收益率数据处理失败: {e}")
        import traceback
        traceback.print_exc()

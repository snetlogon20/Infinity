from dataIntegrator import CommonLib
import os
import sys
from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator.AKShareService.AkShareBondCbJslService import AkShareBondCbJslService
from dataIntegrator.AKShareService.AkShareJobLogger import AkShareJobLogger
from dataIntegrator.common.FileType import FileType
from dataIntegrator.common.MyTokens import MyTokens

logger = CommonLib.logger


class AkShareBondCbJslServiceTest:

    @classmethod
    def refresh_bond_cb_jsl(cls, cookie=None):
        """拉取集思录可转债实时数据并保存到 ClickHouse

        每次拉取全量当前交易数据，全量刷新

        Args:
            cookie (str, optional): 集思录登录 cookie，不传默认使用 MyTokens.AKSHARE_BOND_CB_JSL_COOKIE
        """
        logger.info(f"\n{'=' * 60}")
        logger.info("集思录可转债实时数据刷新任务开始")
        logger.info(f"{'=' * 60}")

        file_path = os.path.join(CommonParameters.outBoundPath, 'akshare_bond_cb_jsl.xlsx')
        job_logger = AkShareJobLogger()

        try:
            # 记录任务开始
            job_logger.start_job('AkShareBondCbJslService', {
                'cookie_used': bool(cookie or MyTokens.AKSHARE_BOND_CB_JSL_COOKIE),
            })

            akShareService = AkShareBondCbJslService()

            # Step 1: 获取原始数据
            dataFrame = akShareService.prepareDataFrame(cookie=cookie)

            if dataFrame.empty:
                logger.warning("没有获取到任何可转债数据，任务终止")
                job_logger.end_job_success(records_processed=0)
                return

            # Step 2: 保存原始数据到 Excel (用于调试/审计)
            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)
            logger.info(f"原始数据已保存到 Excel: {file_path}")

            # Step 3: 从 Excel 重新读取 (对齐标准流程，确保数据一致性)
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)

            # Step 4: 全量刷新 - 删除 ClickHouse 中所有旧数据
            akShareService.deleteDateFromClickHouse()

            # Step 5: 数据转换
            transformed_dataFrame = akShareService.transformDataFrame(dataFrame)

            # Step 6: 保存到 ClickHouse
            akShareService.saveDateToClickHouse(transformed_dataFrame)

            # 记录任务成功
            records_processed = len(transformed_dataFrame) if transformed_dataFrame is not None else 0
            job_logger.end_job_success(records_processed=records_processed)
            logger.info(f"✅ 集思录可转债实时数据刷新完成！共处理 {records_processed} 条记录")

        except Exception as e:
            logger.error(f"❌ 集思录可转债实时数据刷新失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

        logger.info(f"{'=' * 60}\n")


if __name__ == '__main__':
    akShareBondCbJslServiceTest = AkShareBondCbJslServiceTest()
    akShareBondCbJslServiceTest.refresh_bond_cb_jsl()

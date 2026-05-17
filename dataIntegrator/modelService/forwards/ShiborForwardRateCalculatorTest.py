"""
SHIBOR 远期利率计算器测试脚本
"""

import os
import sys

from dataIntegrator.common.CommonDataParameters import CommonDataParameters

from dataIntegrator.modelService.forwards.ShiborForwardRateCalculator import ShiborForwardRateCalculator
from dataIntegrator import CommonLib, CommonParameters

logger = CommonLib.logger
commonLib = CommonLib()


def test_full_workflow():
    """测试完整工作流程"""
    logger.info("\n" + "="*80)
    logger.info("SHIBOR 远期利率计算器")
    logger.info("="*80)

    calculator = ShiborForwardRateCalculator()

    # 获取最近1年数据
    start_date = CommonDataParameters.get_start_date(days=360)
    end_date = CommonParameters.today

    try:
        result_df = calculator.run(
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"\n✅ 执行成功!")
        logger.info(f"输出目录: {calculator.output_dir}")
        logger.info(f"\n输出文件:")
        for file in os.listdir(calculator.output_dir):
            file_path = os.path.join(calculator.output_dir, file)
            file_size = os.path.getsize(file_path)
            size_str = f"{file_size / 1024:.1f} KB"
            
            # 根据文件类型添加图标
            if file.endswith('.pdf'):
                icon = '📄'
            elif file.endswith('.png'):
                icon = '📊'
            elif file.endswith('.csv'):
                icon = '📋'
            else:
                icon = ''
            
            logger.info(f"  {icon} {file} ({size_str})")

        return True
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = test_full_workflow()
    sys.exit(0 if success else 1)

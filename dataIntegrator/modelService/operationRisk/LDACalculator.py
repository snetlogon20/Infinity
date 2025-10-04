import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

class LDACalculator:
    def calculate_operational_risk(self, freq_dist, sev_dist, confidence_level=0.95):
        """
        计算操作风险的预期损失和非预期损失

        参数:
        freq_dist: dict, 频率分布 {'probability': array, 'frequency': array}
        sev_dist: dict, 严重程度分布 {'probability': array, 'severity': array}
        confidence_level: float, 置信水平

        返回:
        results: dict, 包含所有计算结果
        """

        # 提取数据
        freq_probs = freq_dist['probability']
        freq_values = freq_dist['frequency']
        sev_probs = sev_dist['probability']
        sev_values = sev_dist['severity']

        # 1. 计算频率分布期望和严重程度分布期望
        freq_expectation = np.sum(freq_probs * freq_values)
        sev_expectation = np.sum(sev_probs * sev_values)

        print(f"频率分布期望 E[N] = {freq_expectation:.1f}")
        print(f"严重程度分布期望 E[X] = ${sev_expectation:,.2f}")

        # 2. 计算预期损失
        expected_loss = freq_expectation * sev_expectation
        print(f"预期损失 E[S] = ${expected_loss:,.2f}")

        # 3. 生成详细的损失分布表 (TABLE 25.3)
        loss_distribution = []

        # N=0 的情况
        loss_distribution.append({
            'Number_of_Losses': 0,
            'First_Loss': 0,
            'Second_Loss': 0,
            'Total_Loss': 0,
            'Probability': freq_probs[0]  # P(N=0) = 0.6
        })

        # N=1 的情况
        for i, sev in enumerate(sev_values):
            loss_distribution.append({
                'Number_of_Losses': 1,
                'First_Loss': sev,
                'Second_Loss': 0,
                'Total_Loss': sev,
                'Probability': freq_probs[1] * sev_probs[i]  # P(N=1) * P(X=sev)
            })

        # N=2 的情况 - 考虑所有组合
        for i in range(len(sev_values)):
            for j in range(len(sev_values)):
                sev1 = sev_values[i]
                sev2 = sev_values[j]
                total_loss = sev1 + sev2
                prob = freq_probs[2] * sev_probs[i] * sev_probs[j]  # P(N=2) * P(X1) * P(X2)

                loss_distribution.append({
                    'Number_of_Losses': 2,
                    'First_Loss': sev1,
                    'Second_Loss': sev2,
                    'Total_Loss': total_loss,
                    'Probability': prob
                })

        # 转换为DataFrame
        loss_df = pd.DataFrame(loss_distribution)

        # 4. 合并相同总损失的概率（聚合损失分布）
        aggregated_loss = loss_df.groupby('Total_Loss')['Probability'].sum().reset_index()
        aggregated_loss = aggregated_loss.sort_values('Total_Loss')
        aggregated_loss['Cumulative_Probability'] = aggregated_loss['Probability'].cumsum()

        # 5. 计算VaR和非预期损失
        # 找到最小的损失值使得累积概率 ≥ 置信水平
        var_value = aggregated_loss[aggregated_loss['Cumulative_Probability'] >= confidence_level].iloc[0]['Total_Loss']
        unexpected_loss = var_value - expected_loss

        print(f"\n在{confidence_level * 100}%置信水平下:")
        print(f"VaR = ${var_value:,.2f}")
        print(f"非预期损失 = ${unexpected_loss:,.2f}")

        # 6. 准备绘图数据
        plot_data = {
            'frequency': {
                'values': freq_values,
                'probabilities': freq_probs,
                'expectation': freq_expectation
            },
            'severity': {
                'values': sev_values,
                'probabilities': sev_probs,
                'expectation': sev_expectation
            },
            'loss': {
                'losses': aggregated_loss['Total_Loss'].values,
                'probabilities': aggregated_loss['Probability'].values,
                'cumulative_probs': aggregated_loss['Cumulative_Probability'].values,
                'expected_loss': expected_loss,
                'var': var_value,
                'unexpected_loss': unexpected_loss
            }
        }

        return {
            'frequency_expectation': freq_expectation,
            'severity_expectation': sev_expectation,
            'expected_loss': expected_loss,
            'var': var_value,
            'unexpected_loss': unexpected_loss,
            'loss_distribution_tabulation': loss_df,
            'sorted_loss_distribution': aggregated_loss,
            'plot_data': plot_data
        }

    def output_results(self, results, confidence_level):
        # 显示详细的损失分布表
        detailed_df = results['loss_distribution_tabulation'].copy()
        detailed_df['Probability'] = detailed_df['Probability'].round(4)
        detailed_df['First_Loss'] = detailed_df['First_Loss'].apply(lambda x: f"${x:,.0f}")
        detailed_df['Second_Loss'] = detailed_df['Second_Loss'].apply(lambda x: f"${x:,.0f}")
        detailed_df['Total_Loss'] = detailed_df['Total_Loss'].apply(lambda x: f"${x:,.0f}")

        print(detailed_df.to_string(index=False))

        print("\n" + "=" * 60)
        print("聚合后的损失分布:")
        print("=" * 60)

        # 显示聚合后的损失分布
        aggregated_df = results['sorted_loss_distribution'].copy()
        aggregated_df['Probability'] = aggregated_df['Probability'].round(4)
        aggregated_df['Cumulative_Probability'] = aggregated_df['Cumulative_Probability'].round(4)
        aggregated_df['Total_Loss'] = aggregated_df['Total_Loss'].apply(lambda x: f"${x:,.0f}")

        print(aggregated_df.to_string(index=False))

        # 创建图表
        print("\n生成综合图表...")
        fig = self.create_comprehensive_plots(results, confidence_level)

        # 保存结果到Excel文件
        try:
            with pd.ExcelWriter(
                    rf'D:\workspace_python\infinity\dataIntegrator\data\outbound\operational_risk_analysis_results.xlsx') as writer:
                # 详细损失分布表
                detailed_df.to_excel(writer, sheet_name='Detailed_Loss_Distribution', index=False)

                # 聚合损失分布
                aggregated_df.to_excel(writer, sheet_name='Aggregated_Loss_Distribution', index=False)

                # 分析结果汇总
                summary_data = {
                    '指标': [
                        '频率分布期望 E[N]',
                        '严重程度分布期望 E[X]',
                        '预期损失 E[S]',
                        f'VaR ({confidence_level * 100}%置信水平)',
                        f'非预期损失 ({confidence_level * 100}%置信水平)'
                    ],
                    '数值': [
                        results['frequency_expectation'],
                        results['severity_expectation'],
                        results['expected_loss'],
                        results['var'],
                        results['unexpected_loss']
                    ],
                    '单位': ['次', '美元', '美元', '美元', '美元']
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Analysis_Summary', index=False)

            print("分析完成！结果已保存到 'operational_risk_analysis_results.xlsx'")

        except Exception as e:
            print(f"保存Excel文件时出错: {e}")

    def create_comprehensive_plots(self, results, confidence_level=0.95):
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号

        """
        创建综合图表，包含三个子图
        """
        # 创建图形和网格布局
        # 创建图形，调整大小和布局
        fig = plt.figure(figsize=(14, 10))
        # 使用GridSpec创建更紧凑的布局
        gs = GridSpec(2, 2, figure=fig, height_ratios=[1, 1.2], hspace=0.3, wspace=0.3)

        # 获取数据
        freq_data = results['plot_data']['frequency']
        sev_data = results['plot_data']['severity']
        loss_data = results['plot_data']['loss']

        # 1. 频率分布图 (左上)
        ax1 = fig.add_subplot(gs[0, 0])
        bars1 = ax1.bar(freq_data['values'], freq_data['probabilities'],
                        color='lightblue', alpha=0.8, edgecolor='navy', linewidth=1.5)
        ax1.set_xlabel('每年损失次数', fontsize=12, fontweight='bold')
        ax1.set_ylabel('概率', fontsize=12, fontweight='bold')
        ax1.set_title('损失频率分布\n(Number of Losses per Year)', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_xticks(freq_data['values'])

        # 在柱子上添加概率标签
        for bar, prob in zip(bars1, freq_data['probabilities']):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2., height + 0.01,
                     f'{prob:.1f}', ha='center', va='bottom', fontweight='bold')

        # 标记期望值
        ax1.axvline(x=freq_data['expectation'], color='red', linestyle='--', linewidth=2,
                    label=f'期望值 E[N] = {freq_data["expectation"]:.1f}')
        ax1.legend()

        # 2. 严重程度分布图 (右上)
        ax2 = fig.add_subplot(gs[0, 1])
        sev_labels = [f'${x / 1000:.0f}K' for x in sev_data['values']]
        bars2 = ax2.bar(sev_labels, sev_data['probabilities'],
                        color='lightcoral', alpha=0.8, edgecolor='darkred', linewidth=1.5)
        ax2.set_xlabel('单次损失金额', fontsize=12, fontweight='bold')
        ax2.set_ylabel('概率', fontsize=12, fontweight='bold')
        ax2.set_title('损失严重程度分布\n(Loss Size Distribution)', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3, linestyle='--')

        # 在柱子上添加概率标签
        for bar, prob in zip(bars2, sev_data['probabilities']):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2., height + 0.01,
                     f'{prob:.1f}', ha='center', va='bottom', fontweight='bold')

        # 标记期望值
        ax2.axhline(y=0.5, xmin=0, xmax=1, color='red', linestyle='--', linewidth=2,
                    label=f'期望值 E[X] = ${sev_data["expectation"]:,.0f}')
        ax2.legend()

        # 3. 年度损失分布图 (下方大图)
        ax3 = fig.add_subplot(gs[1, :])

        # 创建损失分布的柱状图（转换为千美元显示）
        losses_k = loss_data['losses'] / 1000
        probabilities = loss_data['probabilities']

        # 使用更细的柱子来更好地显示分布
        bars3 = ax3.bar(losses_k, probabilities,
                        color='lightgreen', alpha=0.7, edgecolor='darkgreen',
                        width=2, label='损失概率')

        ax3.set_xlabel('年度总损失 (千美元)', fontsize=12, fontweight='bold')
        ax3.set_ylabel('概率', fontsize=12, fontweight='bold')
        ax3.set_title('年度损失分布\n(Loss per Year Distribution)', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3, linestyle='--')

        # 标记关键值
        expected_loss_k = loss_data['expected_loss'] / 1000
        var_k = loss_data['var'] / 1000

        # 预期损失线
        ax3.axvline(x=expected_loss_k, color='blue', linestyle='-',
                    linewidth=3, label=f'预期损失 (${loss_data["expected_loss"]:,.0f})')

        # VaR线
        ax3.axvline(x=var_k, color='red', linestyle='-',
                    linewidth=3, label=f'VaR ({confidence_level * 100}%置信水平) = ${loss_data["var"]:,.0f}')

        # 非预期损失区域
        ax3.axvspan(expected_loss_k, var_k, alpha=0.3, color='orange',
                    label=f'非预期损失 = ${loss_data["unexpected_loss"]:,.0f}')

        ax3.legend(fontsize=10)

        # 添加文本注释
        annotation_text = f"""分析结果:
        • 频率分布期望 E[N] = {results['frequency_expectation']:.1f}
        • 严重程度分布期望 E[X] = ${results['severity_expectation']:,.0f}
        • 预期损失 E[S] = ${results['expected_loss']:,.0f}
        • {confidence_level * 100}% VaR = ${results['var']:,.0f}
        • 非预期损失 = ${results['unexpected_loss']:,.0f}"""

        ax3.text(0.02, 0.98, annotation_text, transform=ax3.transAxes,
                 fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.tight_layout()
        plt.show()

        return fig



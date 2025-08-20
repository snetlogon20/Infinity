# dataIntegrator - snetlogon20

#### 介绍

**1. Data Integrater** 
是一个金融数据分析平台。内置数据抽取平台，量化金融分析、机器学习、数据可视化及LLM 模型。
- **功能一**：自动获取最新金融市场数据
- **功能二**：提供各类量化模块及数量分析
- **功能三**：提供可视化数据展现
- **功能四**：在数据聚合并计算关键金融指标的基础上，提供大预言分析及金融顾问建议服务。

**2. Infinity Grid**
作为DataIntegrator中的一个模块，Infinity Grid是一个开源的大语言模型Agent，主要功能是对金融量化工具提供大语言模型的支持。Infinity 可以作为一个插件对传统金融行业提供了对包括了对固定收益、股票、 衍生品等各类金融模型的量化计算。

- **功能一**：人类语言翻译为SQL查询并完成量化分析
- **功能二**：金融产品量化分析
- **功能三**：人类语言翻译为需求并生成代码

#### 软件架构
软件架构说明
1. data Service 抽取数据服务
2. modelService 金融模型服务，包括
   - a. 债券分析
   - b. 衍生品分析
   - c. 各类分布模型
   - d. 远期
   - e. 期权
   - f. 蒙特卡洛模拟
   - g. 各类统计基础模型
3. LLMSupport 大语言模型服务
   - a. AI 模型工厂
   - b. RAG 服务
   - c. Chroma 向量服务
4. plotService 绘图服务
5. StreamLit 可视化服务
6. TuShareService Tushare 金融数据获取服务
7. CICD 自动安装装脚本


#### 安装教程
1. Python 3.12
2. ClickHouse

#### 使用说明
详见 https://gitee.com/snetlogon20/infinity/blob/master/dataIntegrator/notebook/readme/Infinity%20Grid(CN).pdf


#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request


#### 特技


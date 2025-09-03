# DataIntegrator - snetlogon20

#### Introduction

**1. Data Integrator**  
A financial data analytics platform with built-in data extraction, quantitative financial analysis, machine learning, data visualization, and LLM capabilities.  
- **Feature 1**: Automatically fetch latest financial market data  
- **Feature 2**: Provide various quantitative modules for financial engineering and financial risk management.  
- **Feature 3**: Offer data visualization capabilities  
- **Feature 4**: Deliver predictive analytics and financial advisory services based on aggregated data and key financial indicators  

**2. Infinity Grid**  
As a module within DataIntegrator, Infinity Grid is an open-source large language model (LLM) Agent that provides LLM support for quantitative financial tools. It serves as a plugin offering quantitative calculations for various financial models including fixed income, equities, and derivatives in traditional finance.  

- **Feature 1**: Translate natural language to SQL queries for quantitative analysis  
- **Feature 2**: Quantitative analysis of financial products  
- **Feature 3**: Convert natural language requirements into executable code  

#### System Architecture  
1. **dataService**: Data extraction service  
2. **modelService**: Financial modeling services including:  
   - a. Bond analysis  
   - b. Derivatives analysis  
   - c. Various distribution models  
   - d. Forwards  
   - e. Options  
   - f. Monte Carlo simulation  
   - g. Fundamental statistical models  
3. **LLMSupport**: Large Language Model services  
   - a. AI model factory  
   - b. RAG services  
   - c. Chroma vector services  
4. **plotService**: Visualization service  
5. **StreamLit**: Dashboard service  
6. **TuShareService**: Tushare financial data API service  
7. **CI/CD**: Automated deployment scripts  

#### Installation Guide  
1. Python 3.12  
2. ClickHouse  

#### User Manual  
   - See: https://gitee.com/snetlogon20/infinity/blob/master/dataIntegrator/notebook/readme/Infinity%20Grid(EN).pdf  

#### Contribution Guidelines  
1. Fork this repository  
2. Create a new Feat_xxx branch  
3. Submit your code  
4. Create a Pull Request  

#### Technical Highlights  
(To be specified)
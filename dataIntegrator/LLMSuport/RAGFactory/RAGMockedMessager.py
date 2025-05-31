import os

class RAGMockedMessager():
    # txt2uml
    txt2uml_MOCKED_AI_ANSWER = """{
            "create_table_sql_statement": [
              {
              "table_name": "Core_LC_Master_Data",
              "create_table_sql": "CREATE TABLE Core_LC_Master_Data (LC_ID String, Applicant_ID String, Beneficiary_ID String, Issuing_Bank_ID String, Advising_Bank_ID String, LC_Type String, LC_Currency String, LC_Amount Decimal(15, 2), Issue_Date Date, Expiry_Date Date, Latest_Shipment_Date Date, LC_Description String)"
              },
              {
              "table_name": "Documentary_Compliance",
              "create_table_sql": "CREATE TABLE Documentary_Compliance (Document_ID String, LC_ID_Ref String, Document_Type String, Document_Status String, Submission_Date Date, Review_Date Date, Discrepancy_Details String, Document_Reference_Number String)"
              },
              {
              "table_name": "Transaction_Tracking",
              "create_table_sql": "CREATE TABLE Transaction_Tracking (Transaction_ID String, LC_ID_Ref String, Transaction_Date Date, Transaction_Type String, Party_Involved String, Transaction_Status String, Previous_Transaction_ID String)"
              }
            ],
            "create_table_uml_statement": "@startuml
                entity Core_LC_Master_Data {
                    LC_ID : String,
                    Applicant_ID : String,
                    Beneficiary_ID : String,
                    Issuing_Bank_ID : String,
                    Advising_Bank_ID : String,
                    LC_Type : String,
                    LC_Currency : String,
                    LC_Amount : Decimal(15, 2),
                    Issue_Date : Date,
                    Expiry_Date : Date,
                    Latest_Shipment_Date : Date,
                    LC_Description : String
                }
                entity Documentary_Compliance {
                    Document_ID : String,
                    LC_ID_Ref : String,
                    Document_Type : String,
                    Document_Status : String,
                    Submission_Date : Date,
                    Review_Date : Date,
                    Discrepancy_Details : String,
                    Document_Reference_Number : String
                }
                entity Transaction_Tracking {
                    Transaction_ID : String,
                    LC_ID_Ref : String,
                    Transaction_Date : Date,
                    Transaction_Type : String,
                    Party_Involved : String,
                    Transaction_Status : String,
                    Previous_Transaction_ID : String
                }
                Core_LC_Master_Data ||--o{ Documentary_Compliance : contains
                Core_LC_Master_Data ||--o{ Transaction_Tracking : contains
                @enduml",
            "explanation_in_Mandarin": "该JSON包含创建三个表的SQL语句和对应的Plant UML图。SQL语句使用Clickhouse语法，每个表的字段根据提供的业务需求定义。UML图中展示了三个实体及其关系，其中Core_LC_Master_Data与另外两个表是一对多的关系。",
            "explanation_in_English": "This JSON contains the SQL statements to create three tables and the corresponding Plant UML diagram. The SQL statements use Clickhouse syntax, and the fields of each table are defined according to the provided business requirements. The UML diagram shows the three entities and their relationships, where Core_LC_Master_Data has a one-to-many relationship with the other two tables.",
            "feedback":"无"
                }"""

    # UML2schema
    UML2schema_MOCKED_AI_ANSWER = """{
    "table_definitions": [
        {
            "table_name": "Core_LC_Master_Data",
            "table_definition": "核心信用证主数据，Core LC Master Data",
            "primary_key": "LC_ID",
            "table_alias": "Core_LC_Master_Data"
        },
        {
            "table_name": "Documentary_Compliance",
            "table_definition": "单证合规性，Documentary Compliance",
            "primary_key": "Document_ID",
            "table_alias": "Documentary_Compliance"
        },
        {
            "table_name": "Transaction_Tracking",
            "table_definition": "交易跟踪，Transaction Tracking",
            "primary_key": "Transaction_ID",
            "table_alias": "Transaction_Tracking"
        }
    ],
    "table_schema": {
        "Core_LC_Master_Data": {
            "columns": {
                "LC_ID": "信用证编号，Letter of Credit Identification（字符串类型）, column alias as:LC_ID",
                "Applicant_ID": "申请人编号，Applicant Identification（字符串类型）, column alias as:Applicant_ID",
                "Beneficiary_ID": "受益人编号，Beneficiary Identification（字符串类型）, column alias as:Beneficiary_ID",
                "Issuing_Bank_ID": "开证行编号，Issuing Bank Identification（字符串类型）, column alias as:Issuing_Bank_ID",
                "Advising_Bank_ID": "通知行编号，Advising Bank Identification（字符串类型）, column alias as:Advising_Bank_ID",
                "LC_Type": "信用证类型，Letter of Credit Type（字符串类型）, column alias as:LC_Type",
                "LC_Currency": "信用证货币，Letter of Credit Currency（字符串类型）, column alias as:LC_Currency",
                "LC_Amount": "信用证金额，Letter of Credit Amount（十进制类型）, column alias as:LC_Amount",
                "Issue_Date": "开证日期，LC Issue Date（日期类型）, column alias as:Issue_Date",
                "Expiry_Date": "到期日期，LC Expiry Date（日期类型）, column alias as:Expiry_Date",
                "Latest_Shipment_Date": "最迟装运日期，Latest Shipment Date（日期类型）, column alias as:Latest_Shipment_Date",
                "LC_Description": "信用证描述，Letter of Credit Description（字符串类型）, column alias as:LC_Description"
            }
        },
        "Documentary_Compliance": {
            "columns": {
                "Document_ID": "单证编号，Document Identification（字符串类型）, column alias as:Document_ID",
                "LC_ID_Ref": "信用证编号引用，Letter of Credit Identification Reference（字符串类型）, column alias as:LC_ID_Ref",
                "Document_Type": "单证类型，Document Type（字符串类型）, column alias as:Document_Type",
                "Document_Status": "单证状态，Document Status（字符串类型）, column alias as:Document_Status",
                "Submission_Date": "提交日期，Document Submission Date（日期类型）, column alias as:Submission_Date",
                "Review_Date": "审核日期，Document Review Date（日期类型）, column alias as:Review_Date",
                "Discrepancy_Details": "差异详情，Discrepancy Details（字符串类型）, column alias as:Discrepancy_Details",
                "Document_Reference_Number": "单证参考编号，Document Reference Number（字符串类型）, column alias as:Document_Reference_Number"
            }
        },
        "Transaction_Tracking": {
            "columns": {
                "Transaction_ID": "交易编号，Transaction Identification（字符串类型）, column alias as:Transaction_ID",
                "LC_ID_Ref": "信用证编号引用，Letter of Credit Identification Reference（字符串类型）, column alias as:LC_ID_Ref",
                "Transaction_Date": "交易日期，Transaction Date（日期类型）, column alias as:Transaction_Date",
                "Transaction_Type": "交易类型，Transaction Type（字符串类型）, column alias as:Transaction_Type",
                "Party_Involved": "参与方，Party Involved（字符串类型）, column alias as:Party_Involved",
                "Transaction_Status": "交易状态，Transaction Status（字符串类型）, column alias as:Transaction_Status",
                "Previous_Transaction_ID": "前一交易编号，Previous Transaction Identification（字符串类型）, column alias as:Previous_Transaction_ID"
            }
        }
    }
    }"""

    # UML2testdata
    UML2testdata_MOCKED_AI_ANSWER = """{
    "delete_sql": [
        "ALTER TABLE Core_LC_Master_Data DELETE WHERE 1=1;",
        "ALTER TABLE Documentary_Compliance DELETE WHERE 1=1;",
        "ALTER TABLE Transaction_Tracking DELETE WHERE 1=1;"
    ],
    "insert_sql": [
        "INSERT INTO Core_LC_Master_Data (LC_ID, Applicant_ID, Beneficiary_ID, Issuing_Bank_ID, Advising_Bank_ID, LC_Type, LC_Currency, LC_Amount, Issue_Date, Expiry_Date, Latest_Shipment_Date, LC_Description) VALUES ('LC0001', 'APP001', 'BEN001', 'ISB001', '', 'Irrevocable', 'USD', 20000.00, '2024-01-01', '2024-04-01', '2024-03-15', 'Electronics Import'), ('LC0002', 'APP002', 'BEN002', 'ISB002', '', 'Irrevocable', 'CNY', 30000.00, '2024-01-02', '2024-04-02', '2024-03-16', 'Textiles Export'), ('LC0003', 'APP003', 'BEN003', 'ISB003', '', 'Irrevocable', 'JPY', 15000.00, '2024-01-03', '2024-04-03', '2024-03-17', 'Automotive Parts'), ('LC0004', 'APP004', 'BEN004', 'ISB004', '', 'Irrevocable', 'USD', 25000.00, '2024-01-04', '2024-04-04', '2024-03-18', 'Furniture'), ('LC0005', 'APP005', 'BEN005', 'ISB005', '', 'Irrevocable', 'CNY', 10000.00, '2024-01-05', '2024-04-05', '2024-03-19', 'Toys');",
        "INSERT INTO Documentary_Compliance (Document_ID, LC_ID_Ref, Document_Type, Document_Status, Submission_Date, Review_Date, Discrepancy_Details, Document_Reference_Number) VALUES ('DOC0001', 'LC0001', 'Bill of Lading', 'Pending Review', '2024-01-10', '', '', 'BL123'), ('DOC0002', 'LC0001', 'Commercial Invoice', 'Compliant', '2024-01-11', '2024-01-12', '', 'INV456'), ('DOC0003', 'LC0002', 'Packing List', 'Discrepant', '2024-01-15', '2024-01-16', 'Missing items', 'PK789'), ('DOC0004', 'LC0003', 'Certificate of Origin', 'Pending Review', '2024-01-20', '', '', 'COO321'), ('DOC0005', 'LC0004', 'Inspection Certificate', 'Compliant', '2024-01-25', '2024-01-26', '', 'IC654');",
        "INSERT INTO Transaction_Tracking (Transaction_ID, LC_ID_Ref, Transaction_Date, Transaction_Type, Party_Involved, Transaction_Status, Previous_Transaction_ID) VALUES ('TRANS001', 'LC0001', '2024-01-10', 'LC Issued', 'Issuing Bank', 'Completed', ''), ('TRANS002', 'LC0001', '2024-01-15', 'Documents Presented', 'Beneficiary', 'In Progress', 'TRANS001'), ('TRANS003', 'LC0002', '2024-01-12', 'LC Issued', 'Issuing Bank', 'Completed', ''), ('TRANS004', 'LC0003', '2024-01-18', 'LC Issued', 'Issuing Bank', 'Completed', ''), ('TRANS005', 'LC0004', '2024-01-21', 'LC Issued', 'Issuing Bank', 'Completed', '');"
    ],
    "update_sql": [
        "ALTER TABLE Core_LC_Master_Data UPDATE LC_Amount = 22000.00, Issue_Date = '2024-01-06' WHERE LC_ID = 'LC0001';",
        "ALTER TABLE Core_LC_Master_Data UPDATE LC_Type = 'Usance', Expiry_Date = '2024-05-01' WHERE LC_ID = 'LC0002';",
        "ALTER TABLE Core_LC_Master_Data UPDATE Beneficiary_ID = 'BEN999', LC_Description = 'Updated Description' WHERE LC_ID = 'LC0003';",
        "ALTER TABLE Core_LC_Master_Data UPDATE Applicant_ID = 'APP999', Latest_Shipment_Date = '2024-03-25' WHERE LC_ID = 'LC0004';",
        "ALTER TABLE Core_LC_Master_Data UPDATE Issuing_Bank_ID = 'ISB999', Advising_Bank_ID = 'ADV999' WHERE LC_ID = 'LC0005';",
        "ALTER TABLE Documentary_Compliance UPDATE Document_Status = 'Compliant', Review_Date = '2024-01-13' WHERE Document_ID = 'DOC0001';",
        "ALTER TABLE Documentary_Compliance UPDATE Discrepancy_Details = 'Resolved discrepancy' WHERE Document_ID = 'DOC0003';",
        "ALTER TABLE Documentary_Compliance UPDATE Submission_Date = '2024-01-18' WHERE Document_ID = 'DOC0004';",
        "ALTER TABLE Transaction_Tracking UPDATE Transaction_Status = 'Completed' WHERE Transaction_ID = 'TRANS002';",
        "ALTER TABLE Transaction_Tracking UPDATE Party_Involved = 'Negotiating Bank' WHERE Transaction_ID = 'TRANS005';"
    ]
    }"""


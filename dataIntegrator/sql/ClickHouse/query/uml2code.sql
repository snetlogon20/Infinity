ALTER TABLE Core_LC_Master_Data DELETE WHERE 1=1;
ALTER TABLE Documentary_Compliance DELETE WHERE 1=1;
ALTER TABLE Transaction_Tracking DELETE WHERE 1=1;


CREATE TABLE Core_LC_Master_Data (LC_ID String,
Applicant_ID String,
Beneficiary_ID String,
Issuing_Bank_ID String,
Advising_Bank_ID String,
LC_Type String,
LC_Currency String,
LC_Amount Decimal(15,2),
Issue_Date Date,
Expiry_Date Date,
Latest_Shipment_Date Date,
LC_Description String)
ENGINE=SummingMergeTree(Applicant_ID)
order by (Applicant_ID)
SETTINGS index_granularity = 8192

select * from Core_LC_Master_Data
INSERT INTO Core_LC_Master_Data (LC_ID, Applicant_ID, Beneficiary_ID, Issuing_Bank_ID, Advising_Bank_ID, LC_Type, LC_Currency, LC_Amount, Issue_Date, Expiry_Date, Latest_Shipment_Date, LC_Description) VALUES ('LC0001', 'APP001', 'BEN001', 'ISB001', '', 'Irrevocable', 'USD', 20000.00, '2024-01-01', '2024-04-01', '2024-03-15', 'Electronics Import'), ('LC0002', 'APP002', 'BEN002', 'ISB002', '', 'Irrevocable', 'CNY', 30000.00, '2024-01-02', '2024-04-02', '2024-03-16', 'Textiles Export'), ('LC0003', 'APP003', 'BEN003', 'ISB003', '', 'Irrevocable', 'JPY', 15000.00, '2024-01-03', '2024-04-03', '2024-03-17', 'Automotive Parts'), ('LC0004', 'APP004', 'BEN004', 'ISB004', '', 'Irrevocable', 'USD', 25000.00, '2024-01-04', '2024-04-04', '2024-03-18', 'Furniture'), ('LC0005', 'APP005', 'BEN005', 'ISB005', '', 'Irrevocable', 'CNY', 10000.00, '2024-01-05', '2024-04-05', '2024-03-19', 'Toys');

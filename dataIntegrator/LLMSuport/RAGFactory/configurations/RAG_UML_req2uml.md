Trade Finance System Business Tables Requirement



Abstract



Define business tables for trade finance system across 5 data domains.


Section 1: The data model of LC business



### Snowflake Model Data Domains&#xA;



*   **Core Domain**: Holds fundamental data for Letters of Credit.


*   **Compliance Domain**: Manages document compliance checks.


*   **Transaction Domain**: Tracks trade transaction activities.


*   **Integration Domain**: Handles SWIFT message integration.


*   **Accounting Domain**: Records financial accounting data.




| No&#xA; | TableName&#xA;                                              | TableDescription&#xA;                                                              |
| ------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 1&#xA;  | infinity\_core\_domain\_lc\_master\_mas&#xA;                | Master data for Letters of Credit, including lifecycle and financial details.&#xA; |
| 2&#xA;  | infinity\_compliance\_domain\_doc\_compliance\_mas&#xA;     | Data related to documentary compliance verification for LCs.&#xA;                  |
| 3&#xA;  | infinity\_transaction\_domain\_trans\_tracking\_mas&#xA;    | Tracks the lifecycle of trade transactions.&#xA;                                   |
| 4&#xA;  | infinity\_integration\_domain\_swift\_integration\_mas&#xA; | Stores data for SWIFT message integration in trade finance.&#xA;                   |
| 5&#xA;  | infinity\_accounting\_domain\_fin\_accounting\_mas&#xA;     | Records financial accounting entries for trade transactions.&#xA;                  |

Section 2: The detail table information



### Table Name: infinity\_core\_domain\_lc\_master\_mas&#xA;



| No&#xA; | ShortName&#xA;           | LongName&#xA;         | Description&#xA;                                        | DataType&#xA; | Length&#xA; | Mandatory&#xA; | DefaultValue&#xA;  | ValidationRules&#xA;                                                                     | StatusSequential&#xA;                                                                                  |
| ------- | ------------------------ | --------------------- | ------------------------------------------------------- | ------------- | ----------- | -------------- | ------------------ | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 1&#xA;  | lc\_id&#xA;              | LCIdentifier&#xA;     | Unique identifier for a Letter of Credit&#xA;           | VARCHAR&#xA;  | 20&#xA;     | Yes&#xA;       | Auto-generate&#xA; | Unique&#xA;                                                                              | 00 request→01 open→02 issue→03 advice→04 negotiated→05 redump→06 closed00/01/03/04/05→07 rejected&#xA; |
| 2&#xA;  | applicant\_name&#xA;     | ApplicantName&#xA;    | Name of the LC applicant&#xA;                           | VARCHAR&#xA;  | 100&#xA;    | Yes&#xA;       | ""&#xA;            | Valid legal entity name&#xA;                                                             | N/A&#xA;                                                                                               |
| 3&#xA;  | beneficiary\_name&#xA;   | BeneficiaryName&#xA;  | Name of the LC beneficiary&#xA;                         | VARCHAR&#xA;  | 100&#xA;    | Yes&#xA;       | ""&#xA;            | Valid legal entity name&#xA;                                                             | N/A&#xA;                                                                                               |
| 4&#xA;  | issuing\_bank\_code&#xA; | IssuingBankCode&#xA;  | SWIFT/BIC code of the issuing bank&#xA;                 | VARCHAR&#xA;  | 11&#xA;     | Yes&#xA;       | ""&#xA;            | Valid SWIFT/BIC code&#xA;                                                                | N/A&#xA;                                                                                               |
| 5&#xA;  | lc\_amount&#xA;          | LCAmount&#xA;         | Principal amount of the LC&#xA;                         | DECIMAL&#xA;  | 18,2&#xA;   | Yes&#xA;       | 0.00&#xA;          | >0&#xA;                                                                                  | N/A&#xA;                                                                                               |
| 6&#xA;  | currency\_code&#xA;      | CurrencyCode&#xA;     | ISO 4217 currency code for the LC&#xA;                  | VARCHAR&#xA;  | 3&#xA;      | Yes&#xA;       | "USD"&#xA;         | Valid ISO currency code&#xA;                                                             | N/A&#xA;                                                                                               |
| 7&#xA;  | issue\_date&#xA;         | IssueDate&#xA;        | Date when the LC is issued&#xA;                         | DATE&#xA;     | -&#xA;      | Yes&#xA;       | CURRENT\_DATE&#xA; | Valid future date&#xA;                                                                   | 00 request→01 open→02 issue→03 advice→04 negotiated→05 redump→06 closed00/01/03/04/05→07 rejected&#xA; |
| 8&#xA;  | expiry\_date&#xA;        | ExpiryDate&#xA;       | Date when the LC expires&#xA;                           | DATE&#xA;     | -&#xA;      | Yes&#xA;       | ""&#xA;            | > issue\_date&#xA;                                                                       | N/A&#xA;                                                                                               |
| 9&#xA;  | status&#xA;              | LCStatus&#xA;         | Lifecycle status of the LC&#xA;                         | ENUM&#xA;     | 20&#xA;     | Yes&#xA;       | "00"&#xA;          | 00=request,01=open,02=issue,03=advice,04=negotiated,05=redump,06=closed,07=rejected&#xA; | 00 request→01 open→02 issue→03 advice→04 negotiated→05 redump→06 closed00/01/03/04/05→07 rejected&#xA; |
| 10&#xA; | goods\_description&#xA;  | GoodsDescription&#xA; | Description of goods or services covered by the LC&#xA; | VARCHAR&#xA;  | 500&#xA;    | Yes&#xA;       | ""&#xA;            | Non - empty text&#xA;                                                                    | N/A&#xA;                                                                                               |

### Table Name: infinity\_compliance\_domain\_doc\_compliance\_mas&#xA;



| No&#xA; | ShortName&#xA;          | LongName&#xA;         | Description&#xA;                                               | DataType&#xA; | Length&#xA; | Mandatory&#xA; | DefaultValue&#xA;  | ValidationRules&#xA;               | SWIFTMapping(700)&#xA;                   |
| ------- | ----------------------- | --------------------- | -------------------------------------------------------------- | ------------- | ----------- | -------------- | ------------------ | ---------------------------------- | ---------------------------------------- |
| 1&#xA;  | lc\_id&#xA;             | LCIdentifier&#xA;     | Linked LC identifier&#xA;                                      | VARCHAR&#xA;  | 20&#xA;     | Yes&#xA;       | ""&#xA;            | Valid existing LC\_ID&#xA;         | 20: Documentary Credit Number&#xA;       |
| 2&#xA;  | doc\_set\_id&#xA;       | DocumentSetID&#xA;    | Unique identifier for a set of documents&#xA;                  | VARCHAR&#xA;  | 20&#xA;     | Yes&#xA;       | Auto-generate&#xA; | Unique&#xA;                        | 21: Reference to Related Document&#xA;   |
| 3&#xA;  | doc\_type&#xA;          | DocumentType&#xA;     | Type of submitted document (e.g., B/L, INV)&#xA;               | ENUM&#xA;     | 20&#xA;     | Yes&#xA;       | ""&#xA;            | B/L/INV/CERT/OTHER&#xA;            | 46A: Documents Required&#xA;             |
| 4&#xA;  | submission\_date&#xA;   | SubmissionDate&#xA;   | Date when documents are submitted&#xA;                         | DATE&#xA;     | -&#xA;      | Yes&#xA;       | CURRENT\_DATE&#xA; | ≤ expiry\_date&#xA;                | 48: Period for Presentation&#xA;         |
| 5&#xA;  | compliance\_status&#xA; | ComplianceStatus&#xA; | Result of document compliance check (e.g., APPROVED, RFI)&#xA; | ENUM&#xA;     | 20&#xA;     | Yes&#xA;       | "PENDING"&#xA;     | PENDING/APPROVED/RFI/REJECTED&#xA; | 73B: Details of Charges (RFI notes)&#xA; |

### Table Name: infinity\_transaction\_domain\_trans\_tracking\_mas&#xA;



| No&#xA; | ShortName&#xA;   | LongName&#xA;          | Description&#xA;                                    | DataType&#xA; | Length&#xA; | Mandatory&#xA; | DefaultValue&#xA;  | ValidationRules&#xA;                | SWIFTMapping(700)&#xA;                 |
| ------- | ---------------- | ---------------------- | --------------------------------------------------- | ------------- | ----------- | -------------- | ------------------ | ----------------------------------- | -------------------------------------- |
| 1&#xA;  | trans\_id&#xA;   | TransactionID&#xA;     | Unique transaction identifier&#xA;                  | VARCHAR&#xA;  | 20&#xA;     | Yes&#xA;       | Auto-generate&#xA; | Unique&#xA;                         | 21: Reference to Related Document&#xA; |
| 2&#xA;  | lc\_id&#xA;      | LCIdentifier&#xA;      | Linked LC identifier&#xA;                           | VARCHAR&#xA;  | 20&#xA;     | Yes&#xA;       | ""&#xA;            | Valid existing LC\_ID&#xA;          | 20: Documentary Credit Number&#xA;     |
| 3&#xA;  | trans\_type&#xA; | TransactionType&#xA;   | Type of transaction (e.g., PAYMENT, AMENDMENT)&#xA; | ENUM&#xA;     | 20&#xA;     | Yes&#xA;       | "PAYMENT"&#xA;     | PAYMENT/AMENDMENT/FEE/INTEREST&#xA; | 32B: Currency Code + Amount&#xA;       |
| 4&#xA;  | trans\_date&#xA; | TransactionDate&#xA;   | Date when the transaction occurs&#xA;               | DATE&#xA;     | -&#xA;      | Yes&#xA;       | CURRENT\_DATE&#xA; | Valid past date&#xA;                | 31D: Date and Place of Expiry&#xA;     |
| 5&#xA;  | amount&#xA;      | TransactionAmount&#xA; | Monetary value of the transaction&#xA;              | DECIMAL&#xA;  | 18,2&#xA;   | Yes&#xA;       | 0.00&#xA;          | ≠0&#xA;                             | 32B: Currency Code + Amount&#xA;       |

### Table Name: infinity\_integration\_domain\_swift\_integration\_mas&#xA;



| No&#xA; | ShortName&#xA;     | LongName&#xA;         | Description&#xA;                                | DataType&#xA; | Length&#xA; | Mandatory&#xA; | DefaultValue&#xA;  | ValidationRules&#xA;         | SWIFTMessageType&#xA;                     |
| ------- | ------------------ | --------------------- | ----------------------------------------------- | ------------- | ----------- | -------------- | ------------------ | ---------------------------- | ----------------------------------------- |
| 1&#xA;  | msg\_id&#xA;       | SWIFTMessageID&#xA;   | Unique SWIFT message identifier&#xA;            | VARCHAR&#xA;  | 35&#xA;     | Yes&#xA;       | Auto-generate&#xA; | Unique&#xA;                  | All types (e.g., MT700, MT730)&#xA;       |
| 2&#xA;  | msg\_type&#xA;     | SWIFTMessageType&#xA; | Type of SWIFT message (e.g., MT700, MT730)&#xA; | ENUM&#xA;     | 10&#xA;     | Yes&#xA;       | "MT700"&#xA;       | MT700/MT730/MT740/MT750&#xA; | N/A&#xA;                                  |
| 3&#xA;  | sender\_bic&#xA;   | SenderBIC&#xA;        | SWIFT/BIC of the message sender&#xA;            | VARCHAR&#xA;  | 11&#xA;     | Yes&#xA;       | ""&#xA;            | Valid SWIFT/BIC code&#xA;    | MT700: 51A: Sender's Correspondent&#xA;   |
| 4&#xA;  | receiver\_bic&#xA; | ReceiverBIC&#xA;      | SWIFT/BIC of the message receiver&#xA;          | VARCHAR&#xA;  | 11&#xA;     | Yes&#xA;       | ""&#xA;            | Valid SWIFT/BIC code&#xA;    | MT700: 52A: Drawn on Bank&#xA;            |
| 5&#xA;  | lc\_id&#xA;        | LCIdentifier&#xA;     | Linked LC identifier&#xA;                       | VARCHAR&#xA;  | 20&#xA;     | Yes&#xA;       | ""&#xA;            | Valid existing LC\_ID&#xA;   | MT700: 20: Documentary Credit Number&#xA; |

### Table Name: infinity\_accounting\_domain\_fin\_accounting\_mas&#xA;



| No&#xA; | ShortName&#xA;      | LongName&#xA;          | Description&#xA;                           | DataType&#xA; | Length&#xA; | Mandatory&#xA; | DefaultValue&#xA;  | ValidationRules&#xA;       | AccountingStandard&#xA; |
| ------- | ------------------- | ---------------------- | ------------------------------------------ | ------------- | ----------- | -------------- | ------------------ | -------------------------- | ----------------------- |
| 1&#xA;  | acc\_entry\_id&#xA; | AccountingEntryID&#xA; | Unique accounting entry identifier&#xA;    | VARCHAR&#xA;  | 20&#xA;     | Yes&#xA;       | Auto-generate&#xA; | Unique&#xA;                | IFRS/IAS&#xA;           |
| 2&#xA;  | lc\_id&#xA;         | LCIdentifier&#xA;      | Linked LC identifier&#xA;                  | VARCHAR&#xA;  | 20&#xA;     | Yes&#xA;       | ""&#xA;            | Valid existing LC\_ID&#xA; | N/A&#xA;                |
| 3&#xA;  | entry\_date&#xA;    | EntryDate&#xA;         | Date of the accounting entry&#xA;          | DATE&#xA;     | -&#xA;      | Yes&#xA;       | CURRENT\_DATE&#xA; | Valid past date&#xA;       | N/A&#xA;                |
| 4&#xA;  | debit\_amount&#xA;  | DebitAmount&#xA;       | Debit amount of the accounting entry&#xA;  | DECIMAL&#xA;  | 18,2&#xA;   | Yes&#xA;       | 0.00&#xA;          | ≥0&#xA;                    | N/A&#xA;                |
| 5&#xA;  | credit\_amount&#xA; | CreditAmount&#xA;      | Credit amount of the accounting entry&#xA; | DECIMAL&#xA;  | 18,2&#xA;   | Yes&#xA;       | 0.00&#xA;          | ≥0&#xA;                    | N/A&#xA;                |

Section 3: default values of each column





| Table&#xA;                                                  | Column&#xA;              | DefaultValue&#xA;  | Mandatory&#xA; | SWIFTMapping&#xA;                      |
| ----------------------------------------------------------- | ------------------------ | ------------------ | -------------- | -------------------------------------- |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | lc\_id&#xA;              | Auto-generate&#xA; | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | applicant\_name&#xA;     | ""&#xA;            | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | beneficiary\_name&#xA;   | ""&#xA;            | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | issuing\_bank\_code&#xA; | ""&#xA;            | Yes&#xA;       | 51A: Sender's Correspondent&#xA;       |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | lc\_amount&#xA;          | 0.00&#xA;          | Yes&#xA;       | 32B: Currency Code + Amount&#xA;       |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | currency\_code&#xA;      | "USD"&#xA;         | Yes&#xA;       | 32B: Currency Code&#xA;                |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | issue\_date&#xA;         | CURRENT\_DATE&#xA; | Yes&#xA;       | 31C: Date of Issue&#xA;                |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | expiry\_date&#xA;        | ""&#xA;            | Yes&#xA;       | 31D: Date and Place of Expiry&#xA;     |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | status&#xA;              | "00"&#xA;          | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_core\_domain\_lc\_master\_mas&#xA;                | goods\_description&#xA;  | ""&#xA;            | Yes&#xA;       | 45A: Description of Goods&#xA;         |
| infinity\_compliance\_domain\_doc\_compliance\_mas&#xA;     | lc\_id&#xA;              | ""&#xA;            | Yes&#xA;       | 20: Documentary Credit Number&#xA;     |
| infinity\_compliance\_domain\_doc\_compliance\_mas&#xA;     | doc\_set\_id&#xA;        | Auto-generate&#xA; | Yes&#xA;       | 21: Reference to Related Document&#xA; |
| infinity\_compliance\_domain\_doc\_compliance\_mas&#xA;     | doc\_type&#xA;           | ""&#xA;            | Yes&#xA;       | 46A: Documents Required&#xA;           |
| infinity\_compliance\_domain\_doc\_compliance\_mas&#xA;     | submission\_date&#xA;    | CURRENT\_DATE&#xA; | Yes&#xA;       | 48: Period for Presentation&#xA;       |
| infinity\_compliance\_domain\_doc\_compliance\_mas&#xA;     | compliance\_status&#xA;  | "PENDING"&#xA;     | Yes&#xA;       | 73B: Details of Charges&#xA;           |
| infinity\_transaction\_domain\_trans\_tracking\_mas&#xA;    | trans\_id&#xA;           | Auto-generate&#xA; | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_transaction\_domain\_trans\_tracking\_mas&#xA;    | lc\_id&#xA;              | ""&#xA;            | Yes&#xA;       | 20: Documentary Credit Number&#xA;     |
| infinity\_transaction\_domain\_trans\_tracking\_mas&#xA;    | trans\_type&#xA;         | "PAYMENT"&#xA;     | Yes&#xA;       | 32B: Currency Code + Amount&#xA;       |
| infinity\_transaction\_domain\_trans\_tracking\_mas&#xA;    | trans\_date&#xA;         | CURRENT\_DATE&#xA; | Yes&#xA;       | 31D: Date and Place of Expiry&#xA;     |
| infinity\_transaction\_domain\_trans\_tracking\_mas&#xA;    | amount&#xA;              | 0.00&#xA;          | Yes&#xA;       | 32B: Currency Code + Amount&#xA;       |
| infinity\_integration\_domain\_swift\_integration\_mas&#xA; | msg\_id&#xA;             | Auto-generate&#xA; | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_integration\_domain\_swift\_integration\_mas&#xA; | msg\_type&#xA;           | "MT700"&#xA;       | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_integration\_domain\_swift\_integration\_mas&#xA; | sender\_bic&#xA;         | ""&#xA;            | Yes&#xA;       | 51A: Sender's Correspondent&#xA;       |
| infinity\_integration\_domain\_swift\_integration\_mas&#xA; | receiver\_bic&#xA;       | ""&#xA;            | Yes&#xA;       | 52A: Drawn on Bank&#xA;                |
| infinity\_integration\_domain\_swift\_integration\_mas&#xA; | lc\_id&#xA;              | ""&#xA;            | Yes&#xA;       | 20: Documentary Credit Number&#xA;     |
| infinity\_accounting\_domain\_fin\_accounting\_mas&#xA;     | acc\_entry\_id&#xA;      | Auto-generate&#xA; | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_accounting\_domain\_fin\_accounting\_mas&#xA;     | lc\_id&#xA;              | ""&#xA;            | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_accounting\_domain\_fin\_accounting\_mas&#xA;     | entry\_date&#xA;         | CURRENT\_DATE&#xA; | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_accounting\_domain\_fin\_accounting\_mas&#xA;     | debit\_amount&#xA;       | 0.00&#xA;          | Yes&#xA;       | no a SWIFT mapped field&#xA;           |
| infinity\_accounting\_domain\_fin\_accounting\_mas&#xA;     | credit\_amount&#xA;      | 0.00&#xA;          | Yes&#xA;       | no a SWIFT mapped field&#xA;           |

Section 5: your doubts or inquiry





*   Are there specific data length requirements for fields other than those specified? For example, should the `goods_description` have a more precise length limit?


*   Regarding the `status` field in `infinity_core_domain_lc_master_mas`, are there any additional status transitions that need to be considered?


*   For the `ENUM` type fields,  are there any plans to expand the list of possible values in the future?

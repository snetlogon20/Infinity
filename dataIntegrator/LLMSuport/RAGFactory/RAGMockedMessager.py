import os

class RAGMockedMessager():

    # txt2req
    txt2req_MOCKED_AI_ANSWER = """# Trade Finance System Business Table Requirements

        Abstract
        
        
        
        This requirement defines business tables for a trade finance system, covering core LC master data, compliance, tracking, SWIFT integration, and financial accounting, to support efficient trade operations.
        
        
        Section 1 The data model of LC business
        
        
        
        Using the snowflake model, the data tables are divided into the following data domains:
        
        
        
        
        | No| | Table Name|                     | Table Description|                                                                                                                     |
        | ------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
        | 1|  | core\_finance\_lc\_master\_mas| | Holds the master data for Letters of Credit, including 20 columns with key information about LC transactions.|                         |
        | 2|  | compliance\_documentary\_mas|   | Manages documentary compliance data for LC operations, consisting of 10 columns to ensure regulatory and contractual adherence.|       |
        | 3|  | tracking\_transaction\_mas|     | Records transaction tracking details, with 10 columns to monitor the lifecycle of LC - related transactions.|                          |
        | 4|  | integration\_swift\_mas|        | Handles data for SWIFT integration, having 10 columns to facilitate communication and data exchange with SWIFT systems.|               |
        | 5|  | accounting\_financial\_mas|     | Stores financial accounting data for LC - related financial activities, with 10 columns for financial record - keeping and reporting.| |
        
        Section 2 The detail table information
        
        
        
        ### Table Name: core\_finance\_lc\_master\_mas|
        
        
        
        | No| | Short Name|                 | Long Name|                         | Description|                                                                                                                                                                                                                                                 | Data Type| | Length| | Mandatory| | Default Value|                      | Validation Rules|                       |
        | ------- | ------------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ----------- | -------------- | --------------------------------------- | ------------------------------------------- |
        | 1|  | lc\_id|                     | Letter of Credit Identifier|       | A unique identifier for each LC|                                                                                                                                                                                                                             | VARCHAR|   | 20|     | Yes|       | Auto - generate|                    | Unique|                                 |
        | 2|  | lc\_ref\_num|               | Letter of Credit Reference Number| | A reference number for the LC used for internal and external communication|                                                                                                                                                                                  | VARCHAR|   | 20|     | Yes|       | ""|                                 | Valid format|                           |
        | 3|  | applicant|                  | LC Applicant|                      | The party applying for the LC|                                                                                                                                                                                                                               | VARCHAR|   | 100|    | Yes|       | ""|                                 | Valid entity name|                      |
        | 4|  | beneficiary|                | LC Beneficiary|                    | The party to be paid under the LC|                                                                                                                                                                                                                           | VARCHAR|   | 100|    | Yes|       | ""|                                 | Valid entity name|                      |
        | 5|  | issuing\_bank|              | LC Issuing Bank|                   | The bank that issues the LC|                                                                                                                                                                                                                                 | VARCHAR|   | 100|    | Yes|       | ""|                                 | Valid bank name|                        |
        | 6|  | advising\_bank|             | LC Advising Bank|                  | The bank that advises the LC to the beneficiary|                                                                                                                                                                                                             | VARCHAR|   | 100|    | No|        | ""|                                 | Valid bank name|                        |
        | 7|  | amount|                     | LC Amount|                         | The total amount of the LC|                                                                                                                                                                                                                                  | DECIMAL|   | 18,2|   | Yes|       | 0.00|                               | > 0|                                    |
        | 8|  | currency|                   | LC Currency|                       | The currency of the LC|                                                                                                                                                                                                                                      | VARCHAR|   | 3|      | Yes|       | ""|                                 | Valid ISO 4217 currency code|           |
        | 9|  | expiry\_date|               | LC Expiry Date|                    | The date when the LC expires|                                                                                                                                                                                                                                | DATE|      | -|      | Yes|       | Calculated based on business rules| | Future date|                            |
        | 10| | presentation\_period|       | LC Presentation Period|            | The period within which documents must be presented|                                                                                                                                                                                                         | INT|       | -|      | Yes|       | 0|                                  | > 0|                                    |
        | 11| | status|                     | LC Status|                         | The current status of the LC, following 00 request->01 open->02 issue->03 advice->04 negotiated -> 05 redump ->06 closed, 00 request->07 rejected, 01 request->07 rejected, 03 advice ->07 rejected, 04 negotiated ->07 rejected, 05 redumped ->07 rejected| | VARCHAR|   | 2|      | Yes|       | "00"|                               | Valid status sequence|                  |
        | 12| | goods\_description|         | Description of Goods|              | A description of the goods covered by the LC|                                                                                                                                                                                                                | VARCHAR|   | 500|    | Yes|       | ""|                                 | Valid description|                      |
        | 13| | shipment\_details|          | Shipment Details|                  | Details regarding the shipment of goods|                                                                                                                                                                                                                     | VARCHAR|   | 500|    | No|        | ""|                                 | Valid shipment information|             |
        | 14| | partial\_shipment\_allowed| | Partial Shipment Allowed|          | Indicates whether partial shipment is allowed|                                                                                                                                                                                                               | BOOLEAN|   | -|      | Yes|       | FALSE|                              | Valid boolean value|                    |
        | 15| | transshipment\_allowed|     | Transshipment Allowed|             | Indicates whether transshipment is allowed|                                                                                                                                                                                                                  | BOOLEAN|   | -|      | Yes|       | FALSE|                              | Valid boolean value|                    |
        | 16| | latest\_shipment\_date|     | Latest Shipment Date|              | The latest date for shipment|                                                                                                                                                                                                                                | DATE|      | -|      | Yes|       | Calculated based on business rules| | Future date, earlier than expiry\_date| |
        | 17| | documents\_required|        | Documents Required|                | A list of documents required for payment under the LC|                                                                                                                                                                                                       | VARCHAR|   | 1000|   | Yes|       | ""|                                 | Valid document list|                    |
        | 18| | additional\_conditions|     | Additional Conditions|             | Any additional conditions of the LC|                                                                                                                                                                                                                         | VARCHAR|   | 1000|   | No|        | ""|                                 | Valid conditions|                       |
        | 19| | amendment\_history|         | LC Amendment History|              | Records of any amendments made to the LC|                                                                                                                                                                                                                    | VARCHAR|   | 2000|   | No|        | ""|                                 | Valid amendment records|                |
        | 20| | creation\_date|             | LC Creation Date|                  | The date when the LC was created|                                                                                                                                                                                                                            | DATE|      | -|      | Yes|       | CURRENT\_DATE|                      | Valid past date|                        |
        
        ### Table Name: compliance\_documentary\_mas|
        
        
        
        | No| | Short Name|           | Long Name|                             | Description|                                                              | Data Type| | Length| | Mandatory| | Default Value|   | Validation Rules|                             |
        | ------- | ------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------- | -------------- | ----------- | -------------- | -------------------- | ------------------------------------------------- |
        | 1|  | doc\_id|              | Document Identifier|                   | A unique identifier for each compliance document|                         | VARCHAR|   | 20|     | Yes|       | Auto - generate| | Unique|                                       |
        | 2|  | lc\_id\_ref|          | Letter of Credit Identifier Reference| | References the related LC|                                                | VARCHAR|   | 20|     | Yes|       | ""|              | Valid existing lc\_id|                        |
        | 3|  | doc\_type|            | Document Type|                         | The type of the compliance document (e.g., Bill of Lading, Invoice)|      | VARCHAR|   | 50|     | Yes|       | ""|              | Valid document type list|                     |
        | 4|  | doc\_status|          | Document Status|                       | The current status of the document (e.g., Submitted, Reviewed, Approved)| | VARCHAR|   | 20|     | Yes|       | "Submitted"|     | Valid status list|                            |
        | 5|  | submission\_date|     | Document Submission Date|              | The date when the document was submitted|                                 | DATE|      | -|      | Yes|       | CURRENT\_DATE|   | Valid past date|                              |
        | 6|  | review\_date|         | Document Review Date|                  | The date when the document was reviewed|                                  | DATE|      | -|      | No|        | ""|              | Valid past date, later than submission\_date| |
        | 7|  | approval\_date|       | Document Approval Date|                | The date when the document was approved|                                  | DATE|      | -|      | No|        | ""|              | Valid past date, later than review\_date|     |
        | 8|  | reviewer|             | Document Reviewer|                     | The person who reviewed the document|                                     | VARCHAR|   | 100|    | No|        | ""|              | Valid user name|                              |
        | 9|  | approver|             | Document Approver|                     | The person who approved the document|                                     | VARCHAR|   | 100|    | No|        | ""|              | Valid user name|                              |
        | 10| | compliance\_comments| | Compliance Comments|                   | Any comments regarding the compliance of the document|                    | VARCHAR|   | 500|    | No|        | ""|              | Valid comment text|                           |
        
        ### Table Name: tracking\_transaction\_mas|
        
        
        
        | No| | Short Name|     | Long Name|                             | Description|                                                                | Data Type| | Length| | Mandatory| | Default Value|   | Validation Rules|            |
        | ------- | ------------------- | ------------------------------------------ | ------------------------------------------------------------------------------- | -------------- | ----------- | -------------- | -------------------- | -------------------------------- |
        | 1|  | trans\_id|      | Transaction Identifier|                | A unique identifier for each transaction|                                   | VARCHAR|   | 20|     | Yes|       | Auto - generate| | Unique|                      |
        | 2|  | lc\_id\_ref|    | Letter of Credit Identifier Reference| | References the related LC|                                                  | VARCHAR|   | 20|     | Yes|       | ""|              | Valid existing lc\_id|       |
        | 3|  | trans\_type|    | Transaction Type|                      | The type of the transaction (e.g., Payment, Amendment, Fee)|                | VARCHAR|   | 20|     | Yes|       | ""|              | Valid transaction type list| |
        | 4|  | trans\_date|    | Transaction Date|                      | The date when the transaction occurred|                                     | DATE|      | -|      | Yes|       | CURRENT\_DATE|   | Valid past date|             |
        | 5|  | amount|         | Transaction Amount|                    | The monetary value of the transaction|                                      | DECIMAL|   | 18,2|   | Yes|       | 0.00|            | != 0|                        |
        | 6|  | sender|         | Transaction Sender|                    | The party initiating the transaction|                                       | VARCHAR|   | 100|    | Yes|       | ""|              | Valid entity name|           |
        | 7|  | receiver|       | Transaction Receiver|                  | The party receiving the transaction|                                        | VARCHAR|   | 100|    | Yes|       | ""|              | Valid entity name|           |
        | 8|  | trans\_status|  | Transaction Status|                    | The current status of the transaction (e.g., Pending, Completed, Rejected)| | VARCHAR|   | 20|     | Yes|       | "Pending"|       | Valid status list|           |
        | 9|  | reference\_num| | Transaction Reference Number|          | A reference number for the transaction|                                     | VARCHAR|   | 20|     | No|        | ""|              | Valid format|                |
        | 10| | remarks|        | Transaction Remarks|                   | Any remarks related to the transaction|                                     | VARCHAR|   | 500|    | No|        | ""|              | Valid comment text|          |
        
        ### Table Name: integration\_swift\_mas|
        
        
        
        | No| | Short Name|     | Long Name|                             | Description|                                                                  | Data Type| | Length| | Mandatory| | Default Value|   | Validation Rules|                |
        | ------- | ------------------- | ------------------------------------------ | --------------------------------------------------------------------------------- | -------------- | ----------- | -------------- | -------------------- | ------------------------------------ |
        | 1|  | swift\_msg\_id| | SWIFT Message Identifier|              | A unique identifier for each SWIFT message|                                   | VARCHAR|   | 20|     | Yes|       | Auto - generate| | Unique|                          |
        | 2|  | lc\_id\_ref|    | Letter of Credit Identifier Reference| | References the related LC|                                                    | VARCHAR|   | 20|     | Yes|       | ""|              | Valid existing lc\_id|           |
        | 3|  | msg\_type|      | SWIFT Message Type|                    | The type of the SWIFT message (e.g., 700, 701)|                               | VARCHAR|   | 3|      | Yes|       | ""|              | Valid SWIFT message type list|   |
        | 4|  | sender\_bic|    | Sender Bank Identifier Code|           | The BIC of the sender bank|                                                   | VARCHAR|   | 11|     | Yes|       | ""|              | Valid BIC format|                |
        | 5|  | receiver\_bic|  | Receiver Bank Identifier Code|         | The BIC of the receiver bank|                                                 | VARCHAR|   | 11|     | Yes|       | ""|              | Valid BIC format|                |
        | 6|  | msg\_date|      | SWIFT Message Date|                    | The date when the SWIFT message was sent|                                     | DATE|      | -|      | Yes|       | CURRENT\_DATE|   | Valid past date|                 |
        | 7|  | msg\_text|      | SWIFT Message Text|                    | The content of the SWIFT message|                                             | VARCHAR|   | 5000|   | Yes|       | ""|              | Valid SWIFT message text format| |
        | 8|  | status|         | SWIFT Message Status|                  | The current status of the SWIFT message (e.g., Sent, Received, Acknowledged)| | VARCHAR|   | 20|     | Yes|       | "Sent"|          | Valid status list|               |
        | 9|  | seq\_num|       | SWIFT Message Sequence Number|         | The sequence number of the SWIFT message within a conversation|               | INT|       | -|      | No|        | 0|               | > 0|                             |
        | 10| | error\_code|    | SWIFT Message Error Code|              | Any error code associated with the SWIFT message|                             | VARCHAR|   | 20|     | No|        | ""|              | Valid error code list|           |
        
        ### Table Name: accounting\_financial\_mas|
        
        
        
        | No| | Short Name|      | Long Name|                             | Description|                                                              | Data Type| | Length| | Mandatory| | Default Value|   | Validation Rules|             |
        | ------- | -------------------- | ------------------------------------------ | ----------------------------------------------------------------------------- | -------------- | ----------- | -------------- | -------------------- | --------------------------------- |
        | 1|  | acc\_trans\_id|  | Accounting Transaction Identifier|     | A unique identifier for each accounting transaction|                      | VARCHAR|   | 20|     | Yes|       | Auto - generate| | Unique|                       |
        | 2|  | lc\_id\_ref|     | Letter of Credit Identifier Reference| | References the related LC|                                                | VARCHAR|   | 20|     | Yes|       | ""|              | Valid existing lc\_id|        |
        | 3|  | acc\_type|       | Accounting Type|                       | The type of the accounting transaction (e.g., Debit, Credit)|             | VARCHAR|   | 10|     | Yes|       | ""|              | Valid accounting type list|   |
        | 4|  | acc\_date|       | Accounting Date|                       | The date when the accounting transaction occurred|                        | DATE|      | -|      | Yes|       | CURRENT\_DATE|   | Valid past date|              |
        | 5|  | amount|          | Accounting Amount|                     | The monetary value of the accounting transaction|                         | DECIMAL|   | 18,2|   | Yes|       | 0.00|            | != 0|                         |
        | 6|  | account\_num|    | Account Number|                        | The account number related to the transaction|                            | VARCHAR|   | 30|     | Yes|       | ""|              | Valid account number format|  |
        | 7|  | description|     | Accounting Description|                | A description of the accounting transaction|                              | VARCHAR|   | 500|    | Yes|       | ""|              | Valid description|            |
        | 8|  | cost\_center|    | Cost Center|                           | The cost center associated with the transaction|                          | VARCHAR|   | 50|     | No|        | ""|              | Valid cost center code|       |
        | 9|  | currency|        | Accounting Currency|                   | The currency of the accounting transaction|                               | VARCHAR|   | 3|      | Yes|       | ""|              | Valid ISO 4217 currency code| |
        | 10| | posting\_status| | Accounting Posting Status|             | The posting status of the accounting transaction (e.g., Posted, Pending)| | VARCHAR|   | 20|     | Yes|       | "Pending"|       | Valid status list|            |
        
        
        Section 3 default values of each column
        
        
        
        ### Table Name: core\_finance\_lc\_master\_mas|
        
        
        
        | Short Name|                 | Default Value|                      | Description|                                              | SWIFT 700 Mapping|                                                    |
        | ------------------------------- | --------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------- |
        | lc\_id|                     | Auto - generate|                    | Automatically generated unique LC identifier|             | No a SWIFT mapped field|                                              |
        | lc\_ref\_num|               | ""|                                 | Empty string as placeholder until assigned|               | No a SWIFT mapped field|                                              |
        | applicant|                  | ""|                                 | Empty string until the applicant information is provided| | Mapped to field '50a/50b/50c/50d' in SWIFT 700, format: entity name|  |
        | beneficiary|                | ""|                                 | Empty string until the beneficiary details are filled|    | Mapped to field '59' in SWIFT 700, format: entity name|               |
        | issuing\_bank|              | ""|                                 | Empty string before bank details are input|               | Mapped to field '52a/52b/52c' in SWIFT 700, format: bank name|        |
        | advising\_bank|             | ""|                                 | Empty string if not applicable|                           | Mapped to field '57a/57b/57c/57d' in SWIFT 700, format: bank name|    |
        | amount|                     | 0.00|                               | Represents initial amount value|                          | Mapped to field '32B' in SWIFT 700, format: currency code + amount|   |
        | currency|                   | ""|                                 | Empty string until currency is specified|                 | Mapped to field '32B' in SWIFT 700, format: ISO 4217 currency code|   |
        | expiry\_date|               | Calculated based on business rules| | Determined by internal business logic|                    | Mapped to field '31D' in SWIFT 700, format: date|                     |
        | presentation\_period|       | 0|                                  | Initial value indicating no period set yet|               | No a SWIFT mapped field|                                              |
        | status|                     | "00"|                               | Initial status as 'request'|                              | No a SWIFT mapped field|                                              |
        | goods\_description|         | ""|                                 | Empty string until goods details are added|               | Mapped to field '45A/45B/45C' in SWIFT 700, format: text description| |
        | shipment\_details|          | ""|                                 | Empty string if no shipment details available|            | Mapped to field '44A/44B/44C/44D' in SWIFT 700, format: text details| |
        | partial\_shipment\_allowed| | FALSE|                              | Defaults to not allowing partial shipment|                | No a SWIFT mapped field|                                              |
        | transshipment\_allowed|     | FALSE|                              | Defaults to not allowing transshipment|                   | No a SWIFT mapped field|                                              |
        | latest\_shipment\_date|     | Calculated based on business rules| | Set according to business rules|                          | Mapped to field '44C/44D' in SWIFT 700, format: date|                 |
        | documents\_required|        | ""|                                 | Empty string until document list is defined|              | Mapped to field '46A/46B' in SWIFT 700, format: text list|            |
        | additional\_conditions|     | ""|                                 | Empty string if no additional conditions|                 | Mapped to field '47A/47B' in SWIFT 700, format: text conditions|      |
        | amendment\_history|         | ""|                                 | Empty string until amendments occur|                      | No a SWIFT mapped field|                                              |
        | creation\_date|             | CURRENT\_DATE|                      | Date of LC creation|                                      | Mapped to field '31C' in SWIFT 700, format: date|                     |
        
        ### Table Name: compliance\_documentary\_mas|
        
        
        
        | Short Name|           | Default Value|   | Description|                                   | SWIFT 700 Mapping|       |
        | ------------------------- | -------------------- | -------------------------------------------------- | ---------------------------- |
        | doc\_id|              | Auto - generate| | Automatically generated document ID|           | No a SWIFT mapped field| |
        | lc\_id\_ref|          | ""|              | Empty string until related LC is assigned|     | No a SWIFT mapped field| |
        | doc\_type|            | ""|              | Empty string until document type is specified| | No a SWIFT mapped field| |
        | doc\_status|          | "Submitted"|     | Default status when document is first entered| | No a SWIFT mapped field| |
        | submission\_date|     | CURRENT\_DATE|   | Date of document submission|                   | No a SWIFT mapped field| |
        | review\_date|         | ""|              | Empty string until review occurs|              | No a SWIFT mapped field| |
        | approval\_date|       | ""|              | Empty string until approval happens|           | No a SWIFT mapped field| |
        | reviewer|             | ""|              | Empty string until reviewer is assigned|       | No a SWIFT mapped field| |
        | approver|             | ""|              | Empty string until approver is determined|     | No a SWIFT mapped field| |
        | compliance\_comments| | ""|              | Empty string if no comments|                   | No a SWIFT mapped field| |
        
        ### Table Name: tracking\_transaction\_mas|
        
        
        
        | Short Name|     | Default Value|   | Description|                                       | SWIFT 700 Mapping|       |
        | ------------------- | -------------------- | ------------------------------------------------------ | ---------------------------- |
        | trans\_id|      | Auto - generate| | Automatically generated transaction ID|            | No a SWIFT mapped field| |
        | lc\_id\_ref|    | ""|              | Empty string until related LC is set|              | No a SWIFT mapped field| |
        | trans\_type|    | ""|              | Empty string until transaction type is defined|    | No a SWIFT mapped field| |
        | trans\_date|    | CURRENT\_DATE|   | Date of transaction|                               | No a SWIFT mapped field| |
        | amount|         | 0.00|            | Initial amount value|                              | No a SWIFT mapped field| |
        | sender|         | ""|              | Empty string until sender information is provided| | No a SWIFT mapped field| |
        | receiver|       | ""|              | Empty string until receiver details are filled|    | No a SWIFT mapped field| |
        | trans\_status|  | "Pending"|       | Default status when transaction is initiated|      | No a SWIFT mapped field| |
        | reference\_num| | ""|              | Empty string until reference number is assigned|   | No a SWIFT mapped field| |
        | remarks|        | ""|              | Empty string if no remarks|                        | No a SWIFT mapped field| |
        
        ### Table Name: integration\_swift\_mas|
        
        
        
        | Short Name|     | Default Value|   | Description|                                      | SWIFT 700 Mapping|                                                                                                |
        | ------------------- | -------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
        | swift\_msg\_id| | Auto - generate| | Automatically generated SWIFT message ID|         | No a SWIFT mapped field|                                                                                          |
        | lc\_id\_ref|    | ""|              | Empty string until related LC is associated|      | No a SWIFT mapped field|                                                                                          |
        | msg\_type|      | ""|              | Empty string until message type is determined|    | No a SWIFT mapped field|                                                                                          |
        | sender\_bic|    | ""|              | Empty string until sender bank BIC is input|      | Mapped to field '52a/52b/52c' in SWIFT 700, format: BIC code|                                                     |
        | receiver\_bic|  | ""|              | Empty string until receiver bank BIC is provided| | Mapped to field '53a/53b/53c/54a/54b/54c/56a/56b/56c/57a/57b/57c/57d/58a/58b/58c' in SWIFT 700, format: BIC code| |
        | msg\_date|      | CURRENT\_DATE|   | Date of message sending|                          | Mapped to field '31C' in SWIFT 700, format: date|                                                                 |
        | msg\_text|      | ""|              | Empty string until message content is composed|   | Mapped to various text fields in SWIFT 700 depending on message type, format: text|                               |
        | status|         | "Sent"|          | Default status when message is first sent|        | No a SWIFT mapped field|                                                                                          |
        | seq\_num|       | 0|               | Initial sequence number|                          | No a SWIFT mapped field|                                                                                          |
        | error\_code|    | ""|              | Empty string if no error|                         | No a SWIFT mapped field|                                                                                          |
        
        ### Table Name: accounting\_financial\_mas|
        
        
        
        | Short Name|      | Default Value|   | Description|                                         | SWIFT 700 Mapping|       |
        | -------------------- | -------------------- | -------------------------------------------------------- | ---------------------------- |
        | acc\_trans\_id|  | Auto - generate| | Automatically generated accounting transaction ID|   | No a SWIFT mapped field| |
        | lc\_id\_ref|     | ""|              | Empty string until related LC is linked|             | No a SWIFT mapped field| |
        | acc\_type|       | ""|              | Empty string until accounting type is specified|     | No a SWIFT mapped field| |
        | acc\_date|       | CURRENT\_DATE|   | Date of accounting transaction|                      | No a SWIFT mapped field| |
        | amount|          | 0.00|            | Initial accounting amount|                           | No a SWIFT mapped field| |
        | account\_num|    | ""|              | Empty string until account number is entered|        | No a SWIFT mapped field| |
        | description|     | ""|              | Empty string until transaction description is added| | No a SWIFT mapped field| |
        | cost\_center|    | ""|              | Empty string if no cost center assigned|             | No a SWIFT mapped field| |
        | currency|        | ""|              | Empty string until currency is defined|              | No a SWIFT mapped field| |
        | posting\_status| | "Pending"|       | Default status when transaction is first recorded|   | No a SWIFT mapped field| |
        
        Section 4 validation rules
        
        
        
        ### Table Name: core\_finance\_lc\_master\_mas|
        
        
        
        | Column Name|                | Validate rule|                                       | Warning message|                                                                                             |
        | ------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
        | lc\_id|                     | Must be unique across all LCs|                       | "LC ID already exists. Please use a unique identifier."|                                                     |
        | lc\_ref\_num|               | Must follow the defined format|                      | "Invalid LC reference number format. Please check and re - enter."|                                          |
        | applicant|                  | Must be a valid entity name|                         | "Invalid applicant name. Please enter a valid entity name."|                                                 |
        | beneficiary|                | Must be a valid entity name|                         | "Invalid beneficiary name. Please enter a valid entity name."|                                               |
        | issuing\_bank|              | Must be a valid bank name|                           | "Invalid issuing bank name. Please enter a valid bank name."|                                                |
        | advising\_bank|             | If provided, must be a valid bank name|              | "Invalid advising bank name. Please enter a valid bank name or leave it blank if not applicable."|           |
        | amount|                     | Must be greater than 0|                              | "LC amount must be greater than 0. Please enter a valid amount."|                                            |
        | currency|                   | Must be a valid ISO 4217 currency code|              | "Invalid currency code. Please enter a valid ISO 4217 currency code."|                                       |
        | expiry\_date|               | Must be a future date|                               | "Expiry date must be in the future. Please enter a valid date."|                                             |
        | presentation\_period|       | Must be greater than 0|                              | "Presentation period must be greater than 0. Please enter a valid period."|                                  |
        | status|                     | Must follow the defined status sequence|             | "Invalid LC status transition. Please check the status sequence and correct it."|                            |
        | goods\_description|         | Must be a valid description|                         | "Invalid goods description. Please enter a clear and valid description."|                                    |
        | shipment\_details|          | If provided, must be valid shipment information|     | "Invalid shipment details. Please enter accurate shipment information or leave it blank if not applicable."| |
        | partial\_shipment\_allowed| | Must be a valid boolean value|                       | "Invalid value for partial shipment allowed. Please enter either TRUE or FALSE."|                            |
        | transshipment\_allowed|     | Must be a valid boolean value|                       | "Invalid value for transshipment allowed. Please enter either TRUE or FALSE."|                               |
        | latest\_shipment\_date|     | Must be a future date and earlier than expiry\_date| | "Latest shipment date must be in the future and earlier than the expiry date. Please correct the date."|     |
        | documents\_required|        | Must be a valid list of documents|                   | "Invalid document list. Please enter a valid list of required documents."|                                   |
        | additional\_conditions|     | If provided, must be valid conditions|               | "Invalid additional conditions. Please enter valid conditions or leave it blank if not applicable."|         |
        | amendment\_history|         | If provided, must be valid amendment records|        | "Invalid amendment history. Please enter valid records or leave it blank if no amendments."|                 |
        | creation\_date|             | Must be a valid past date|                           | "Invalid creation date. Please enter a valid past date."|                                                    |
        
        ### Table Name: compliance\_documentary\_mas|
        
        
        
        | Column Name|          | Validate rule|                                                      | Warning message|                                                                                  |
        | ------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
        | doc\_id|              | Must be unique across all compliance documents|                     | "Document ID already exists. Please use a unique identifier."|                                    |
        | lc\_id\_ref|          | Must reference an existing LC ID|                                   | "Invalid LC reference. Please enter a valid LC ID."|                                              |
        | doc\_type|            | Must be a valid document type from the allowed list|                | "Invalid document type. Please select from the valid document type list."|                        |
        | doc\_status|          | Must be a valid status from the allowed list|                       | "Invalid document status. Please select from the valid status list."|                             |
        | submission\_date|     | Must be a valid past date|                                          | "Invalid submission date. Please enter a valid past date."|                                       |
        | review\_date|         | If provided, must be a valid past date later than submission\_date| | "Invalid review date. Review date must be later than the submission date and a valid past date."| |
        | approval\_date|       | If provided, must be a valid past date later than review\_date|     | "Invalid approval date. Approval date must be later than the review date and a valid past date."| |
        | reviewer|             | If provided, must be a valid user name|                             | "Invalid reviewer name. Please enter a valid user name or leave it blank if not applicable."|     |
        | approver|             | If provided, must be a valid user name|                             | "Invalid approver name. Please enter a valid user name or leave it blank if not applicable."|     |
        | compliance\_comments| | If provided, must be valid comment text|                            | "Invalid compliance comments. Please enter valid text or leave it blank if no comments."|         |
        
        ### Table Name: tracking\_transaction\_mas|
        
        
        
        | Column Name|    | Validate rule|                                          | Warning message|                                                                 |
        | ------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------ |
        | trans\_id|      | Must be unique across all transactions|                 | "Transaction ID already exists. Please use a unique identifier."|                |
        | lc\_id\_ref|    | Must reference an existing LC ID|                       | "Invalid LC reference. Please enter a valid LC ID."|                             |
        | trans\_type|    | Must be a valid transaction type from the allowed list| | "Invalid transaction type. Please select from the valid transaction type list."| |
        | trans\_date|    | Must be a valid past date|                              | "Invalid transaction date. Please enter a valid past date."|                     |
        | amount|         | Must not be equal to 0|                                 | "Transaction amount cannot be 0. Please enter a valid amount."|                  |
        | sender|         | Must be a valid entity name|                            | "Invalid sender name. Please enter a valid entity name."|                        |
        | receiver|       | Must be a valid entity name|                            | "Invalid receiver name. Please enter a valid entity name."|                      |
        | trans\_status|  | Must be a valid status from the allowed list|           | "Invalid transaction status. Please select from the valid status list."|         |
        | reference\_num| | If provided, must follow the defined format|            | "Invalid reference number format. Please check and re - enter."|                 |
        | remarks|        | If provided, must be valid comment text|                | "Invalid remarks. Please enter valid text or leave it blank if no remarks."|     |
        
        ### Table Name: integration\_swift\_mas|
        
        
        
        | Column Name|    | Validate rule|                                                      | Warning message|                                                                      |
        | ------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
        | swift\_msg\_id| | Must be unique across all SWIFT messages|                           | "SWIFT message ID already exists. Please use a unique identifier."|                   |
        | lc\_id\_ref|    | Must reference an existing LC ID|                                   | "Invalid LC reference. Please enter a valid LC ID."|                                  |
        | msg\_type|      | Must be a valid SWIFT message type from the allowed list|           | "Invalid SWIFT message type. Please select from the valid message type list."|        |
        | sender\_bic|    | Must be a valid BIC format|                                         | "Invalid sender BIC format. Please enter a valid BIC code."|                          |
        | receiver\_bic|  | Must be a valid BIC format|                                         | "Invalid receiver BIC format. Please enter a valid BIC code."|                        |
        | msg\_date|      | Must be a valid past date|                                          | "Invalid message date. Please enter a valid past date."|                              |
        | msg\_text|      | Must follow the valid SWIFT message text format based on msg\_type| | "Invalid SWIFT message text format. Please check and correct the message content."|   |
        | status|         | Must be a valid status from the allowed list|                       | "Invalid SWIFT message status. Please select from the valid status list."|            |
        | seq\_num|       | Must be greater than 0 if provided|                                 | "Invalid sequence number. Sequence number must be greater than 0 if entered."|        |
        | error\_code|    | If provided, must be a valid error code from the allowed list|      | "Invalid error code. Please enter a valid error code or leave it blank if no error."| |
        
        ### Table Name: accounting\_financial\_mas|
        
        
        
        | Column Name|     | Validate rule|                                         | Warning message|                                                                            |
        | -------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
        | acc\_trans\_id|  | Must be unique across all accounting transactions|     | "Accounting transaction ID already exists. Please use a unique identifier."|                |
        | lc\_id\_ref|     | Must reference an existing LC ID|                      | "Invalid LC reference. Please enter a valid LC ID."|                                        |
        | acc\_type|       | Must be a valid accounting type from the allowed list| | "Invalid accounting type. Please select from the valid accounting type list."|              |
        | acc\_date|       | Must be a valid past date|                             | "Invalid accounting date. Please enter a valid past date."|                                 |
        | amount|          | Must not be equal to 0|                                | "Accounting amount cannot be 0. Please enter a valid amount."|                              |
        | account\_num|    | Must follow the valid account number format|           | "Invalid account number format. Please check and re - enter."|                              |
        | description|     | Must be a valid description|                           | "Invalid accounting description. Please enter a clear and valid description."|              |
        | cost\_center|    | If provided, must be a valid cost center code|         | "Invalid cost center code. Please enter a valid code or leave it blank if not applicable."| |
        | currency|        | Must be a valid ISO 4217 currency code|                | "Invalid currency code. Please enter a valid ISO 4217 currency code."|                      |
        | posting\_status| | Must be a valid status from the allowed list|          | "Invalid posting status. Please select from the valid status list."|                        |
        
        
        
        
        Section 5 your doubts or inquiry
        
        
        
        
        
        1.  In the `core_finance_lc_master_mas` table, for the `status` column, the defined status sequences cover common transitions, but it's unclear how to handle more complex or exceptional scenarios, such as re - opening a closed LC. Are there specific business rules for these situations?
        
        
        2.  Regarding the SWIFT 700 message mapping, the mapping rules for some fields seem rather general. For example, for the `msg_text` in the `integration_swift_mas` table, it's mentioned to map to various text fields depending on the message type, but it lacks detailed mapping instructions for each specific message type. Could you provide more specific guidelines?
        
        
        3.  For the calculation of `expiry_date` and `latest_shipment_date` in the `core_finance_lc_master_mas` table, it's stated to be based on business rules, but no details about these rules are given. What factors should be considered in these calculations?
        
        
        4.  In the validation rules, for columns with text descriptions like `goods_description` and `compliance_comments`, the validation for valid content is rather vague. How can we precisely define what constitutes a valid description or comment?
        
        
        Section 6 Reference URL
        
        
        
        
        
        | No| | Reference Doc|      | Reference Site|                                                                                                                                                                                                                                          |
        | ------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
        | 1|  | UCP600|             | [https://www.cietac.org/articles/63](https://www.cietac.org/articles/63)                                                                                                                                                                                     |
        | 2|  | SWIFT 700 document| | [https://mbd.baidu.com/newspage/data/dtlandingsuper?nid=dt\_4695470141140934410\&sourceFrom=search\_a](https://mbd.baidu.com/newspage/data/dtlandingsuper?nid=dt_4695470141140934410\&sourceFrom=search_a)                                                   |
        | 3|  | ISBP 745|           | [https://www.iccwbo.org/publications-and-resources/publications/international-standard-banking-practice-isbp-for-the-ucp-600/](https://www.iccwbo.org/publications-and-resources/publications/international-standard-banking-practice-isbp-for-the-ucp-600/) |
        | 4|  | ICC Trade Register| | [https://www.iccwbo.org/our-work/trade-finance/icc-trade-register/](https://www.iccwbo.org/our-work/trade-finance/icc-trade-register/)                                                                                                                       |
            """

    # txt2uml
    txt2uml_MOCKED_AI_ANSWER = """{
    "drop_table_sql_statement": [
      {
      "table_name": "infinity_core_domain_lc_master_mas",
      "drop_table_sql": "drop table IF EXISTS infinity_core_domain_lc_master_mas"
      },
      {
      "table_name": "infinity_compliance_domain_doc_compliance_mas",
      "drop_table_sql": "drop table IF EXISTS infinity_compliance_domain_doc_compliance_mas"
      },
      {
      "table_name": "infinity_transaction_domain_trans_tracking_mas",
      "drop_table_sql": "drop table IF EXISTS infinity_transaction_domain_trans_tracking_mas"
      },
      {
      "table_name": "infinity_integration_domain_swift_integration_mas",
      "drop_table_sql": "drop table IF EXISTS infinity_integration_domain_swift_integration_mas"
      },
      {
      "table_name": "infinity_accounting_domain_fin_accounting_mas",
      "drop_table_sql": "drop table IF EXISTS infinity_accounting_domain_fin_accounting_mas"
      }
    ],
    "create_table_sql_statement": [
      {
      "table_name": "infinity_core_domain_lc_master_mas",
      "create_table_sql": "CREATE TABLE infinity_core_domain_lc_master_mas (lc_id String, applicant_name String, beneficiary_name String, issuing_bank_code String, lc_amount Decimal(18,2), currency_code String, issue_date Date, expiry_date Date, status String, goods_description String) ENGINE=SummingMergeTree(lc_id) order by (lc_id) SETTINGS index_granularity = 8192"
      },
      {
      "table_name": "infinity_compliance_domain_doc_compliance_mas",
      "create_table_sql": "CREATE TABLE infinity_compliance_domain_doc_compliance_mas (lc_id String, doc_set_id String, doc_type String, submission_date Date, compliance_status String) ENGINE=SummingMergeTree(lc_id) order by (lc_id) SETTINGS index_granularity = 8192"
      },
      {
      "table_name": "infinity_transaction_domain_trans_tracking_mas",
      "create_table_sql": "CREATE TABLE infinity_transaction_domain_trans_tracking_mas (trans_id String, lc_id String, trans_type String, trans_date Date, amount Decimal(18,2)) ENGINE=SummingMergeTree(trans_id) order by (trans_id) SETTINGS index_granularity = 8192"
      },
      {
      "table_name": "infinity_integration_domain_swift_integration_mas",
      "create_table_sql": "CREATE TABLE infinity_integration_domain_swift_integration_mas (msg_id String, msg_type String, sender_bic String, receiver_bic String, lc_id String) ENGINE=SummingMergeTree(msg_id) order by (msg_id) SETTINGS index_granularity = 8192"
      },
      {
      "table_name": "infinity_accounting_domain_fin_accounting_mas",
      "create_table_sql": "CREATE TABLE infinity_accounting_domain_fin_accounting_mas (acc_entry_id String, lc_id String, entry_date Date, debit_amount Decimal(18,2), credit_amount Decimal(18,2)) ENGINE=SummingMergeTree(acc_entry_id) order by (acc_entry_id) SETTINGS index_granularity = 8192"
      }
    ],
    "create_table_uml_statement": "@startuml
        entity infinity_core_domain_lc_master_mas {
            lc_id : String,
            applicant_name : String,
            beneficiary_name : String,
            issuing_bank_code : String,
            lc_amount : Decimal(18, 2),
            currency_code : String,
            issue_date : Date,
            expiry_date : Date,
            status : String,
            goods_description : String
        }
        entity infinity_compliance_domain_doc_compliance_mas {
            lc_id : String,
            doc_set_id : String,
            doc_type : String,
            submission_date : Date,
            compliance_status : String
        }
        entity infinity_transaction_domain_trans_tracking_mas {
            trans_id : String,
            lc_id : String,
            trans_type : String,
            trans_date : Date,
            amount : Decimal(18, 2)
        }
        entity infinity_integration_domain_swift_integration_mas {
            msg_id : String,
            msg_type : String,
            sender_bic : String,
            receiver_bic : String,
            lc_id : String
        }
        entity infinity_accounting_domain_fin_accounting_mas {
            acc_entry_id : String,
            lc_id : String,
            entry_date : Date,
            debit_amount : Decimal(18, 2),
            credit_amount : Decimal(18, 2)
        }
        infinity_core_domain_lc_master_mas ||--o{ infinity_compliance_domain_doc_compliance_mas : contains
        infinity_core_domain_lc_master_mas ||--o{ infinity_transaction_domain_trans_tracking_mas : contains
        infinity_core_domain_lc_master_mas ||--o{ infinity_integration_domain_swift_integration_mas : contains
        infinity_core_domain_lc_master_mas ||--o{ infinity_accounting_domain_fin_accounting_mas : contains
        @enduml",
    "feedback":"字段长度和状态转换待确认，枚举值扩展需规划"
}
    """

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
        "ALTER TABLE infinity_core_domain_lc_master_mas DELETE WHERE 1=1;",
        "ALTER TABLE infinity_compliance_domain_doc_compliance_mas DELETE WHERE 1=1;",
        "ALTER TABLE infinity_transaction_domain_trans_tracking_mas DELETE WHERE 1=1;",
        "ALTER TABLE infinity_integration_domain_swift_integration_mas DELETE WHERE 1=1;",
        "ALTER TABLE infinity_accounting_domain_fin_accounting_mas DELETE WHERE 1=1;"
    ],
    "insert_sql": [
        "INSERT INTO infinity_core_domain_lc_master_mas (lc_id, applicant_name, beneficiary_name, issuing_bank_code, lc_amount, currency_code, issue_date, expiry_date, status, goods_description) VALUES ('LC0001', 'Applicant A Corp', 'Beneficiary A Ltd', 'BANKUS33', 50000.00, 'USD', '2024-06-01', '2024-09-01', '00', 'Industrial Machinery'), ('LC0002', 'Applicant B GmbH', 'Beneficiary B S.A.', 'DEUTDEFF', 75000.00, 'EUR', '2024-06-02', '2024-09-15', '01', 'Medical Equipment');",
        "INSERT INTO infinity_compliance_domain_doc_compliance_mas (lc_id, doc_set_id, doc_type, submission_date, compliance_status) VALUES ('LC0001', 'DS001', 'B/L', '2024-06-10', 'SUBMITTED'), ('LC0002', 'DS002', 'INV', '2024-06-11', 'REVIEWED');",
        "INSERT INTO infinity_transaction_domain_trans_tracking_mas (trans_id, lc_id, trans_type, trans_date, amount) VALUES ('TXN001', 'LC0001', 'PAYMENT', '2024-06-15', 50000.00), ('TXN002', 'LC0002', 'AMENDMENT', '2024-06-16', 1000.00);",
        "INSERT INTO infinity_integration_domain_swift_integration_mas (msg_id, msg_type, sender_bic, receiver_bic, lc_id) VALUES ('SWIFT001', 'MT700', 'BANKUS33XXX', 'DEUTDEFFXXX', 'LC0001'), ('SWIFT002', 'MT701', 'DEUTDEFFXXX', 'BANKUS33XXX', 'LC0002');",
        "INSERT INTO infinity_accounting_domain_fin_accounting_mas (acc_entry_id, lc_id, entry_date, debit_amount, credit_amount) VALUES ('ACC001', 'LC0001', '2024-06-20', 50000.00, 0.00), ('ACC002', 'LC0002', '2024-06-21', 0.00, 75000.00);"
    ],
    "update_sql": [
        "ALTER TABLE infinity_core_domain_lc_master_mas UPDATE applicant_name = 'Updated Applicant A Inc', beneficiary_name = 'Updated Beneficiary A Group', issuing_bank_code = 'CITIUS33', lc_amount = 55000.00, currency_code = 'GBP', issue_date = '2024-06-03', expiry_date = '2024-09-10', status = '02', goods_description = 'Updated Machinery Parts' WHERE lc_id = 'LC0001';",
        "ALTER TABLE infinity_core_domain_lc_master_mas UPDATE applicant_name = 'Updated Applicant B AG', beneficiary_name = 'Updated Beneficiary B International', issuing_bank_code = 'COMMDEFF', lc_amount = 80000.00, currency_code = 'CHF', issue_date = '2024-06-04', expiry_date = '2024-09-20', status = '03', goods_description = 'Updated Medical Devices' WHERE lc_id = 'LC0002';",
        "ALTER TABLE infinity_compliance_domain_doc_compliance_mas UPDATE doc_type = 'PACKING_LIST', submission_date = '2024-06-12', compliance_status = 'APPROVED' WHERE lc_id = 'LC0001' AND doc_set_id = 'DS001';",
        "ALTER TABLE infinity_compliance_domain_doc_compliance_mas UPDATE doc_type = 'CERT_OF_ORIGIN', submission_date = '2024-06-13', compliance_status = 'REJECTED' WHERE lc_id = 'LC0002' AND doc_set_id = 'DS002';",
        "ALTER TABLE infinity_transaction_domain_trans_tracking_mas UPDATE trans_type = 'FEE', trans_date = '2024-06-17', amount = 150.00 WHERE trans_id = 'TXN001';",
        "ALTER TABLE infinity_transaction_domain_trans_tracking_mas UPDATE trans_type = 'ADJUSTMENT', trans_date = '2024-06-18', amount = -500.00 WHERE trans_id = 'TXN002';",
        "ALTER TABLE infinity_integration_domain_swift_integration_mas UPDATE msg_type = 'MT730', sender_bic = 'UBSWCHZHXXX', receiver_bic = 'HSBCHKHHXXX' WHERE msg_id = 'SWIFT001';",
        "ALTER TABLE infinity_integration_domain_swift_integration_mas UPDATE msg_type = 'MT732', sender_bic = 'BNPAFRPPXXX', receiver_bic = 'SCBLUS33XXX' WHERE msg_id = 'SWIFT002';",
        "ALTER TABLE infinity_accounting_domain_fin_accounting_mas UPDATE entry_date = '2024-06-22', debit_amount = 10000.00, credit_amount = 0.00 WHERE acc_entry_id = 'ACC001';",
        "ALTER TABLE infinity_accounting_domain_fin_accounting_mas UPDATE entry_date = '2024-06-23', debit_amount = 0.00, credit_amount = 5000.00 WHERE acc_entry_id = 'ACC002';"
    ]
}"""

    # UML2testdata
    schema2SQL_MOCKED_AI_ANSWER = """{
    "sql": "SELECT 
        infinity_core_domain_lc_master_mas.lc_id AS infinity_core_domain_lc_master_mas__lc_id,
        infinity_core_domain_lc_master_mas.applicant_name AS infinity_core_domain_lc_master_mas__applicant_name,
        infinity_core_domain_lc_master_mas.beneficiary_name AS infinity_core_domain_lc_master_mas__beneficiary_name,
        infinity_core_domain_lc_master_mas.issuing_bank_code AS infinity_core_domain_lc_master_mas__issuing_bank_code,
        infinity_core_domain_lc_master_mas.lc_amount AS infinity_core_domain_lc_master_mas__lc_amount,
        infinity_core_domain_lc_master_mas.currency_code AS infinity_core_domain_lc_master_mas__currency_code,
        infinity_core_domain_lc_master_mas.issue_date AS infinity_core_domain_lc_master_mas__issue_date,
        infinity_core_domain_lc_master_mas.expiry_date AS infinity_core_domain_lc_master_mas__expiry_date,
        infinity_core_domain_lc_master_mas.status AS infinity_core_domain_lc_master_mas__status,
        infinity_core_domain_lc_master_mas.goods_description AS infinity_core_domain_lc_master_mas__goods_description
    FROM 
        infinity_core_domain_lc_master_mas
    WHERE 
        infinity_core_domain_lc_master_mas.currency_code = 'CHF';",
    "explanation_in_Mandarin": "查询信用证主数据中货币代码为EUR的记录，返回所有相关字段。",
    "explanation_in_English": "Query the master data of Letters of Credit where the currency code is EUR, returning all relevant fields.",
    "isPlotRequired": "no",
    "plotRequirement": {
        "plotType": "lineChart",
        "PlotX": "",
        "PlotY": "",
        "PlotTitle": "",
        "xlabel": "",
        "ylabel": ""
    },
    "isLinearRegressionRequired": "no",
    "linearRequirement": {
        "plotType": "lineChart",
        "xColumns": "",
        "yColumn": "",
        "PlotXColumn": "",
        "PlotTitle": "",
        "xlabel": "",
        "ylabel": "",
        "if_run_test": "false",
        "X_given_test_source_path": ""
    },
    "isMonteCarloRequired": "no",
    "MonteCarloRequirement": {
        "market":"", 
        "stock":"",
        "start_date": "",
        "end_date":"",
        "init_value": "",
        "analysis_column": "",
        "t": 0.01,
        "times": 10,
        "series": 1000,
        "alpha": 0.05,
        "distribution_type": "lognormal"
    },
    "feedback": ""
}"""
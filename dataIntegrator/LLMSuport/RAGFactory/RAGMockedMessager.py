import os

class RAGMockedMessager():

    # txt2req
    txt2req_MOCKED_AI_ANSWER = """# Trade Finance System Business Table Requirements

        Abstract
        
        
        
        This requirement defines business tables for a trade finance system, covering core LC master data, compliance, tracking, SWIFT integration, and financial accounting, to support efficient trade operations.
        
        
        Section 1 The data model of LC business
        
        
        
        Using the snowflake model, the data tables are divided into the following data domains:
        
        
        
        
        | No&#xA; | Table Name&#xA;                     | Table Description&#xA;                                                                                                                     |
        | ------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
        | 1&#xA;  | core\_finance\_lc\_master\_mas&#xA; | Holds the master data for Letters of Credit, including 20 columns with key information about LC transactions.&#xA;                         |
        | 2&#xA;  | compliance\_documentary\_mas&#xA;   | Manages documentary compliance data for LC operations, consisting of 10 columns to ensure regulatory and contractual adherence.&#xA;       |
        | 3&#xA;  | tracking\_transaction\_mas&#xA;     | Records transaction tracking details, with 10 columns to monitor the lifecycle of LC - related transactions.&#xA;                          |
        | 4&#xA;  | integration\_swift\_mas&#xA;        | Handles data for SWIFT integration, having 10 columns to facilitate communication and data exchange with SWIFT systems.&#xA;               |
        | 5&#xA;  | accounting\_financial\_mas&#xA;     | Stores financial accounting data for LC - related financial activities, with 10 columns for financial record - keeping and reporting.&#xA; |
        
        Section 2 The detail table information
        
        
        
        ### Table Name: core\_finance\_lc\_master\_mas&#xA;
        
        
        
        | No&#xA; | Short Name&#xA;                 | Long Name&#xA;                         | Description&#xA;                                                                                                                                                                                                                                                 | Data Type&#xA; | Length&#xA; | Mandatory&#xA; | Default Value&#xA;                      | Validation Rules&#xA;                       |
        | ------- | ------------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ----------- | -------------- | --------------------------------------- | ------------------------------------------- |
        | 1&#xA;  | lc\_id&#xA;                     | Letter of Credit Identifier&#xA;       | A unique identifier for each LC&#xA;                                                                                                                                                                                                                             | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | Auto - generate&#xA;                    | Unique&#xA;                                 |
        | 2&#xA;  | lc\_ref\_num&#xA;               | Letter of Credit Reference Number&#xA; | A reference number for the LC used for internal and external communication&#xA;                                                                                                                                                                                  | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | ""&#xA;                                 | Valid format&#xA;                           |
        | 3&#xA;  | applicant&#xA;                  | LC Applicant&#xA;                      | The party applying for the LC&#xA;                                                                                                                                                                                                                               | VARCHAR&#xA;   | 100&#xA;    | Yes&#xA;       | ""&#xA;                                 | Valid entity name&#xA;                      |
        | 4&#xA;  | beneficiary&#xA;                | LC Beneficiary&#xA;                    | The party to be paid under the LC&#xA;                                                                                                                                                                                                                           | VARCHAR&#xA;   | 100&#xA;    | Yes&#xA;       | ""&#xA;                                 | Valid entity name&#xA;                      |
        | 5&#xA;  | issuing\_bank&#xA;              | LC Issuing Bank&#xA;                   | The bank that issues the LC&#xA;                                                                                                                                                                                                                                 | VARCHAR&#xA;   | 100&#xA;    | Yes&#xA;       | ""&#xA;                                 | Valid bank name&#xA;                        |
        | 6&#xA;  | advising\_bank&#xA;             | LC Advising Bank&#xA;                  | The bank that advises the LC to the beneficiary&#xA;                                                                                                                                                                                                             | VARCHAR&#xA;   | 100&#xA;    | No&#xA;        | ""&#xA;                                 | Valid bank name&#xA;                        |
        | 7&#xA;  | amount&#xA;                     | LC Amount&#xA;                         | The total amount of the LC&#xA;                                                                                                                                                                                                                                  | DECIMAL&#xA;   | 18,2&#xA;   | Yes&#xA;       | 0.00&#xA;                               | > 0&#xA;                                    |
        | 8&#xA;  | currency&#xA;                   | LC Currency&#xA;                       | The currency of the LC&#xA;                                                                                                                                                                                                                                      | VARCHAR&#xA;   | 3&#xA;      | Yes&#xA;       | ""&#xA;                                 | Valid ISO 4217 currency code&#xA;           |
        | 9&#xA;  | expiry\_date&#xA;               | LC Expiry Date&#xA;                    | The date when the LC expires&#xA;                                                                                                                                                                                                                                | DATE&#xA;      | -&#xA;      | Yes&#xA;       | Calculated based on business rules&#xA; | Future date&#xA;                            |
        | 10&#xA; | presentation\_period&#xA;       | LC Presentation Period&#xA;            | The period within which documents must be presented&#xA;                                                                                                                                                                                                         | INT&#xA;       | -&#xA;      | Yes&#xA;       | 0&#xA;                                  | > 0&#xA;                                    |
        | 11&#xA; | status&#xA;                     | LC Status&#xA;                         | The current status of the LC, following 00 request->01 open->02 issue->03 advice->04 negotiated -> 05 redump ->06 closed, 00 request->07 rejected, 01 request->07 rejected, 03 advice ->07 rejected, 04 negotiated ->07 rejected, 05 redumped ->07 rejected&#xA; | VARCHAR&#xA;   | 2&#xA;      | Yes&#xA;       | "00"&#xA;                               | Valid status sequence&#xA;                  |
        | 12&#xA; | goods\_description&#xA;         | Description of Goods&#xA;              | A description of the goods covered by the LC&#xA;                                                                                                                                                                                                                | VARCHAR&#xA;   | 500&#xA;    | Yes&#xA;       | ""&#xA;                                 | Valid description&#xA;                      |
        | 13&#xA; | shipment\_details&#xA;          | Shipment Details&#xA;                  | Details regarding the shipment of goods&#xA;                                                                                                                                                                                                                     | VARCHAR&#xA;   | 500&#xA;    | No&#xA;        | ""&#xA;                                 | Valid shipment information&#xA;             |
        | 14&#xA; | partial\_shipment\_allowed&#xA; | Partial Shipment Allowed&#xA;          | Indicates whether partial shipment is allowed&#xA;                                                                                                                                                                                                               | BOOLEAN&#xA;   | -&#xA;      | Yes&#xA;       | FALSE&#xA;                              | Valid boolean value&#xA;                    |
        | 15&#xA; | transshipment\_allowed&#xA;     | Transshipment Allowed&#xA;             | Indicates whether transshipment is allowed&#xA;                                                                                                                                                                                                                  | BOOLEAN&#xA;   | -&#xA;      | Yes&#xA;       | FALSE&#xA;                              | Valid boolean value&#xA;                    |
        | 16&#xA; | latest\_shipment\_date&#xA;     | Latest Shipment Date&#xA;              | The latest date for shipment&#xA;                                                                                                                                                                                                                                | DATE&#xA;      | -&#xA;      | Yes&#xA;       | Calculated based on business rules&#xA; | Future date, earlier than expiry\_date&#xA; |
        | 17&#xA; | documents\_required&#xA;        | Documents Required&#xA;                | A list of documents required for payment under the LC&#xA;                                                                                                                                                                                                       | VARCHAR&#xA;   | 1000&#xA;   | Yes&#xA;       | ""&#xA;                                 | Valid document list&#xA;                    |
        | 18&#xA; | additional\_conditions&#xA;     | Additional Conditions&#xA;             | Any additional conditions of the LC&#xA;                                                                                                                                                                                                                         | VARCHAR&#xA;   | 1000&#xA;   | No&#xA;        | ""&#xA;                                 | Valid conditions&#xA;                       |
        | 19&#xA; | amendment\_history&#xA;         | LC Amendment History&#xA;              | Records of any amendments made to the LC&#xA;                                                                                                                                                                                                                    | VARCHAR&#xA;   | 2000&#xA;   | No&#xA;        | ""&#xA;                                 | Valid amendment records&#xA;                |
        | 20&#xA; | creation\_date&#xA;             | LC Creation Date&#xA;                  | The date when the LC was created&#xA;                                                                                                                                                                                                                            | DATE&#xA;      | -&#xA;      | Yes&#xA;       | CURRENT\_DATE&#xA;                      | Valid past date&#xA;                        |
        
        ### Table Name: compliance\_documentary\_mas&#xA;
        
        
        
        | No&#xA; | Short Name&#xA;           | Long Name&#xA;                             | Description&#xA;                                                              | Data Type&#xA; | Length&#xA; | Mandatory&#xA; | Default Value&#xA;   | Validation Rules&#xA;                             |
        | ------- | ------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------- | -------------- | ----------- | -------------- | -------------------- | ------------------------------------------------- |
        | 1&#xA;  | doc\_id&#xA;              | Document Identifier&#xA;                   | A unique identifier for each compliance document&#xA;                         | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | Auto - generate&#xA; | Unique&#xA;                                       |
        | 2&#xA;  | lc\_id\_ref&#xA;          | Letter of Credit Identifier Reference&#xA; | References the related LC&#xA;                                                | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | ""&#xA;              | Valid existing lc\_id&#xA;                        |
        | 3&#xA;  | doc\_type&#xA;            | Document Type&#xA;                         | The type of the compliance document (e.g., Bill of Lading, Invoice)&#xA;      | VARCHAR&#xA;   | 50&#xA;     | Yes&#xA;       | ""&#xA;              | Valid document type list&#xA;                     |
        | 4&#xA;  | doc\_status&#xA;          | Document Status&#xA;                       | The current status of the document (e.g., Submitted, Reviewed, Approved)&#xA; | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | "Submitted"&#xA;     | Valid status list&#xA;                            |
        | 5&#xA;  | submission\_date&#xA;     | Document Submission Date&#xA;              | The date when the document was submitted&#xA;                                 | DATE&#xA;      | -&#xA;      | Yes&#xA;       | CURRENT\_DATE&#xA;   | Valid past date&#xA;                              |
        | 6&#xA;  | review\_date&#xA;         | Document Review Date&#xA;                  | The date when the document was reviewed&#xA;                                  | DATE&#xA;      | -&#xA;      | No&#xA;        | ""&#xA;              | Valid past date, later than submission\_date&#xA; |
        | 7&#xA;  | approval\_date&#xA;       | Document Approval Date&#xA;                | The date when the document was approved&#xA;                                  | DATE&#xA;      | -&#xA;      | No&#xA;        | ""&#xA;              | Valid past date, later than review\_date&#xA;     |
        | 8&#xA;  | reviewer&#xA;             | Document Reviewer&#xA;                     | The person who reviewed the document&#xA;                                     | VARCHAR&#xA;   | 100&#xA;    | No&#xA;        | ""&#xA;              | Valid user name&#xA;                              |
        | 9&#xA;  | approver&#xA;             | Document Approver&#xA;                     | The person who approved the document&#xA;                                     | VARCHAR&#xA;   | 100&#xA;    | No&#xA;        | ""&#xA;              | Valid user name&#xA;                              |
        | 10&#xA; | compliance\_comments&#xA; | Compliance Comments&#xA;                   | Any comments regarding the compliance of the document&#xA;                    | VARCHAR&#xA;   | 500&#xA;    | No&#xA;        | ""&#xA;              | Valid comment text&#xA;                           |
        
        ### Table Name: tracking\_transaction\_mas&#xA;
        
        
        
        | No&#xA; | Short Name&#xA;     | Long Name&#xA;                             | Description&#xA;                                                                | Data Type&#xA; | Length&#xA; | Mandatory&#xA; | Default Value&#xA;   | Validation Rules&#xA;            |
        | ------- | ------------------- | ------------------------------------------ | ------------------------------------------------------------------------------- | -------------- | ----------- | -------------- | -------------------- | -------------------------------- |
        | 1&#xA;  | trans\_id&#xA;      | Transaction Identifier&#xA;                | A unique identifier for each transaction&#xA;                                   | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | Auto - generate&#xA; | Unique&#xA;                      |
        | 2&#xA;  | lc\_id\_ref&#xA;    | Letter of Credit Identifier Reference&#xA; | References the related LC&#xA;                                                  | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | ""&#xA;              | Valid existing lc\_id&#xA;       |
        | 3&#xA;  | trans\_type&#xA;    | Transaction Type&#xA;                      | The type of the transaction (e.g., Payment, Amendment, Fee)&#xA;                | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | ""&#xA;              | Valid transaction type list&#xA; |
        | 4&#xA;  | trans\_date&#xA;    | Transaction Date&#xA;                      | The date when the transaction occurred&#xA;                                     | DATE&#xA;      | -&#xA;      | Yes&#xA;       | CURRENT\_DATE&#xA;   | Valid past date&#xA;             |
        | 5&#xA;  | amount&#xA;         | Transaction Amount&#xA;                    | The monetary value of the transaction&#xA;                                      | DECIMAL&#xA;   | 18,2&#xA;   | Yes&#xA;       | 0.00&#xA;            | != 0&#xA;                        |
        | 6&#xA;  | sender&#xA;         | Transaction Sender&#xA;                    | The party initiating the transaction&#xA;                                       | VARCHAR&#xA;   | 100&#xA;    | Yes&#xA;       | ""&#xA;              | Valid entity name&#xA;           |
        | 7&#xA;  | receiver&#xA;       | Transaction Receiver&#xA;                  | The party receiving the transaction&#xA;                                        | VARCHAR&#xA;   | 100&#xA;    | Yes&#xA;       | ""&#xA;              | Valid entity name&#xA;           |
        | 8&#xA;  | trans\_status&#xA;  | Transaction Status&#xA;                    | The current status of the transaction (e.g., Pending, Completed, Rejected)&#xA; | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | "Pending"&#xA;       | Valid status list&#xA;           |
        | 9&#xA;  | reference\_num&#xA; | Transaction Reference Number&#xA;          | A reference number for the transaction&#xA;                                     | VARCHAR&#xA;   | 20&#xA;     | No&#xA;        | ""&#xA;              | Valid format&#xA;                |
        | 10&#xA; | remarks&#xA;        | Transaction Remarks&#xA;                   | Any remarks related to the transaction&#xA;                                     | VARCHAR&#xA;   | 500&#xA;    | No&#xA;        | ""&#xA;              | Valid comment text&#xA;          |
        
        ### Table Name: integration\_swift\_mas&#xA;
        
        
        
        | No&#xA; | Short Name&#xA;     | Long Name&#xA;                             | Description&#xA;                                                                  | Data Type&#xA; | Length&#xA; | Mandatory&#xA; | Default Value&#xA;   | Validation Rules&#xA;                |
        | ------- | ------------------- | ------------------------------------------ | --------------------------------------------------------------------------------- | -------------- | ----------- | -------------- | -------------------- | ------------------------------------ |
        | 1&#xA;  | swift\_msg\_id&#xA; | SWIFT Message Identifier&#xA;              | A unique identifier for each SWIFT message&#xA;                                   | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | Auto - generate&#xA; | Unique&#xA;                          |
        | 2&#xA;  | lc\_id\_ref&#xA;    | Letter of Credit Identifier Reference&#xA; | References the related LC&#xA;                                                    | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | ""&#xA;              | Valid existing lc\_id&#xA;           |
        | 3&#xA;  | msg\_type&#xA;      | SWIFT Message Type&#xA;                    | The type of the SWIFT message (e.g., 700, 701)&#xA;                               | VARCHAR&#xA;   | 3&#xA;      | Yes&#xA;       | ""&#xA;              | Valid SWIFT message type list&#xA;   |
        | 4&#xA;  | sender\_bic&#xA;    | Sender Bank Identifier Code&#xA;           | The BIC of the sender bank&#xA;                                                   | VARCHAR&#xA;   | 11&#xA;     | Yes&#xA;       | ""&#xA;              | Valid BIC format&#xA;                |
        | 5&#xA;  | receiver\_bic&#xA;  | Receiver Bank Identifier Code&#xA;         | The BIC of the receiver bank&#xA;                                                 | VARCHAR&#xA;   | 11&#xA;     | Yes&#xA;       | ""&#xA;              | Valid BIC format&#xA;                |
        | 6&#xA;  | msg\_date&#xA;      | SWIFT Message Date&#xA;                    | The date when the SWIFT message was sent&#xA;                                     | DATE&#xA;      | -&#xA;      | Yes&#xA;       | CURRENT\_DATE&#xA;   | Valid past date&#xA;                 |
        | 7&#xA;  | msg\_text&#xA;      | SWIFT Message Text&#xA;                    | The content of the SWIFT message&#xA;                                             | VARCHAR&#xA;   | 5000&#xA;   | Yes&#xA;       | ""&#xA;              | Valid SWIFT message text format&#xA; |
        | 8&#xA;  | status&#xA;         | SWIFT Message Status&#xA;                  | The current status of the SWIFT message (e.g., Sent, Received, Acknowledged)&#xA; | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | "Sent"&#xA;          | Valid status list&#xA;               |
        | 9&#xA;  | seq\_num&#xA;       | SWIFT Message Sequence Number&#xA;         | The sequence number of the SWIFT message within a conversation&#xA;               | INT&#xA;       | -&#xA;      | No&#xA;        | 0&#xA;               | > 0&#xA;                             |
        | 10&#xA; | error\_code&#xA;    | SWIFT Message Error Code&#xA;              | Any error code associated with the SWIFT message&#xA;                             | VARCHAR&#xA;   | 20&#xA;     | No&#xA;        | ""&#xA;              | Valid error code list&#xA;           |
        
        ### Table Name: accounting\_financial\_mas&#xA;
        
        
        
        | No&#xA; | Short Name&#xA;      | Long Name&#xA;                             | Description&#xA;                                                              | Data Type&#xA; | Length&#xA; | Mandatory&#xA; | Default Value&#xA;   | Validation Rules&#xA;             |
        | ------- | -------------------- | ------------------------------------------ | ----------------------------------------------------------------------------- | -------------- | ----------- | -------------- | -------------------- | --------------------------------- |
        | 1&#xA;  | acc\_trans\_id&#xA;  | Accounting Transaction Identifier&#xA;     | A unique identifier for each accounting transaction&#xA;                      | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | Auto - generate&#xA; | Unique&#xA;                       |
        | 2&#xA;  | lc\_id\_ref&#xA;     | Letter of Credit Identifier Reference&#xA; | References the related LC&#xA;                                                | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | ""&#xA;              | Valid existing lc\_id&#xA;        |
        | 3&#xA;  | acc\_type&#xA;       | Accounting Type&#xA;                       | The type of the accounting transaction (e.g., Debit, Credit)&#xA;             | VARCHAR&#xA;   | 10&#xA;     | Yes&#xA;       | ""&#xA;              | Valid accounting type list&#xA;   |
        | 4&#xA;  | acc\_date&#xA;       | Accounting Date&#xA;                       | The date when the accounting transaction occurred&#xA;                        | DATE&#xA;      | -&#xA;      | Yes&#xA;       | CURRENT\_DATE&#xA;   | Valid past date&#xA;              |
        | 5&#xA;  | amount&#xA;          | Accounting Amount&#xA;                     | The monetary value of the accounting transaction&#xA;                         | DECIMAL&#xA;   | 18,2&#xA;   | Yes&#xA;       | 0.00&#xA;            | != 0&#xA;                         |
        | 6&#xA;  | account\_num&#xA;    | Account Number&#xA;                        | The account number related to the transaction&#xA;                            | VARCHAR&#xA;   | 30&#xA;     | Yes&#xA;       | ""&#xA;              | Valid account number format&#xA;  |
        | 7&#xA;  | description&#xA;     | Accounting Description&#xA;                | A description of the accounting transaction&#xA;                              | VARCHAR&#xA;   | 500&#xA;    | Yes&#xA;       | ""&#xA;              | Valid description&#xA;            |
        | 8&#xA;  | cost\_center&#xA;    | Cost Center&#xA;                           | The cost center associated with the transaction&#xA;                          | VARCHAR&#xA;   | 50&#xA;     | No&#xA;        | ""&#xA;              | Valid cost center code&#xA;       |
        | 9&#xA;  | currency&#xA;        | Accounting Currency&#xA;                   | The currency of the accounting transaction&#xA;                               | VARCHAR&#xA;   | 3&#xA;      | Yes&#xA;       | ""&#xA;              | Valid ISO 4217 currency code&#xA; |
        | 10&#xA; | posting\_status&#xA; | Accounting Posting Status&#xA;             | The posting status of the accounting transaction (e.g., Posted, Pending)&#xA; | VARCHAR&#xA;   | 20&#xA;     | Yes&#xA;       | "Pending"&#xA;       | Valid status list&#xA;            |
        
        
        Section 3 default values of each column
        
        
        
        ### Table Name: core\_finance\_lc\_master\_mas&#xA;
        
        
        
        | Short Name&#xA;                 | Default Value&#xA;                      | Description&#xA;                                              | SWIFT 700 Mapping&#xA;                                                    |
        | ------------------------------- | --------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------- |
        | lc\_id&#xA;                     | Auto - generate&#xA;                    | Automatically generated unique LC identifier&#xA;             | No a SWIFT mapped field&#xA;                                              |
        | lc\_ref\_num&#xA;               | ""&#xA;                                 | Empty string as placeholder until assigned&#xA;               | No a SWIFT mapped field&#xA;                                              |
        | applicant&#xA;                  | ""&#xA;                                 | Empty string until the applicant information is provided&#xA; | Mapped to field '50a/50b/50c/50d' in SWIFT 700, format: entity name&#xA;  |
        | beneficiary&#xA;                | ""&#xA;                                 | Empty string until the beneficiary details are filled&#xA;    | Mapped to field '59' in SWIFT 700, format: entity name&#xA;               |
        | issuing\_bank&#xA;              | ""&#xA;                                 | Empty string before bank details are input&#xA;               | Mapped to field '52a/52b/52c' in SWIFT 700, format: bank name&#xA;        |
        | advising\_bank&#xA;             | ""&#xA;                                 | Empty string if not applicable&#xA;                           | Mapped to field '57a/57b/57c/57d' in SWIFT 700, format: bank name&#xA;    |
        | amount&#xA;                     | 0.00&#xA;                               | Represents initial amount value&#xA;                          | Mapped to field '32B' in SWIFT 700, format: currency code + amount&#xA;   |
        | currency&#xA;                   | ""&#xA;                                 | Empty string until currency is specified&#xA;                 | Mapped to field '32B' in SWIFT 700, format: ISO 4217 currency code&#xA;   |
        | expiry\_date&#xA;               | Calculated based on business rules&#xA; | Determined by internal business logic&#xA;                    | Mapped to field '31D' in SWIFT 700, format: date&#xA;                     |
        | presentation\_period&#xA;       | 0&#xA;                                  | Initial value indicating no period set yet&#xA;               | No a SWIFT mapped field&#xA;                                              |
        | status&#xA;                     | "00"&#xA;                               | Initial status as 'request'&#xA;                              | No a SWIFT mapped field&#xA;                                              |
        | goods\_description&#xA;         | ""&#xA;                                 | Empty string until goods details are added&#xA;               | Mapped to field '45A/45B/45C' in SWIFT 700, format: text description&#xA; |
        | shipment\_details&#xA;          | ""&#xA;                                 | Empty string if no shipment details available&#xA;            | Mapped to field '44A/44B/44C/44D' in SWIFT 700, format: text details&#xA; |
        | partial\_shipment\_allowed&#xA; | FALSE&#xA;                              | Defaults to not allowing partial shipment&#xA;                | No a SWIFT mapped field&#xA;                                              |
        | transshipment\_allowed&#xA;     | FALSE&#xA;                              | Defaults to not allowing transshipment&#xA;                   | No a SWIFT mapped field&#xA;                                              |
        | latest\_shipment\_date&#xA;     | Calculated based on business rules&#xA; | Set according to business rules&#xA;                          | Mapped to field '44C/44D' in SWIFT 700, format: date&#xA;                 |
        | documents\_required&#xA;        | ""&#xA;                                 | Empty string until document list is defined&#xA;              | Mapped to field '46A/46B' in SWIFT 700, format: text list&#xA;            |
        | additional\_conditions&#xA;     | ""&#xA;                                 | Empty string if no additional conditions&#xA;                 | Mapped to field '47A/47B' in SWIFT 700, format: text conditions&#xA;      |
        | amendment\_history&#xA;         | ""&#xA;                                 | Empty string until amendments occur&#xA;                      | No a SWIFT mapped field&#xA;                                              |
        | creation\_date&#xA;             | CURRENT\_DATE&#xA;                      | Date of LC creation&#xA;                                      | Mapped to field '31C' in SWIFT 700, format: date&#xA;                     |
        
        ### Table Name: compliance\_documentary\_mas&#xA;
        
        
        
        | Short Name&#xA;           | Default Value&#xA;   | Description&#xA;                                   | SWIFT 700 Mapping&#xA;       |
        | ------------------------- | -------------------- | -------------------------------------------------- | ---------------------------- |
        | doc\_id&#xA;              | Auto - generate&#xA; | Automatically generated document ID&#xA;           | No a SWIFT mapped field&#xA; |
        | lc\_id\_ref&#xA;          | ""&#xA;              | Empty string until related LC is assigned&#xA;     | No a SWIFT mapped field&#xA; |
        | doc\_type&#xA;            | ""&#xA;              | Empty string until document type is specified&#xA; | No a SWIFT mapped field&#xA; |
        | doc\_status&#xA;          | "Submitted"&#xA;     | Default status when document is first entered&#xA; | No a SWIFT mapped field&#xA; |
        | submission\_date&#xA;     | CURRENT\_DATE&#xA;   | Date of document submission&#xA;                   | No a SWIFT mapped field&#xA; |
        | review\_date&#xA;         | ""&#xA;              | Empty string until review occurs&#xA;              | No a SWIFT mapped field&#xA; |
        | approval\_date&#xA;       | ""&#xA;              | Empty string until approval happens&#xA;           | No a SWIFT mapped field&#xA; |
        | reviewer&#xA;             | ""&#xA;              | Empty string until reviewer is assigned&#xA;       | No a SWIFT mapped field&#xA; |
        | approver&#xA;             | ""&#xA;              | Empty string until approver is determined&#xA;     | No a SWIFT mapped field&#xA; |
        | compliance\_comments&#xA; | ""&#xA;              | Empty string if no comments&#xA;                   | No a SWIFT mapped field&#xA; |
        
        ### Table Name: tracking\_transaction\_mas&#xA;
        
        
        
        | Short Name&#xA;     | Default Value&#xA;   | Description&#xA;                                       | SWIFT 700 Mapping&#xA;       |
        | ------------------- | -------------------- | ------------------------------------------------------ | ---------------------------- |
        | trans\_id&#xA;      | Auto - generate&#xA; | Automatically generated transaction ID&#xA;            | No a SWIFT mapped field&#xA; |
        | lc\_id\_ref&#xA;    | ""&#xA;              | Empty string until related LC is set&#xA;              | No a SWIFT mapped field&#xA; |
        | trans\_type&#xA;    | ""&#xA;              | Empty string until transaction type is defined&#xA;    | No a SWIFT mapped field&#xA; |
        | trans\_date&#xA;    | CURRENT\_DATE&#xA;   | Date of transaction&#xA;                               | No a SWIFT mapped field&#xA; |
        | amount&#xA;         | 0.00&#xA;            | Initial amount value&#xA;                              | No a SWIFT mapped field&#xA; |
        | sender&#xA;         | ""&#xA;              | Empty string until sender information is provided&#xA; | No a SWIFT mapped field&#xA; |
        | receiver&#xA;       | ""&#xA;              | Empty string until receiver details are filled&#xA;    | No a SWIFT mapped field&#xA; |
        | trans\_status&#xA;  | "Pending"&#xA;       | Default status when transaction is initiated&#xA;      | No a SWIFT mapped field&#xA; |
        | reference\_num&#xA; | ""&#xA;              | Empty string until reference number is assigned&#xA;   | No a SWIFT mapped field&#xA; |
        | remarks&#xA;        | ""&#xA;              | Empty string if no remarks&#xA;                        | No a SWIFT mapped field&#xA; |
        
        ### Table Name: integration\_swift\_mas&#xA;
        
        
        
        | Short Name&#xA;     | Default Value&#xA;   | Description&#xA;                                      | SWIFT 700 Mapping&#xA;                                                                                                |
        | ------------------- | -------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
        | swift\_msg\_id&#xA; | Auto - generate&#xA; | Automatically generated SWIFT message ID&#xA;         | No a SWIFT mapped field&#xA;                                                                                          |
        | lc\_id\_ref&#xA;    | ""&#xA;              | Empty string until related LC is associated&#xA;      | No a SWIFT mapped field&#xA;                                                                                          |
        | msg\_type&#xA;      | ""&#xA;              | Empty string until message type is determined&#xA;    | No a SWIFT mapped field&#xA;                                                                                          |
        | sender\_bic&#xA;    | ""&#xA;              | Empty string until sender bank BIC is input&#xA;      | Mapped to field '52a/52b/52c' in SWIFT 700, format: BIC code&#xA;                                                     |
        | receiver\_bic&#xA;  | ""&#xA;              | Empty string until receiver bank BIC is provided&#xA; | Mapped to field '53a/53b/53c/54a/54b/54c/56a/56b/56c/57a/57b/57c/57d/58a/58b/58c' in SWIFT 700, format: BIC code&#xA; |
        | msg\_date&#xA;      | CURRENT\_DATE&#xA;   | Date of message sending&#xA;                          | Mapped to field '31C' in SWIFT 700, format: date&#xA;                                                                 |
        | msg\_text&#xA;      | ""&#xA;              | Empty string until message content is composed&#xA;   | Mapped to various text fields in SWIFT 700 depending on message type, format: text&#xA;                               |
        | status&#xA;         | "Sent"&#xA;          | Default status when message is first sent&#xA;        | No a SWIFT mapped field&#xA;                                                                                          |
        | seq\_num&#xA;       | 0&#xA;               | Initial sequence number&#xA;                          | No a SWIFT mapped field&#xA;                                                                                          |
        | error\_code&#xA;    | ""&#xA;              | Empty string if no error&#xA;                         | No a SWIFT mapped field&#xA;                                                                                          |
        
        ### Table Name: accounting\_financial\_mas&#xA;
        
        
        
        | Short Name&#xA;      | Default Value&#xA;   | Description&#xA;                                         | SWIFT 700 Mapping&#xA;       |
        | -------------------- | -------------------- | -------------------------------------------------------- | ---------------------------- |
        | acc\_trans\_id&#xA;  | Auto - generate&#xA; | Automatically generated accounting transaction ID&#xA;   | No a SWIFT mapped field&#xA; |
        | lc\_id\_ref&#xA;     | ""&#xA;              | Empty string until related LC is linked&#xA;             | No a SWIFT mapped field&#xA; |
        | acc\_type&#xA;       | ""&#xA;              | Empty string until accounting type is specified&#xA;     | No a SWIFT mapped field&#xA; |
        | acc\_date&#xA;       | CURRENT\_DATE&#xA;   | Date of accounting transaction&#xA;                      | No a SWIFT mapped field&#xA; |
        | amount&#xA;          | 0.00&#xA;            | Initial accounting amount&#xA;                           | No a SWIFT mapped field&#xA; |
        | account\_num&#xA;    | ""&#xA;              | Empty string until account number is entered&#xA;        | No a SWIFT mapped field&#xA; |
        | description&#xA;     | ""&#xA;              | Empty string until transaction description is added&#xA; | No a SWIFT mapped field&#xA; |
        | cost\_center&#xA;    | ""&#xA;              | Empty string if no cost center assigned&#xA;             | No a SWIFT mapped field&#xA; |
        | currency&#xA;        | ""&#xA;              | Empty string until currency is defined&#xA;              | No a SWIFT mapped field&#xA; |
        | posting\_status&#xA; | "Pending"&#xA;       | Default status when transaction is first recorded&#xA;   | No a SWIFT mapped field&#xA; |
        
        Section 4 validation rules
        
        
        
        ### Table Name: core\_finance\_lc\_master\_mas&#xA;
        
        
        
        | Column Name&#xA;                | Validate rule&#xA;                                       | Warning message&#xA;                                                                                             |
        | ------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
        | lc\_id&#xA;                     | Must be unique across all LCs&#xA;                       | "LC ID already exists. Please use a unique identifier."&#xA;                                                     |
        | lc\_ref\_num&#xA;               | Must follow the defined format&#xA;                      | "Invalid LC reference number format. Please check and re - enter."&#xA;                                          |
        | applicant&#xA;                  | Must be a valid entity name&#xA;                         | "Invalid applicant name. Please enter a valid entity name."&#xA;                                                 |
        | beneficiary&#xA;                | Must be a valid entity name&#xA;                         | "Invalid beneficiary name. Please enter a valid entity name."&#xA;                                               |
        | issuing\_bank&#xA;              | Must be a valid bank name&#xA;                           | "Invalid issuing bank name. Please enter a valid bank name."&#xA;                                                |
        | advising\_bank&#xA;             | If provided, must be a valid bank name&#xA;              | "Invalid advising bank name. Please enter a valid bank name or leave it blank if not applicable."&#xA;           |
        | amount&#xA;                     | Must be greater than 0&#xA;                              | "LC amount must be greater than 0. Please enter a valid amount."&#xA;                                            |
        | currency&#xA;                   | Must be a valid ISO 4217 currency code&#xA;              | "Invalid currency code. Please enter a valid ISO 4217 currency code."&#xA;                                       |
        | expiry\_date&#xA;               | Must be a future date&#xA;                               | "Expiry date must be in the future. Please enter a valid date."&#xA;                                             |
        | presentation\_period&#xA;       | Must be greater than 0&#xA;                              | "Presentation period must be greater than 0. Please enter a valid period."&#xA;                                  |
        | status&#xA;                     | Must follow the defined status sequence&#xA;             | "Invalid LC status transition. Please check the status sequence and correct it."&#xA;                            |
        | goods\_description&#xA;         | Must be a valid description&#xA;                         | "Invalid goods description. Please enter a clear and valid description."&#xA;                                    |
        | shipment\_details&#xA;          | If provided, must be valid shipment information&#xA;     | "Invalid shipment details. Please enter accurate shipment information or leave it blank if not applicable."&#xA; |
        | partial\_shipment\_allowed&#xA; | Must be a valid boolean value&#xA;                       | "Invalid value for partial shipment allowed. Please enter either TRUE or FALSE."&#xA;                            |
        | transshipment\_allowed&#xA;     | Must be a valid boolean value&#xA;                       | "Invalid value for transshipment allowed. Please enter either TRUE or FALSE."&#xA;                               |
        | latest\_shipment\_date&#xA;     | Must be a future date and earlier than expiry\_date&#xA; | "Latest shipment date must be in the future and earlier than the expiry date. Please correct the date."&#xA;     |
        | documents\_required&#xA;        | Must be a valid list of documents&#xA;                   | "Invalid document list. Please enter a valid list of required documents."&#xA;                                   |
        | additional\_conditions&#xA;     | If provided, must be valid conditions&#xA;               | "Invalid additional conditions. Please enter valid conditions or leave it blank if not applicable."&#xA;         |
        | amendment\_history&#xA;         | If provided, must be valid amendment records&#xA;        | "Invalid amendment history. Please enter valid records or leave it blank if no amendments."&#xA;                 |
        | creation\_date&#xA;             | Must be a valid past date&#xA;                           | "Invalid creation date. Please enter a valid past date."&#xA;                                                    |
        
        ### Table Name: compliance\_documentary\_mas&#xA;
        
        
        
        | Column Name&#xA;          | Validate rule&#xA;                                                      | Warning message&#xA;                                                                                  |
        | ------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
        | doc\_id&#xA;              | Must be unique across all compliance documents&#xA;                     | "Document ID already exists. Please use a unique identifier."&#xA;                                    |
        | lc\_id\_ref&#xA;          | Must reference an existing LC ID&#xA;                                   | "Invalid LC reference. Please enter a valid LC ID."&#xA;                                              |
        | doc\_type&#xA;            | Must be a valid document type from the allowed list&#xA;                | "Invalid document type. Please select from the valid document type list."&#xA;                        |
        | doc\_status&#xA;          | Must be a valid status from the allowed list&#xA;                       | "Invalid document status. Please select from the valid status list."&#xA;                             |
        | submission\_date&#xA;     | Must be a valid past date&#xA;                                          | "Invalid submission date. Please enter a valid past date."&#xA;                                       |
        | review\_date&#xA;         | If provided, must be a valid past date later than submission\_date&#xA; | "Invalid review date. Review date must be later than the submission date and a valid past date."&#xA; |
        | approval\_date&#xA;       | If provided, must be a valid past date later than review\_date&#xA;     | "Invalid approval date. Approval date must be later than the review date and a valid past date."&#xA; |
        | reviewer&#xA;             | If provided, must be a valid user name&#xA;                             | "Invalid reviewer name. Please enter a valid user name or leave it blank if not applicable."&#xA;     |
        | approver&#xA;             | If provided, must be a valid user name&#xA;                             | "Invalid approver name. Please enter a valid user name or leave it blank if not applicable."&#xA;     |
        | compliance\_comments&#xA; | If provided, must be valid comment text&#xA;                            | "Invalid compliance comments. Please enter valid text or leave it blank if no comments."&#xA;         |
        
        ### Table Name: tracking\_transaction\_mas&#xA;
        
        
        
        | Column Name&#xA;    | Validate rule&#xA;                                          | Warning message&#xA;                                                                 |
        | ------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------ |
        | trans\_id&#xA;      | Must be unique across all transactions&#xA;                 | "Transaction ID already exists. Please use a unique identifier."&#xA;                |
        | lc\_id\_ref&#xA;    | Must reference an existing LC ID&#xA;                       | "Invalid LC reference. Please enter a valid LC ID."&#xA;                             |
        | trans\_type&#xA;    | Must be a valid transaction type from the allowed list&#xA; | "Invalid transaction type. Please select from the valid transaction type list."&#xA; |
        | trans\_date&#xA;    | Must be a valid past date&#xA;                              | "Invalid transaction date. Please enter a valid past date."&#xA;                     |
        | amount&#xA;         | Must not be equal to 0&#xA;                                 | "Transaction amount cannot be 0. Please enter a valid amount."&#xA;                  |
        | sender&#xA;         | Must be a valid entity name&#xA;                            | "Invalid sender name. Please enter a valid entity name."&#xA;                        |
        | receiver&#xA;       | Must be a valid entity name&#xA;                            | "Invalid receiver name. Please enter a valid entity name."&#xA;                      |
        | trans\_status&#xA;  | Must be a valid status from the allowed list&#xA;           | "Invalid transaction status. Please select from the valid status list."&#xA;         |
        | reference\_num&#xA; | If provided, must follow the defined format&#xA;            | "Invalid reference number format. Please check and re - enter."&#xA;                 |
        | remarks&#xA;        | If provided, must be valid comment text&#xA;                | "Invalid remarks. Please enter valid text or leave it blank if no remarks."&#xA;     |
        
        ### Table Name: integration\_swift\_mas&#xA;
        
        
        
        | Column Name&#xA;    | Validate rule&#xA;                                                      | Warning message&#xA;                                                                      |
        | ------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
        | swift\_msg\_id&#xA; | Must be unique across all SWIFT messages&#xA;                           | "SWIFT message ID already exists. Please use a unique identifier."&#xA;                   |
        | lc\_id\_ref&#xA;    | Must reference an existing LC ID&#xA;                                   | "Invalid LC reference. Please enter a valid LC ID."&#xA;                                  |
        | msg\_type&#xA;      | Must be a valid SWIFT message type from the allowed list&#xA;           | "Invalid SWIFT message type. Please select from the valid message type list."&#xA;        |
        | sender\_bic&#xA;    | Must be a valid BIC format&#xA;                                         | "Invalid sender BIC format. Please enter a valid BIC code."&#xA;                          |
        | receiver\_bic&#xA;  | Must be a valid BIC format&#xA;                                         | "Invalid receiver BIC format. Please enter a valid BIC code."&#xA;                        |
        | msg\_date&#xA;      | Must be a valid past date&#xA;                                          | "Invalid message date. Please enter a valid past date."&#xA;                              |
        | msg\_text&#xA;      | Must follow the valid SWIFT message text format based on msg\_type&#xA; | "Invalid SWIFT message text format. Please check and correct the message content."&#xA;   |
        | status&#xA;         | Must be a valid status from the allowed list&#xA;                       | "Invalid SWIFT message status. Please select from the valid status list."&#xA;            |
        | seq\_num&#xA;       | Must be greater than 0 if provided&#xA;                                 | "Invalid sequence number. Sequence number must be greater than 0 if entered."&#xA;        |
        | error\_code&#xA;    | If provided, must be a valid error code from the allowed list&#xA;      | "Invalid error code. Please enter a valid error code or leave it blank if no error."&#xA; |
        
        ### Table Name: accounting\_financial\_mas&#xA;
        
        
        
        | Column Name&#xA;     | Validate rule&#xA;                                         | Warning message&#xA;                                                                            |
        | -------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
        | acc\_trans\_id&#xA;  | Must be unique across all accounting transactions&#xA;     | "Accounting transaction ID already exists. Please use a unique identifier."&#xA;                |
        | lc\_id\_ref&#xA;     | Must reference an existing LC ID&#xA;                      | "Invalid LC reference. Please enter a valid LC ID."&#xA;                                        |
        | acc\_type&#xA;       | Must be a valid accounting type from the allowed list&#xA; | "Invalid accounting type. Please select from the valid accounting type list."&#xA;              |
        | acc\_date&#xA;       | Must be a valid past date&#xA;                             | "Invalid accounting date. Please enter a valid past date."&#xA;                                 |
        | amount&#xA;          | Must not be equal to 0&#xA;                                | "Accounting amount cannot be 0. Please enter a valid amount."&#xA;                              |
        | account\_num&#xA;    | Must follow the valid account number format&#xA;           | "Invalid account number format. Please check and re - enter."&#xA;                              |
        | description&#xA;     | Must be a valid description&#xA;                           | "Invalid accounting description. Please enter a clear and valid description."&#xA;              |
        | cost\_center&#xA;    | If provided, must be a valid cost center code&#xA;         | "Invalid cost center code. Please enter a valid code or leave it blank if not applicable."&#xA; |
        | currency&#xA;        | Must be a valid ISO 4217 currency code&#xA;                | "Invalid currency code. Please enter a valid ISO 4217 currency code."&#xA;                      |
        | posting\_status&#xA; | Must be a valid status from the allowed list&#xA;          | "Invalid posting status. Please select from the valid status list."&#xA;                        |
        
        
        
        
        Section 5 your doubts or inquiry
        
        
        
        
        
        1.  In the `core_finance_lc_master_mas` table, for the `status` column, the defined status sequences cover common transitions, but it's unclear how to handle more complex or exceptional scenarios, such as re - opening a closed LC. Are there specific business rules for these situations?
        
        
        2.  Regarding the SWIFT 700 message mapping, the mapping rules for some fields seem rather general. For example, for the `msg_text` in the `integration_swift_mas` table, it's mentioned to map to various text fields depending on the message type, but it lacks detailed mapping instructions for each specific message type. Could you provide more specific guidelines?
        
        
        3.  For the calculation of `expiry_date` and `latest_shipment_date` in the `core_finance_lc_master_mas` table, it's stated to be based on business rules, but no details about these rules are given. What factors should be considered in these calculations?
        
        
        4.  In the validation rules, for columns with text descriptions like `goods_description` and `compliance_comments`, the validation for valid content is rather vague. How can we precisely define what constitutes a valid description or comment?
        
        
        Section 6 Reference URL
        
        
        
        
        
        | No&#xA; | Reference Doc&#xA;      | Reference Site&#xA;                                                                                                                                                                                                                                          |
        | ------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
        | 1&#xA;  | UCP600&#xA;             | [https://www.cietac.org/articles/63](https://www.cietac.org/articles/63)                                                                                                                                                                                     |
        | 2&#xA;  | SWIFT 700 document&#xA; | [https://mbd.baidu.com/newspage/data/dtlandingsuper?nid=dt\_4695470141140934410\&sourceFrom=search\_a](https://mbd.baidu.com/newspage/data/dtlandingsuper?nid=dt_4695470141140934410\&sourceFrom=search_a)                                                   |
        | 3&#xA;  | ISBP 745&#xA;           | [https://www.iccwbo.org/publications-and-resources/publications/international-standard-banking-practice-isbp-for-the-ucp-600/](https://www.iccwbo.org/publications-and-resources/publications/international-standard-banking-practice-isbp-for-the-ucp-600/) |
        | 4&#xA;  | ICC Trade Register&#xA; | [https://www.iccwbo.org/our-work/trade-finance/icc-trade-register/](https://www.iccwbo.org/our-work/trade-finance/icc-trade-register/)                                                                                                                       |
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
        infinity_core_domain_lc_master_mas.currency_code = 'EUR';",
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
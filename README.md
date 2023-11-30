# XXX Chat PoC  <!-- omit in toc -->

This project is a prototype web application aiming to demonstrate that Azure OpenAI Service can offer a new form of user experience to xxx employees. The application is hosted on **Country Hosting** tenant.

- [Getting Started](#getting-started)
  - [Access to Country Hosting](#access-to-country-hosting)
    - [Initial zzzz ITS Registration](#initial-zzzz-its-registration)
    - [Accounts Managed by CyberArk](#accounts-managed-by-cyberark)
  - [Prerequisites](#prerequisites)
  - [Running the Application Locally](#running-the-application-locally)
  - [Sharing Environments](#sharing-environments)
    - [Notes](#notes)
- [Utilities](#utilities)
  - [Extract Documents from Excel to CSV](#extract-documents-from-excel-to-csv)
  - [Upload Documents to ACS](#upload-documents-to-acs)
    - [CSV Documents](#csv-documents)
    - [PDF Documents](#pdf-documents)

## Getting Started

### Access to Country Hosting

#### Initial zzzz ITS Registration

**(One time only)** Request zzzz ITS to create a user account and add them to the corresponding security group (Readers / Contributors / Owners)

1. Submit [Country Hosting Request Form](https://forms.office.com/Pages/ResponsePage.aspx?id=uyT_3okgAESMjvceaAN4srgECulSRRpNkT8reLSDZa5URU0wME8wWDc1UVpPTDFUS1gwOTBIT0MxVyQlQCN0PWcu&wdLOR=c48452761-22EC-466B-AFF2-5F7A06C3AC4E)

    - Subscription name: `JP-SUB-CH-DEV-xxx-CHAT`
    - Owners of the subscription: Bangari, Samuel (xxx) <Samuel.Bangari@jp.yyyy.com> and Izumi, Ken (xxx) <Ken.Izumi@jp.yyyy.com>
    - Request Category: `Account - JP-CLD-IIDアカウント作成・削除申請`
    - Name of the security group: `JP-SG CH Contributors xxx Chat`
    - For question #4, e-mail addresses of prospective users and their security group name should be entered
    - Question #6 (申請に必要な申請書/メールを添付してください。) could be left unanswered

1. Since this step requires zzzz ITS to talk to Global ITS, it might take as much as 2~3 weeks.
1. If zzzz ITS has any CyberArk licenses left, the department assigns some to prospective users at the time of account creation. If no CyberArk liceses are left, zzzz ITS sends emails to prospective users with initial passwords.

#### Accounts Managed by CyberArk

1. **(One time only)** After the account is created, zzzz ITS sends a mail with further instructions, which need to be followed for activating the accounts. ![Activating CyberArk accounts](docs/cyberark1.png)

    1. Instructions contain a list of videos that the prospective users should watch (①~③).
    1. In the end, the users should fill up a form and send it to zzzz ITS (④~⑥).
    1. Once the form is submitted, zzzz ITS activates the account and the users can login to CyberArk and Azure Portal.

1. **(Every day)** Typical login flow for obtaining `jp-cld-{your name}` passwords is as follows. Please note that as the passwords stored in CyberArk change on a daily basis, we need to repeat this process every day.

    1. Login to [CyberArk](https://cyberark-tokyo.jp.kworld.yyyy.com/PasswordVault) by using the same login credentials as F5 VPN, i.e., `Mac username` and `passphrase + RSA token`.
    1. Show the password. ![Activating CyberArk accounts](docs/cyberark2.png)
    1. Copy the password.
    1. Login to Azure Portal using a different browser.

        - As Azure sign-in info is usually preserved in Edge and generally stores Cloud Next info, use of Chrome is recommended.
        - During the first login, Azure presents the Multi Factor Authentication (MFA) registration flow. Use this to register your company iPhone's authenticator app for MFA.

### Prerequisites

- [Azure Developer CLI](https://aka.ms/azure-dev/install)
- [Python 3+](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/en/download/)
- [Git](https://git-scm.com/downloads)
- Zscaler Root Certificate

    1. Launch the `Keychain Access` application
    1. Click on the `System` tab from the left column
    1. Click on the `Certificates` tab from the top header
    1. Select `Zscaler Root CA`
    1. Right click and name the file as `zscaler_root_ca.pem`
    1. Save `zscaler_root_ca.pem` to local
    1. Move `zscaler_root_ca.pem` to the root directory of the project

    ![Extraction of zscaler_root_ca.pem](docs/zscaler.png)

### Running the Application Locally

Note that Azure resources MUST BE already provisioned to run the application locally.

1. Run `azd auth login --use-device-code`.
1. Run `cd app`.
1. Launch the app.

    - **(First time only)** `./start.sh --install-packages`.
    - **(2nd time onwards)** `./start.sh`

1. Access the app at [http://127.0.0.1:5000](http://127.0.0.1:5000).

### Sharing Environments

To give someone else access to a completely deployed and existing environment, either you or they can follow these steps:

1. Install the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
1. Clone this repository
1. Run `azd env refresh -e {environment name}`

    They will need the (i) **azd environment name**, (ii) **subscription ID**, and (iii) **location** to run this command. You can find those values in your `.azure/{env name}/.env` file.  This will populate their azd environment's `.env` file with all the settings needed to run the app locally.

1. Confirm Azure ID, or **Object ID**, of intended users by accessing [Azure Web Portal](https://portal.azure.com/) > Azure Active Directory > Users > Search > Object ID

    ![How to confirm user Object IDs (1)](docs/role-assignment-01.png)
    ![How to confirm user Object IDs (2)](docs/role-assignment-02.png)

1. Set the environment variable `AZURE_PRINCIPAL_ID` either in `.azure/{env name}/.env` file or in the active shell to their Azure ID, which should be confirmed in the previous step.
1. Run `.scripts/roles.sh` to assign all of the necessary roles to the user.  If they do not have the necessary permission to create roles in the subscription, then you may need to run this script for them. Once the script runs, they should be able to run the app locally.

#### Notes

1. `.scripts/roles.sh` assigns the following Azure built-in roles, whose details can be found [here](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles).

    | # | ID                                     | Target Azure Service   | Role Name                      | Role Details                                                                                                                                                                            |
    |--:|----------------------------------------|:-----------------------|:-------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | 1 | `5e0bd9bd-7b93-4f28-af87-19fc36ad61bd` | Azure Open AI          | Cognitive Services OpenAI User | Read access to view files, models, deployments. The ability to create completion and embedding calls                                                                                    |
    | 2 | `2a2b9908-6ea1-4ae2-8e65-a410df84e7d1` | Azure Blob Storage     | Storage Blob Data Reader       | Read and list Azure Storage containers and blobs. To learn which actions are required for a given data operation, see Permissions for calling blob and queue data operations.           |
    | 3 | `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | Azure Blob Storage     | Storage Blob Data Contributor  | Read, write, and delete Azure Storage containers and blobs. To learn which actions are required for a given data operation, see Permissions for calling blob and queue data operations. |
    | 4 | `1407120a-92aa-4202-b7e9-c0e197c71c8f` | Azure Cognitive Search | Search Index Data Reader       | Grants read access to Azure Cognitive Search index data.                                                                                                                                |
    | 5 | `8ebe5a00-799e-43f5-93ac-243d3dce84a7` | Azure Cognitive Search | Search Index Data Contributor  | Grants full access to Azure Cognitive Search index data.                                                                                                                                |

1. Azure ID of intended users can be comfirmed from command line by executing the following.

    ```bash
    az ad user list --filter "mail eq '{USER_EMAIL_ADDRESS}'" --query "[].id" -o tsv
    ```

### Provisioning and Deploy

1. Provision the resources by running `azd provision`
2. Create the index based on instructions in [Data Ingestion Guide](docs/xxxchat_data_ingestion.md).
3. Deploy the app by running `azd deploy`

## Utilities

### Extract Documents from Excel to CSV

The documents used in this project are provided in an Excel file. Use the instructions in this section to export those documents in CSV files.

1. Create a local copy of [Reference Knowledges.xlsx](https://spo-global.yyyy.com/:x:/r/sites/JP-xxx_DI/Shared%20Documents/07%20-%20KOMEI/Chat%20KOMEI%20PoC/Reference%20Knowledges.xlsx?d=wd5c6d3f809ff41a2b3bb0367f6353081&csf=1&web=1&e=pQJlaw) and store it in `/data`.
1. Create a Python virtual environment and install the packages.

    ```bash
    # 1) Create a virtual environment
    python -m venv scripts/.venv
    # 2) Upgrade pip
    ./scripts/.venv/bin/python -m pip install --upgrade pip
    # 3) Install the packages
    ./scripts/.venv/bin/python -m pip install -r scripts/requirements.txt
    ```

1. Run `./scripts/.venv/bin/python ./scripts/extract_knowledge_items_from_xlsx_to_csv.py`.
1. Confirm that a CSV file is created per Excel sheet in `./data/csv` as follows:

    ```text
    data
    ├── Reference Knowledges.xlsx
    └── csv
        ├── srfi_faq.csv
        ├── insights.csv
        └── red_book.csv
    ```

    These CSV files can be uploaded to ACS. Follow the instruction here: [Upload Documents to ACS](#upload-documents-to-acs).

### Upload Documents to ACS

#### CSV Documents

For testing purpose, please set AZURE_SEARCH_INDEX in `./azure/{env-name}/.env` to be something different from the index name used by the app (e.g. `test-index`).

1. Prepare documents you want to upload in CSV files and store them in `/data/csv`.
1. Run `./scripts/prepdocs.sh csv`.

#### PDF Documents

For testing purpose, please set AZURE_SEARCH_INDEX_paagj in `./azure/{env-name}/.env` to be something different from the index name used by the app (e.g. `test-index`).

1. Prepare documents you want to upload in PDF files and store them in `/data/pdf`. You can download PDF files from [Knowledges - JGAPP](https://spo-global.yyyy.com/:f:/r/sites/JP-xxx_DI/Shared%20Documents/07%20-%20KOMEI/Chat%20KOMEI%20PoC/Knowledges%20-%20JGAPP?csf=1&web=1&e=sCx8Na).
1. Run `./scripts/prepdocs.sh pdf`. This does two things:
   1. Upload PDF files to ABS.
      1. `<pdf ID>.pdf`: Copies of PDF files under `data/pdf`.
      1. `metadata/blobnames_<smallest ID>-<largest ID>.json`: A map from pdf ID to original PDF name. This file contains the map from `<smallest ID>` to `<largest ID>`.
   1. Index ACS using the contents from the PDF documents.

## Appendix

### Sample ENV file

```
AZURE_APP_SERVICE_PLAN_NAME="JP-asp-JPE-DEV-xxx-Chat-001"
AZURE_BACKEND_SERVICE_NAME="JP-app-JPE-DEV-xxx-Chat-001"
AZURE_ENV_NAME="xxxchatpoc-20230920"
AZURE_LOCATION="japaneast"
AZURE_OPENAI_RESOURCE_GROUP="JP-rg-JPE-DEV-xxx-xxxchatpoc"
AZURE_OPENAI_SERVICE="jp-oai-jpe-dev-xxx-chat-001"
AZURE_PRIVATE_DNS_ZONE_OPENAI_ID="/subscriptions/186b7a44-a6a0-40e2-bc49-dfcd4162bcfd/resourceGroups/JP-RG-PrivateDNSZone/providers/Microsoft.Network/privateDnsZones/privatelink.openai.azure.com"
AZURE_PRIVATE_DNS_ZONE_SEARCH_ID="/subscriptions/186b7a44-a6a0-40e2-bc49-dfcd4162bcfd/resourceGroups/JP-RG-PrivateDNSZone/providers/Microsoft.Network/privateDnsZones/privatelink.search.windows.net"
AZURE_PRIVATE_DNS_ZONE_STBLOB_ID="/subscriptions/186b7a44-a6a0-40e2-bc49-dfcd4162bcfd/resourceGroups/JP-RG-PrivateDNSZone/providers/Microsoft.Network/privateDnsZones/privatelink.blob.core.windows.net"
AZURE_PRIVATE_DNS_ZONE_WEBAPP_ID="/subscriptions/186b7a44-a6a0-40e2-bc49-dfcd4162bcfd/resourceGroups/JP-RG-PrivateDNSZone/providers/Microsoft.Network/privateDnsZones/privatelink.azurewebsites.net"
AZURE_RESOURCE_GROUP="JP-rg-JPE-DEV-xxx-xxxchatpoc"
AZURE_SEARCH_INDEX="xxxchat-searchindex-all"
AZURE_SEARCH_INDEX_srfi="srfi"
AZURE_SEARCH_INDEX_paagj="paagj"
AZURE_SEARCH_SERVICE="jp-srch-jpe-dev-xxx-chat-001"
AZURE_SEARCH_SERVICE_RESOURCE_GROUP="JP-rg-JPE-DEV-xxx-xxxchatpoc"
AZURE_STORAGE_ACCOUNT="yyyyjpstjpedevxxxchat001"
AZURE_STORAGE_CONTAINER="content"
AZURE_STORAGE_RESOURCE_GROUP="JP-rg-JPE-DEV-xxx-xxxchatpoc"
AZURE_SUBSCRIPTION_ID="4e5f4eee-7351-44f9-b798-5cc689abbc47"
AZURE_TENANT_ID="deff24bb-2089-4400-8c8e-f71e680378b2"
BACKEND_URI="https://jp-app-jpe-dev-xxx-chat-001.azurewebsites.net"
OPENAI_API_ENDPOINT="https://jp-oai-jpe-dev-xxx-chat-001.openai.azure.com"
SEARCH_API_KEY="REDACTED"
SEARCH_ENDPOINT="https://jp-srch-jpe-dev-xxx-chat-001.search.windows.net"
```
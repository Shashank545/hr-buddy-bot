# Data Ingestion for KitChat

## Introduction

- This document reports the setup and process required for `Kit-Chat's` data ingestion pipeline.
- `Kit-Chat` knowledge data exists in `PDF` and `HTML` Sharepoint files.
- It contains HR related informations to answer general HR enquiries from employees.
- Data Ingeston pipeline consists of two processes


    1. Process 1 - Loading contents from static knowledge files and chunking them
    1. Process 2 - Creating search indexes from chunk in Azure Cognitive Search(ACS)


## Setup

1. Provision an Azure Open AI Service instance with One Cloud Hosting (OCH).
1. Deploy `text-embedding-ada-002` embedding model from Azure OpenAI.
1. Provision an Azure Cognitive Search (ACS) instance with OCH.
1. Enable semantic search of the ACS instance. You could do this on [Azure Portal](https://portal.azure.com).
1. Create a `.env` file and set the following environment variables:

    1. `OPENAI_API_KEY`
    1. `OPENAI_API_ENDPOINT`
    1. `SEARCH_API_KEY`
    1. `SEARCH_ENDPOINT`

1. Create a local Python environment with `scripts/requirements.txt`.
1. Place all PDF and HTML files to be chunked into `data/` directory with optional sub-directories if needed.
1. Place the `pii_list.txt` file containings personal names to be filtered into `data/` directory.

## Data Ingestion Pipeline

### Procees 1 : Create knowledge chunks from Kit-Chat Files

Steps:
1. Fetch all PDF/HTML files for loading
1. Load PDF files fetched from disk and create documents
1. Create chunks from PDF documents and save to disk

For PDF Files:
```bash
python scripts/prepdocs.py 'data/' --sourceformat 'pdf' -o 'output/' -p 'chunk' -v
```

For HTML Files:
```bash
python scripts/prepdocs.py 'data/' --sourceformat 'html' -o 'output/' -p 'chunk' -v
```

The chunks will be stored in `output` folder with file format similar to below:
1. `kitchat_html_chunkstore_yyyymmdd_hhmmss.json` for HTML files
1. `kitchat_pdf_chunkstore_yyyymmdd_hhmmss.json` for PDF files


### Procees 2 : Create ACS Indexes from knowledge chunks

Steps:
1. Read JSON chunks from disk
1. Add title and content embeddings to chunks and save to disk if needed
1. Create ACS index if it does not exist
1. Upload updated chunks to ACS Index

```bash
python scripts/prepdocs.py 'data/' -o 'output/' -p 'index' -v
```

It will create a single unified search indexes in ACS with the name `kitchat-searchindex-all` combining all PDF and HTML data chunks.


## Ingestion statistics

`Summary for PDF Files`:

```bash
[INFO] Data Ingestion Statistics for PDF Files :......
[INFO] chunking_method: 'rcsplit'
[INFO] total_num_files: 53
[INFO] total_num_pages: 531
[INFO] min(num_tokens_per_page): 0
[INFO] mean(num_tokens_per_page): 570
[INFO] median(num_tokens_per_page): 526
[INFO] max(num_tokens_per_page): 1647
```

`Summary for HTML Files`:
```bash
[INFO] Data Ingestion Statistics for HTML Sharepoint Files :......
[INFO] chunking_method: 'rcsplit'
[INFO] total_num_files: 73
[INFO] total_num_pages: 73
[INFO] min(num_tokens_per_page): 424
[INFO] mean(num_tokens_per_page): 1313
[INFO] median(num_tokens_per_page): 1033
[INFO] max(num_tokens_per_page): 4601
```

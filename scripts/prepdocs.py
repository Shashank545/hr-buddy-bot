"""Parse contents of input files, and create and populate ACS index(es) to enable RAG.

Before running this script, DO NOT forget to source required environment vars by
executing the following command from the root directory of the project.

`source .azure/{ENVIRONMENT_NAME}/.env`
"""
import argparse
import datetime
import json
import os
import pickle
import statistics
import sys
import time
from pathlib import Path
from typing import Callable, List

import openai
import pdfplumber
import tiktoken
# from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswVectorSearchAlgorithmConfiguration,
    PrioritizedFields,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings,
    SimpleField,
    VectorSearch
)
from datamodels import Chunk, KnowledgeFormat
from dotenv import find_dotenv, load_dotenv
from langchain.document_loaders import UnstructuredHTMLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from rich import print
from rich.progress import track
from utils import count_tokens, get_filenames, is_input_dir_valid, load_json, load_names, to_json

load_dotenv(find_dotenv())



azd_credential = AzureDeveloperCliCredential()
openai.api_type = "azure_ad"
openai_token = azd_credential.get_token("https://cognitiveservices.azure.com/.default")
openai.api_key = openai_token.token
openai.api_base = os.environ.get("OPENAI_API_ENDPOINT")
openai.api_version = "2023-05-15"


ACS_ENDPOINT = os.environ.get("SEARCH_ENDPOINT")
print(ACS_ENDPOINT)
TEXT_EMBEDDING_ADA_002_DEPLOYMENT = "text-embedding-ada-002"
TEXT_EMBEDDING_ADA_002_DIMENSION = 1536
MAX_ALLOWED_TOKEN_COUNT_FOR_TEXT_EMBEDDING_ADA_002 = 8191
MAX_EMBEDDING_RETRIES = 5

FORMAT_OPTION_WEB = "html"
FORMAT_OPTION_PDF = "pdf"
FORMAT_OPTIONS = {FORMAT_OPTION_WEB, FORMAT_OPTION_PDF}

CHUNK_PROCESS = "chunk"
INDEX_PROCESS = "index"
PROCESS_OPTIONS = {CHUNK_PROCESS, INDEX_PROCESS}

SLEEP_TIME_FOR_INDEXING_IN_SEC = 3
SLEEP_TIME_FOR_EMBEDDING_IN_SEC = 3
SAVE_CHUNKS_TO_DISK = True

ACS_FIELDS_KITCHAT = [
    SimpleField(
        name="id",
        type="Edm.String",
        key=True,
        filterable=True,
    ),
    SimpleField(
        name="parent_id",
        type="Edm.String",
        filterable=True,
    ),
    SearchableField(
        name="title",
        type="Edm.String",
        analyzer_name="en.lucene",
    ),
    SearchField(
        name="title_embedding",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=TEXT_EMBEDDING_ADA_002_DIMENSION,
        vector_search_configuration="default",
    ),
    SearchableField(
        name="content",
        type="Edm.String",
        analyzer_name="en.lucene",
        searchable=True,
    ),
    SearchField(
        name="content_embedding",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=TEXT_EMBEDDING_ADA_002_DIMENSION,
        vector_search_configuration="default",
    ),
    SimpleField(
        name="source_path",
        type="Edm.String",
    ),
    SimpleField(
        name="lang",
        type="Edm.String",
    ),
    SimpleField(
        name="page_num",
        type="Edm.Int32",
    ),
    SimpleField(
        name="num_tokens",
        type="Edm.Int32",
    ),
    SimpleField(
        name="modified_from_source",
        type="Edm.Boolean",
    ),
]

ENCODER = tiktoken.encoding_for_model("text-embedding-ada-002")
DEFAULT_SEPARATORS = ["\n\n", "\n", "。", " ", ""]


def process_args() -> argparse.Namespace:
    """Process/Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Prepare documents by extracting content from input PDF "
            "and HTML Sharepoint files, splitting content into chunks,"
            "and indexing in a ACS search index"
        ),
        epilog=(
            "Example: python scripts/prepdocs.py 'data/' --sourceformat 'html' \
            -o 'output/' -p 'index' -v"
        ),
    )
    parser.add_argument(
        "files",
        help="Path to the KiChat files",
    )
    parser.add_argument(
        "--process",
        "-p",
        required=True,
        default=CHUNK_PROCESS,
        choices=PROCESS_OPTIONS,
        help=("Optional. Select process to orchestrate. Defaults to chunking process."),
    )
    parser.add_argument(
        "--sourceformat",
        required=False,
        default=FORMAT_OPTION_PDF,
        choices=FORMAT_OPTIONS,
        help=("Optional. Select source file format. Defaults to PDF."),
    )
    parser.add_argument(
        "--postprocess",
        "-pp",
        required=False,
        default="data/pii_list.txt",
        help=("Optional. Path to file containing personal information to be redacted."),
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        dest="path_to_chunkstores",
        required=False,
        type=str,
        default="output",
        help="Path to output chunkstores",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args()


def set_openai_token() -> None:
    """Refresh Open AI token."""
    global openai_token
    openai_token = azd_credential.get_token("https://cognitiveservices.azure.com/.default")
    openai.api_key = openai_token.token
    print("[DEBUG] OpenAI token is set")


def generate_embeddings(text: str, limit_text_len: bool = True) -> List[float]:
    """Generate embeddings for the input text using text-embedding-ada-002."""
    time.sleep(SLEEP_TIME_FOR_EMBEDDING_IN_SEC)
    if limit_text_len:
        text = ENCODER.decode(
            ENCODER.encode(text)[:MAX_ALLOWED_TOKEN_COUNT_FOR_TEXT_EMBEDDING_ADA_002]
        )
    retry = 0
    while retry < MAX_EMBEDDING_RETRIES:
        try:
            response = openai.Embedding.create(
                input=text,
                engine=TEXT_EMBEDDING_ADA_002_DEPLOYMENT
            )
            embeddings = response["data"][0]["embedding"]
            return embeddings
        except openai.error.APIError as err:
            print(f"[WARNING] '{err}'. Retrying to generate embeddings.")
            set_openai_token()
        retry += 1
    return None


def init_rc_text_splitter(
    chunk_size: int = 1024,
    chunk_overlap: int = 128,
    length_function: Callable = count_tokens,
    is_separator_regex: bool = False,
    keep_separator: bool = True,
    separators: List[str] = DEFAULT_SEPARATORS,
) -> RecursiveCharacterTextSplitter:
    """Initialize Recursive Char Text Splitter from Langchain.

    Args:
        chunk_size (int): max number of tokens allowed in a single chunk
        chunk_overlap (int): overlap between adjacent chunks
        length_function (Callable): custom method used to count tokens
        is_separator_regex (bool): is separator regex
        keep_separator (bool): keep separator in splits
        separators (List[str]): list of separators
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=length_function,
        is_separator_regex=is_separator_regex,
        keep_separator=keep_separator,
        separators=separators,
    )


def chunk_with_rcsplit(documents: List[KnowledgeFormat]) -> List[Chunk]:
    """Chunk text by recursively looking at certain characters.

    Args:
        documents (List[KnowledgeFormat]): input documents to be chunked

    Returns:
        List[Chunk]: output chunks
    """
    splitter = init_rc_text_splitter(chunk_size=1024, chunk_overlap=128)
    chunkstore = []
    for doc in documents:
        texts = splitter.split_text(doc.content)
        parents = [
            Chunk(
                content=text,
                page_num=doc.page_num,
                source_path=doc.source_path,
                title=doc.title,
                lang=doc.lang,
            )
            for text in texts
        ]
        chunkstore.extend(parents)
    return chunkstore


def postprocess_chunk(chunkstore: List[Chunk], filternames: List[str]) -> List[Chunk]:
    """Filter out perosnal infromation like employee names during postprocessing.

    Args:
        chunkstore (List[Chunk]): List of chunks to be postprocessed
        filternames (List[str]): List of names to be filtered out

    Returns:
        List[Chunk]: List of chunks after being cleaned
    """
    for chunk in chunkstore:
        for name in filternames:
            chunk.content = chunk.content.replace(name[:-1], "")

    # print(chunkstore[0])
    return chunkstore


def get_chunks(
    doc_type: str,
    documents: List[KnowledgeFormat],
    path_to_chunkstores: Path,
    filternames: List[str],
) -> None:
    """Get chunks from input documents and save to disk.

    Args:
        doc_type (str): Type of source document
        documents (List[KnowledgeFormat]): List of source documents
        path_to_chunkstores (Path): Output directory to store chunks
        filternames (List[str]): List of strings for postprocessing
    """
    # split with recursive method
    chunkstore = chunk_with_rcsplit(documents)

    # post process
    _ = postprocess_chunk(chunkstore, filternames)

    # save chunks to disk
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_fname = path_to_chunkstores.joinpath(
        f"kitchat_{doc_type}_chunkstore_{timestamp}.json"
    )
    to_json(out_fname, chunkstore)
    print(f"[INFO] Chunks are stored in '{out_fname}'")


def load_pdf_documents(path_to_docs: Path) -> List[KnowledgeFormat]:
    """Load PDF files from disk.

    Note that all target PDF files are loaded to memory at \
    once (known as eager loading).

    Args:
        path_to_docs (str): directory containing PDF Files
        method (str): loader name

    Returns:
        List[KnowledgeFormat]: PDF pages
    """
    filenames = get_filenames(path_to_docs.stem, "pdf", True)
    docs = []
    for filename in track(sequence=filenames, description="Loading PDF files..."):
        doc = []
        with pdfplumber.open(filename) as pdf:
            for page in pdf.pages:
                doc.append(
                    KnowledgeFormat(
                        content=page.extract_text(),
                        source_path=filename.as_posix(),
                        title=filename.stem[:-3],
                        page_num=page.page_number,
                        lang=filename.stem.split("_")[-1],
                    )
                )
        docs.extend(doc)
    return docs


def load_html_documents(path_to_docs: Path) -> List[KnowledgeFormat]:
    """Load PDF files from disk.

    Note that all target HTML files are loaded to memory at \
    once (known as eager loading).

    Args:
        path_to_docs (str): directory containing HTML Files
        method (str): loader name

    Returns:
        List[KnowledgeFormat]: HTML pages
    """
    filenames = get_filenames(path_to_docs.stem, "html", True)
    docs = []
    html_count = 1
    for filename in track(
        sequence=filenames, description="Loading HTML Sharepoint files..."
    ):
        doc = []
        loader = UnstructuredHTMLLoader(filename)
        data_items = loader.load()
        for data in data_items:
            doc.append(
                KnowledgeFormat(
                    content=data.page_content,
                    source_path=filename.as_posix(),
                    title=filename.stem[:-3]
                    if filename.stem[-2:] == "en"
                    else filename.stem,
                    page_num=html_count,
                    lang=filename.stem[-2:] if filename.stem[-2:] == "en" else "jp",
                )
            )
            html_count = html_count + 1
        docs.extend(doc)
    return docs


def create_search_index_object(index_name: str, fields: list) -> SearchIndex:
    """Create search index object.

    For vector search, we use Hierarchical Navigable Small World (HNSW)
    approximate nearest neighbors algorithm.

    Args:
        index_name (str): name of ACS index
        fields (list): search fields

    Returns:
        SearchIndex: search index object
    """
    return SearchIndex(
        name=index_name,
        fields=fields,
        semantic_settings=SemanticSettings(
            configurations=[
                SemanticConfiguration(
                    name="default",
                    prioritized_fields=PrioritizedFields(
                        title_field=None,
                        prioritized_content_fields=[
                            SemanticField(field_name="content")
                        ],
                    ),
                )
            ]
        ),
        vector_search=VectorSearch(
            algorithm_configurations=[
                HnswVectorSearchAlgorithmConfiguration(
                    name="default",
                    kind="hnsw",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 1000,
                        "metric": "cosine",
                    },
                )
            ]
        ),
    )


def create_search_index(
        *,
        index_name: str,
        fields: list,
        verbose: bool = True
) -> None:
    """Create ACS index if it does not exist already.

    Args:
        index_name (str): search index name
        fields (list): search fields
        verbose (bool, optional): verbose flag. Defaults to True.
    """
    index_client = SearchIndexClient(
        endpoint=ACS_ENDPOINT,
        credential=azd_credential,
        api_version="2023-07-01-Preview",
    )
    if index_name not in index_client.list_index_names():
        index: SearchIndex = create_search_index_object(index_name, fields)
        if verbose:
            print(f"[INFO] Creating search index '{index_name}'")
        index_client.create_index(index)
    else:
        if verbose:
            print(f"[INFO] Search index '{index_name}' already exists")


def populate_index(
    index_name: str,
    chunks: List[dict],
    verbose: bool = True,
) -> None:
    """Index documents by uploading to ACS.

    Args:
        index_name (str): name of index
        chunks (List[dict]): document chunks
        verbose (bool, optional): verbose flag. Defaults to True.
    """
    if verbose:
        print(f"[INFO] Populating index '{index_name}'")

    search_client = SearchClient(
        endpoint=ACS_ENDPOINT,
        index_name=index_name,
        credential=azd_credential,
        api_version="2023-07-01-Preview",
    )

    batch = []
    results = []
    for chunk in track(sequence=chunks, description="Populating index..."):
        time.sleep(SLEEP_TIME_FOR_INDEXING_IN_SEC)
        batch.append(chunk)
        if sys.getsizeof(json.dumps(batch)) >= 1.5e7:
            results += search_client.upload_documents(documents=batch)
            batch = []

    if len(batch) > 0:
        results += search_client.upload_documents(documents=batch)

    num_success = sum([1 for record in results if record.succeeded])
    if verbose:
        print(f"[INFO] Indexed {len(results)} chunks, {num_success} succeeded")


def display_doc_stats(
    loaded_data: List[KnowledgeFormat],
    method: str = "rcsplit",
    source_type: str = "PDF",
) -> None:
    """Display chunk statistics and properties of each type.

    Args:
        loaded_data (List[KnowledgeFormat]): List of loaded documents
        method (str): split method
        source_type (Str): type of document
    """
    total_num_files = len(set(doc.source_path for doc in loaded_data))
    total_num_pages = len(loaded_data)
    num_tokens = [page.num_tokens for page in loaded_data]

    print(f"[INFO] Data Ingestion Statistics for {source_type} Files :......")
    print(f"[INFO] chunking_method: '{method}'")
    print(f"[INFO] total_num_files: {total_num_files}")
    print(f"[INFO] total_num_pages: {total_num_pages}")
    print(f"[INFO] min(num_tokens_per_page): {min(num_tokens)}")
    print(f"[INFO] mean(num_tokens_per_page): {int(statistics.mean(num_tokens))}")
    print(f"[INFO] median(num_tokens_per_page): {int(statistics.median(num_tokens))}")
    print(f"[INFO] max(num_tokens_per_page): {max(num_tokens)}")
    print("\n\n")


def main():
    """Orchestrate KitChat knowledge preprocessing, chunking and ACS indexing."""
    # Parse input arguments
    args = process_args()
    path_to_docs = Path(args.files)
    path_to_pii = Path(args.postprocess)  # path to file with employee information
    path_to_chunkstores = Path(args.path_to_chunkstores)  # path to chhunkstore

    # [Process 1] : Orchestrate knowledge chunking and postprocessing
    if args.process == CHUNK_PROCESS:
        # Check if source format is missing
        if args.process and not args.sourceformat:
            raise ValueError("Source file format is required for chunking process!!")

        # Load list of strings to filter out
        kit_names = load_names(path_to_pii)

        if is_input_dir_valid(path_to_docs):
            print(
                "[INFO] Process 1 ** : Orchestrate knowledge chunking"
                "and postprocessing"
            )

            if args.sourceformat == FORMAT_OPTION_PDF:
                # [Step 1/3] Fetch all PDF files for loading
                print(
                    f"[INFO] [Step 1/3] Fetch all {FORMAT_OPTION_PDF.upper()}"
                    "files for loading."
                )
                trg_filenames = get_filenames(path_to_docs, args.sourceformat, True)

                # [Step 2/3] Load PDF files fetched from disk and create documents
                print(
                    f"[INFO] [Step 2/3] Load {FORMAT_OPTION_PDF.upper()} files"
                    "fetched from disk and create documents."
                )
                pdf_documents = load_pdf_documents(path_to_docs)
                if args.verbose:
                    print(
                        f"[INFO] Target {args.sourceformat} files: "
                        "{[f.name for f in trg_filenames]}\n\n\n"
                        f"[INFO] Total {args.sourceformat}s: {len(trg_filenames)}\n\n"
                    )
                    display_doc_stats(pdf_documents)

                # [Step 3/3] Create chunks from PDF documents and save to disk
                print(
                    f"[INFO] [Step 3/3] Create chunks from {FORMAT_OPTION_PDF.upper()}"
                    "documents and save to disk."
                )
                _ = get_chunks(
                    FORMAT_OPTION_PDF, pdf_documents, path_to_chunkstores, kit_names
                )

            elif args.sourceformat == FORMAT_OPTION_WEB:
                # [Step 1/3] Fetch all HTML files for loading
                print(
                    f"[INFO] [Step 1/3] Fetch all {FORMAT_OPTION_WEB.upper()}"
                    "files for loading."
                )
                trg_filenames = get_filenames(path_to_docs, args.sourceformat, True)

                # [Step 2/3] Load HTML files fetched from disk and create documents
                print(
                    f"[INFO] [Step 2/3] Load {FORMAT_OPTION_WEB.upper()} files "
                    "fetched from disk and create documents."
                )
                html_documents = load_html_documents(path_to_docs)
                if args.verbose:
                    print(
                        f"[INFO] Target {args.sourceformat} files: "
                        "{[f.name for f in trg_filenames]}\n\n\n"
                        f"[INFO] Total {args.sourceformat} files: {len(trg_filenames)}"
                    )
                    display_doc_stats(html_documents, source_type="HTML Sharepoint")

                # [Step 3/3] Create chunks from HTML documents and save to disk
                print(
                    f"[INFO] [Step 3/3] Create chunks from {FORMAT_OPTION_WEB.upper()} "
                    "documents and save to disk."
                )
                _ = get_chunks(
                    FORMAT_OPTION_WEB, html_documents, path_to_chunkstores, kit_names
                )

    # [Process 2] : Orchestrate KitChat ACS indexing
    elif args.process == INDEX_PROCESS:
        # Get chunked file names in JSON
        filenames = get_filenames("output", "json")
        print(filenames)
        index_name = "kitchat-searchindex-all"

        # Process input chunked files one by one
        # Create a separate index for each chunk type
        all_chunks = []
        print(f"[INFO] Setting up index '{index_name}'...")
        # [Step 1/4] Read JSON chunks from disk
        for filename in filenames:
            chunks = load_json(filename)
            print(f"[INFO] Loaded {len(chunks)}-{filename.stem.split('_')[1]} chunks")
            all_chunks.extend(chunks)
        print(len(all_chunks))

        # [Step 2/4] Add title and content embeddings to chunks and
        # save the final form of the chunks to disk if needed
        title_embeddings = {chunk["title"]: [] for chunk in all_chunks}
        for title in track(
            sequence=title_embeddings.keys(), description="Embedding titles..."
        ):
            title_embeddings[title] = generate_embeddings(title)

        for chunk in track(sequence=all_chunks, description="Embedding contents..."):
            chunk["title_embedding"] = title_embeddings[chunk["title"]]
            chunk["content_embedding"] = generate_embeddings(chunk["content"])
        num_errors = sum(
            [
                "content_embedding" not in chunk
                or chunk["content_embedding"] is None
                for chunk in all_chunks
            ]
        )
        print(f"[DEBUG] num_errors_during_embedding: {num_errors}")
        if SAVE_CHUNKS_TO_DISK:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(f"{index_name}_{timestamp}.pickle", "wb") as fout:
                pickle.dump(all_chunks, fout)

        # [Step 3/4] Create ACS index if it does not exist
        create_search_index(
            index_name=index_name, fields=ACS_FIELDS_KITCHAT, verbose=True
        )

        # [Step 4/4] Upload updated chunks to ACS
        populate_index(
            index_name=index_name,
            chunks=all_chunks,
            verbose=True,
        )

    return


if __name__ == "__main__":
    main()

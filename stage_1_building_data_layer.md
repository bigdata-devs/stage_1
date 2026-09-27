# Stage 1 Building the Data Layer 

Search Engine Project 

Big Data 

Grado en Ciencia e Ingeniería de Datos Universidad de Las Palmas de Gran Canaria 

## **1 Introduction** 

The overall goal of Big Data course project is to design and implement a simple _search engine_ from scratch, providing students with a practical introduction to the core components of modern data pipelines and Big Data processing. The final system will be capable of ingesting raw data, processing it into efficient structures, and serving basic search queries. At the core of this project lies the _data layer_ , which serves as the foundation for all other components of the search engine. Its main purpose is to provide a reliable, scalable, and well-organized environment where raw data can be stored, transformed, and optimized for efficient querying. 

This guide focuses exclusively on _Stage 1_ , whose objective is to design and implement this data layer, establishing the backbone of the entire search engine. In this phase, students will build a workflow to collect, clean, and organize data, ensuring it is ready for the indexing and querying processes in later stages. The outcome of Stage 1 is a well-structured storage architecture that separates unstructured content from structured, queryable data. The data layer consists of two complementary storage systems: 

- _Datalake:_ Stores the raw and cleaned book content in an unstructured format, acting as the central repository for data ingestion and processing. 

- _Datamarts:_ Stores structured, queryable data, including book metadata and the inverted indexes that enable fast and efficient search operations. 

By the end of this stage, students will have developed a solid data architecture that mirrors the design principles of real-world Big Data systems. This foundation will enable _Stage 2_ , where the crawling, indexing and querying modules will be implemented and integrated into a fully functional search engine. In addition, students will benchmark alternative implementations using at least three programming languages, such as Python, Java, C#, or any other language justified by the group. 

1 

## **2 Data Source** 

The dataset for this project comes from _Project Gutenberg_ , a free digital library of public domain books. 

Each book has a unique id and is available as a plain-text (.txt). For example, the book with ID 1342 (Pride and Prejudice by Jane Austen) can be downloaded from: 

https://www.gutenberg.org/cache/epub/1342/pg1342.txt 

Each book follows a consistent structure: 

1. _Header:_ Contains metadata about the book such as title, author, release date, language, and licensing notes. 

2. _Body:_ The actual text of the book. 

3. _Footer:_ Closing notes and copyright information. 

The following script provides an example of how to download a book from Project Gutenberg, detect the markers that delimit the text, and split it into header and body. 

**<mark>import</mark>** <mark>requests</mark> **<mark>from</mark>** <mark>pathlib</mark> **<mark>import</mark>** <mark>Path START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK" END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"</mark> **<mark>def</mark>** <mark>download_book(book_id:</mark> **<mark>int</mark>** <mark>, output_path:</mark> **<mark>str</mark>** <mark>): output_path = Path(output_path) output_path.mkdir(parents=True, exist_ok=True) url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt" response = requests.get(url) response.raise_for_status() text = response.text</mark> **<mark>if</mark>** <mark>START_MARKER</mark> **<mark>not in</mark>** <mark>text</mark> **<mark>or</mark>** <mark>END_MARKER</mark> **<mark>not in</mark>** <mark>text:</mark> **<mark>return</mark>** <mark>False header, body_and_footer = text.split(START_MARKER, 1) body, footer = body_and_footer.split(END_MARKER, 1)</mark> _<mark># --- Step 3: Save each part ---</mark>_ <mark>body_path = output_path / f"{book_id}_body.txt" header_path = output_path / f"{book_id}_header.txt" with</mark> **<mark>open</mark>** <mark>(body_path, "w", encoding="utf-8") as f: f.write(body.strip()) with</mark> **<mark>open</mark>** <mark>(header_path, "w", encoding="utf-8") as f: f.write(header.strip())</mark> **<mark>return</mark>** <mark>True</mark> _<mark># Example of Usage</mark>_ <mark>success = download_book(1342, "data/output")</mark> 

Listing 1: Function to download and split a book 

2 

## **3 Organizing the Datalake** 

To ensure the ingestion pipeline remains scalable, organized, and easy to maintain, the _datalake_ should follow a well-defined directory hierarchy. A recommended approach is to structure files based on the date and hour of ingestion, reflecting exactly when each file was downloaded. 

This organization offers several key benefits: 

- _Traceability:_ Quickly identify when a specific book was ingested, simplifying debugging and audit processes. 

- _Incremental processing:_ Later stages, such as indexing, can focus only on the most recent folders instead of scanning the entire datalake. 

- _Scalability:_ Distributing files across multiple directories avoids performance bottlenecks that occur when too many files are stored in a single folder. 

- _Compatibility:_ This layout mirrors common practices in distributed storage systems such as HDFS or Amazon S3, making it easier to migrate to a large-scale environment in the future. 

By following this hierarchy, the datalake remains clean, efficient, and ready to handle growing volumes of data without requiring major structural changes. The recommended layout is: 

datalake/ 

YYYYMMDD/ HH/ 

<BOOK_ID>.body.txt <BOOK_ID>.header.txt 

where _YYYYMMDD_ is the date of download (e.g., 20250925); _HH_ is the hour of download in 24-hour format (e.g., 14 for 2 PM); and _<BOOK_ID>_ is the file id obtained from Project Gutenberg. 

### **3.1 Datalake Structure Benchmark** 

The datalake structure must not be treated as a fixed design decision. Each group must compare different ways of organizing the downloaded documents and evaluate how each structure affects ingestion, lookup, recovery, and later indexing. The benchmark must be implemented in at least three programming languages, for example Python, Java, C#, Go, Rust, or JavaScript/Node.js. All language implementations must process the same dataset, use the same preprocessing rules, and produce equivalent outputs. This ensures that the comparison focuses on the language implementation and the storage structure, rather than on differences in functionality. Recommended datalake structures to compare include: 

- _Time-based hierarchy:_ Files are grouped by download date and hour, as shown above. 

- _Book-based hierarchy:_ Each book has its own directory containing the body, header, and any auxiliary metadata. 

3 

- _Batch or range-based hierarchy:_ Books are grouped into folders by ranges, batches, or hash prefixes, reducing the number of files stored in a single directory. 

The experiments should measure: 

- _Download and write throughput:_ Number of books downloaded, split, and stored per unit of time. 

- _Lookup cost:_ Time needed to locate the body and header of a specific book. 

- _Incremental processing:_ Cost of detecting which books are new and ready to be indexed. 

- _Recovery behavior:_ Ability to resume the pipeline after an interruption without duplicating or losing documents. 

- _Storage overhead:_ Number of files, directories, and auxiliary control structures required by each design. 

The report must justify which datalake structure is selected for the final implementation and explain the trade-offs observed across the different programming languages. 

## **4 Building Datamarts** 

Once books have been downloaded and processed, the next step is to organize the cleaned data into optimized storage structures called _datamarts_ . While the _datalake_ serves as a scalable repository for all raw and cleaned text, the _datamart_ provides structured, queryable data that will be directly used by the indexing and search modules. The datamart consists of two main components: 

1. _Metadata:_ Structured information about each book, extracted from the _header_ . 

2. _Inverted Index:_ Efficient data structures built from the _body_ , enabling fast search queries. 

This separation ensures that metadata operations (e.g., filtering by author or title) and search operations (e.g., keyword lookups) can be handled independently and efficiently. 

### **4.1 Metadata** 

The metadata must be parsed directly from the _header_ of each downloaded book. By keeping metadata separate from the full text files, the system can quickly filter and organize books without scanning the entire contents of each file. This enables operations such as: 

- Filtering books by a specific author, title, or language. 

- Quickly locating the path of the corresponding cleaned text file. 

- Supporting the indexing stage by supplying structured input data. 

4 

The header typically contains descriptive information in a structured, line-by-line format, including fields such as Title, Author, and Language. After extracting these values — for example, using _regular expressions_ (regex) to match the relevant lines — the data can be cleaned and normalized. Once extracted, the metadata is stored in a database, such as _SQLite_ , to provide a simple and efficient way to query structured information. 

An example schema for the books table: 

book_id | title | author | language 5 | Robinson Crusoe | Daniel Defoe | en 

#### **Metadata Storage Comparison** 

To evaluate the performance of the metadata layer, the same schema can be implemented using different storage backends. This comparison is optional but recommended when the group wants to study how metadata queries behave under different systems. Possible categories for testing include: 

- _Lightweight embedded database: SQLite_ is simple to set up and ideal for prototypes or small datasets. 

- _Traditional relational database: PostgreSQL_ or _MySQL_ provide robust indexing, transaction handling, and better support for concurrent access. 

- _NoSQL database: MongoDB_ or _Redis_ offer flexible schema design, high-speed inserts, and horizontal scalability for very large datasets. 

By running the same set of operations on these different systems, students can measure the trade-offs between simplicity, speed, and scalability, and justify their final choice of metadata storage for the project. 

#### **Benchmarking Considerations** 

To ensure the metadata storage layer is efficient and scalable, several experiments should be planned: 

1. _Insertion speed:_ Measure how quickly metadata for thousands of books can be inserted into the database. 

2. _Query performance:_ Evaluate the response time for common queries, such as: _Find all books by a specific author_ ; or _Retrieve the path of a book by its title or ID._ 

3. _Scalability tests:_ Test how performance changes as the number of books grows from hundreds to tens of thousands. 

These benchmarks will help select the most appropriate metadata storage option for later stages of the project, ensuring that the metadata layer can support both the indexing and querying modules efficiently. 

5 

### **4.2 Inverted index** 

The inverted index can be organized in different ways depending on performance, scalability, and implementation complexity. Below are three illustrative approaches, each with its own advantages and trade-offs. Students are required to implement and benchmark at least three different indexing structures, and they may also design their own custom approaches. The goal is to understand how the physical organization of the index impacts both query speed and indexing efficiency. 

The benchmark must also compare implementations in at least three programming languages. The same dataset, tokenizer, normalization rules, and query workload must be used in all cases so that results are comparable across languages and index structures. 

#### **Single Monolithic File** 

All terms and their posting lists are stored in _one single file_ , for example, in a JSON or binary format. The structure maps each term directly to the list of documents where it appears: 

{ "adventure": [5, 12, 42], 

"island": [5, 1342], 

"shipwreck": [12, 17] } 

This file should be saved in the project under the path: 

datamarts/inverted_index.json 

#### **Pros:** 

- Very simple to implement and maintain. 

- Easy to back up and transfer as a single file. 

#### **Cons:** 

- As the index grows, every update may require rewriting a large file. 

- Limited scalability for concurrent read/write operations. 

#### **NoSQL Database (MongoDB)** 

In this approach, the inverted index is stored directly in a _NoSQL database_ , such as MongoDB, where each term is represented as a document containing its postings list. This design takes advantage of built-in features like indexing, compression, and fast random access. 

{ "term": "adventure", "postings": [5, 12, 42, 1342] } 

6 

#### **Pros:** 

- High performance for random reads and writes. 

- Built-in scalability and support for distributed storage. 

- Simplifies concurrent access and incremental updates. 

- Query language allows for flexible searches and analytics. 

#### **Cons:** 

- Requires installing and managing an external database system. 

- Added complexity compared to simple file-based approaches. 

- Network latency can impact performance if not properly configured. 

#### **Hierarchical Folder Structure** 

In this approach, the inverted index is organized as a set of folders, where each _term_ has its own individual .txt file. The files can be grouped into subdirectories. For example: 

datamarts/ 

inverted_index/ A/ adventure.txt apple.txt B/ boat.txt bridge.txt C/ castle.txt 

Each file contains the _postings list_ for its corresponding term, i.e., the list of book_id values (and optionally positions) where the term appears. 

Example content of adventure.txt: 

5 12 42 1342 

#### **Pros:** 

- Very fine-grained updates: only the file of the affected term is modified. 

- Natural fit for distributed file systems or cloud storage environments. 

- Easy to track and debug individual terms by inspecting their dedicated files. 

7 

#### **Cons:** 

- A very large number of small files can overwhelm the filesystem, reducing performance. 

- Lookup times may increase due to frequent file access operations. 

- More complex maintenance compared to monolithic or grouped-file structures. 

#### **Benchmarking Considerations** 

To evaluate the different approaches, students should design experiments to measure: 

- _Indexing speed:_ Time required to build the inverted index from a given dataset. 

- _Query performance:_ Average response time for a set of representative search queries. 

- _Update performance:_ Cost of adding new books to an existing index without rebuilding it completely. 

- _Memory and disk usage:_ Amount of RAM and storage required by each implementation. 

- _Scalability:_ How performance changes as the number of books and terms grows. 

These benchmarks will highlight the trade-offs between simplicity, update performance, memory usage, and scalability. The final report must discuss both dimensions of the experiment: the data structure used to store downloaded documents and the data structure used to store the inverted index. 

## **5 Control Layer** 

The _control layer_ acts as the _brain_ of the data ingestion pipeline. Its main role is to coordinate and supervise the execution of tasks across the different stages of the system, ensuring that the workflow proceeds smoothly, without duplication or data loss. This layer focuses on _tracking the state of the system_ . It keeps a record of what has been done, what is currently in progress, and what still needs to be completed. This makes the entire pipeline reliable and auditable. In this stage, only a _minimal control layer_ will be implemented. Its purpose is to test the functionality of the _data layer_ by coordinating simple operations such as downloading a book and sending it to the indexing step. More advanced orchestration features, such as parallel processing or complex scheduling, will be addressed in later stages. 

### **5.1 State Tracking** 

The control layer uses simple _control files_ to track progress. Control files are stored in a dedicated directory, such as control/. 

control/ downloaded_books.txt indexed_books.txt 

Each file contains a list of identifiers (BOOK_ID) representing the books at a specific stage: 

8 

- downloaded_books.txt Lists all books that have been successfully downloaded. 

- indexed_books.txt Lists all books that have been successfully indexed. 

### **5.2 How it works** 

The _control layer_ acts as the central coordinator of the entire pipeline, deciding which actions need to be performed at each step. The orchestration logic follows a simple decision process: 

1. _Check for books ready to be indexed:_ If there are books that have already been downloaded and cleaned but not yet indexed, the control layer schedules them for indexing. 

2. _Download new books if needed:_ If no books are pending for indexing, the system attempts to download a new book from Project Gutenberg. Before downloading, it verifies that the selected BOOK_ID has not been downloaded before, preventing duplicates. 

3. _Update state tracking:_ After each operation, the corresponding control files are updated to reflect the current state of the pipeline. 

The following function is a _simple example_ of how the control layer can coordinate downloads and indexing tasks. It shows the basic idea of checking which books are ready to be indexed and downloading new ones when needed. Students are free to design their own orchestration logic, for instance by introducing multiple downloaders or parallel indexers, as long as it correctly manages the pipeline and avoids duplicated work. 

**<mark>from</mark>** <mark>pathlib</mark> **<mark>import</mark>** <mark>Path</mark> **<mark>import</mark>** <mark>random CONTROL_PATH = Path("control") DOWNLOADS = CONTROL_PATH / "downloaded_books.txt" INDEXINGS = CONTROL_PATH / "indexed_books.txt" TOTAL_BOOKS = 70000</mark> 

**<mark>def</mark>** <mark>control_pipeline_step(): CONTROL_PATH.mkdir(parents=True, exist_ok=True)</mark> 

<mark>downloaded =</mark> **<mark>set</mark>** <mark>(DOWNLOADS.read_text().splitlines())</mark> **<mark>if</mark>** <mark>DOWNLOADS.exists()</mark> **<mark>else set</mark>** <mark>() indexed =</mark> **<mark>set</mark>** <mark>(INDEXINGS.read_text().splitlines())</mark> **<mark>if</mark>** <mark>INDEXINGS.exists()</mark> **<mark>else set</mark>** <mark>() ready_to_index = downloaded - indexed</mark> **<mark>if</mark>** <mark>ready_to_index: book_id = ready_to_index.pop()</mark> **<mark>print</mark>** <mark>(f"[CONTROL] Scheduling book {book_id} for indexing...")</mark> _<mark># Here you would call the indexer</mark>_ <mark>with</mark> **<mark>open</mark>** <mark>(INDEXINGS, "a", encoding="utf-8") as f: f.write(f"{book_id}\n")</mark> **<mark>print</mark>** <mark>(f"[CONTROL] Book {book_id} successfully indexed.")</mark> **<mark>else</mark>** <mark>:</mark> **<mark>for</mark>** <mark>_</mark> **<mark>in range</mark>** <mark>(10):</mark> _<mark># Retry up to 10 times to find a new book</mark>_ <mark>candidate_id =</mark> **<mark>str</mark>** <mark>(random.randint(1, TOTAL_BOOKS))</mark> **<mark>if</mark>** <mark>candidate_id</mark> **<mark>not in</mark>** <mark>downloaded:</mark> **<mark>print</mark>** <mark>(f"[CONTROL] Downloading new book with ID {candidate_id}...")</mark> _<mark># Here you would call the downloader</mark>_ <mark>with</mark> **<mark>open</mark>** <mark>(DOWNLOADS, "a", encoding="utf-8") as f: f.write(f"{candidate_id}\n")</mark> 

9 

**<mark>print</mark>** <mark>(f"[CONTROL] Book {candidate_id} successfully downloaded.")</mark> **<mark>break</mark>** 

Listing 2: Example control function to coordinate downloads and indexing 

## **6 Project Delivery Guidelines** 

Each group must select a unique _group name_ that will be used to identify their project. The final deliverable for this stage consists of a single _written report_ in PDF format. This document will serve as the official record of your work and must clearly reference the external repository where all the source code is hosted. 

This is the only file that must be submitted to the _virtual campus platform_ , and _only one member of the group_ should upload it on behalf of the entire team. This avoids duplicate submissions and ensures clarity during the evaluation process. 

### **6.1 Required Structure of the Report** 

The report (.pdf) must include the following sections: 

1. _Cover page:_ 

   - Course name and academic year. 

   - Project title. 

   - Full names and student IDs of all group members. 

   - The chosen group name. 

   - The URL of the GitHub repository. 

2. _Introduction and objectives:_ Describe the purpose of the project and the scope of the first stage. 

3. _System architecture:_ Explain how the pipeline is organized, including the datalake, datamart, and control layer. 

4. _Design decisions:_ Justify the selected data structures and indexing strategies. 

5. _Benchmarks and results:_ Present performance metrics and discuss the outcomes. This section must include a comparison of at least three programming languages and must evaluate both the datalake structure used to store downloaded documents and the invertedindex structure used to support search. 

6. _Conclusions and future improvements._ 

### **6.2 Group Name and Repository Structure** 

The GitHub repository must follow the exact format: 

https://github.com/<group_name>/stage_1 

10 

Example of a valid repository URL: 

https://github.com/dataexplorers/stage_1 

The repository must: 

- Include a README.md with detailed setup and execution instructions. 

- Provide a sample dataset so instructors can quickly test the pipeline. 

- Use Git history to show the progression of the development work. 

## **7 Evaluation Criteria** 

The grading will consider both the report and the implementation in the GitHub repository: 

- _Report quality_ (30%) – clarity, completeness, and organization of the written document. 

- _Correctness of the pipeline_ (30%) – proper functioning of downloading, indexing, and querying modules. 

- _Code quality_ (20%) – structure, modularity, and documentation of the source code. 

- _Benchmarking and analysis_ (20%) – depth of performance experiments, including the comparison of at least three programming languages, the datalake storage structure, the inverted-index structure, and a critical discussion of results. 

Students will have the opportunity to deliver a short _oral presentation_ of their work. This presentation is _optional_ and provides an opportunity to gain extra credit or to better demonstrate individual contributions to the project. 

- Each student will have a maximum of _4 minutes_ to present the work, and will be assigned a specific time slot by the instructor. 

- Presentations should focus on key aspects such as design decisions, implementation challenges, performance analysis, and lessons learned. 

- Students that choose not to present will not be penalized; their grade will be based entirely on the report and implementation. 

The schedule for the presentations will be communicated in advance so that each student knows exactly when they will be presenting. 


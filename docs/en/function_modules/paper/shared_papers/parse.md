# Parsing and medata extraction

we conduct detailed parsing and content extraction of the collected papers to ensure precise retrieval.

## **Source analysis**:
We analyze the source of a PDF document through various methods including
structured PDF parsing, keyword frequency analysis, LLM-assisted analysis.
such as from `Nature`, `IEEE`, etc.
For details, refer to **Code docs**:`Fun_modules.paper.parse.extractors.source_analyze`

## **Structured parsing for papers**:
Based on the analyzed paper source, we use the corresponding parsing templates to parse the document, 
extracting sections such as `Abstract`, `MainText`, `Methods`, `References`, etc., 
to enable more precise literature database retrieval.

Labridge support the following parsing templates now：
  - Nature Parser: refer to **Code docs** `Fun_modules.paper.parse.parsers.nature_parser`
  - IEEE Parser: refer to **Code docs** `Fun_modules.paper.parse.parsers.ieee_parser`

## **Metadata Extraction**:
Labridge utilizes LLM (Large Language Models) to extract metadata from literature, 
such as **article title**, **article keywords**, **author information**, **author affiliation**, **publication date**, etc. 
Papers downloaded from journal websites by Labridge often already contains sufficient metadata. 
For such documents, this step involves supplementing any metadata that is not already provided.

Refer to **Code docs** `Fun_modules.paper.parse.extractors.metadata_extract` for details.

<figure class="figure-image">
  <img src="\assets\images\function_modules\paper\shared_papers\parse.png" alt="Example" />
  <figcaption>Metadata Extraction Example</figcaption>
</figure>
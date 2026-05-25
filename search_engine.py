import requests
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

def clean_doi(doi_str):
    if not doi_str:
        return None
    doi_str = doi_str.strip().lower()
    for prefix in ["https://doi.org/", "http://doi.org/", "doi:"]:
        if doi_str.startswith(prefix):
            doi_str = doi_str[len(prefix):]
    return doi_str

def parse_openalex_work(work):
    """Extracts unified metadata from an OpenAlex work record."""
    doi = clean_doi(work.get("doi"))
    title = work.get("title") or "Untitled Document"
    
    # Extract authors
    authors_list = []
    for a in work.get("authorships", []):
        name = a.get("author", {}).get("display_name")
        if name:
            authors_list.append(name)
    authors = ", ".join(authors_list) if authors_list else "Unknown Author(s)"
    
    year = work.get("publication_year")
    
    # Extract journal / source name
    source = None
    primary_loc = work.get("primary_location")
    if primary_loc:
        source_info = primary_loc.get("source")
        if source_info:
            source = source_info.get("display_name")
    if not source:
        source = "Unknown Source"
        
    # Get all unique PDF URLs
    pdf_urls = []
    best_oa = work.get("best_oa_location")
    if best_oa and best_oa.get("pdf_url"):
        pdf_urls.append(best_oa.get("pdf_url"))
        
    for loc in work.get("locations", []):
        if loc and loc.get("pdf_url"):
            p_url = loc.get("pdf_url")
            if p_url not in pdf_urls:
                pdf_urls.append(p_url)
                
    pdf_url = pdf_urls[0] if pdf_urls else None
                
    # Reconstruct abstract
    abstract = None
    abstract_index = work.get("abstract_inverted_index")
    if abstract_index:
        try:
            word_positions = []
            for word, positions in abstract_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort()
            abstract = " ".join([word for pos, word in word_positions])
        except Exception:
            pass

    return {
        "doi": doi,
        "title": title,
        "authors": authors,
        "year": year,
        "source": source,
        "pdf_url": pdf_url,
        "pdf_urls": pdf_urls,
        "language": work.get("language"),
        "database": "OpenAlex",
        "abstract": abstract or "Resumo não disponível."
    }

def search_openalex(query, limit, email=None, language=None):
    """Searches OpenAlex API for open access papers matching query."""
    url = "https://api.openalex.org/works"
    
    filters = ["is_oa:true"]
    if language in ["en", "pt"]:
        filters.append(f"language:{language}")
        
    # OpenAlex works best when search keywords are clean
    params = {
        "search": query,
        "filter": ",".join(filters),
        "per_page": min(limit * 2, 100) # Fetch more to have a buffer for items without PDF URLs
    }
    
    headers = {}
    if email:
        headers["User-Agent"] = f"mailto:{email}"
    else:
        headers["User-Agent"] = "OpenAccessDownloader/1.0 (mailto:open_access_downloader@example.com)"
        
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        
        parsed_results = []
        for work in results:
            parsed = parse_openalex_work(work)
            # Only keep works with PDF URL or we can keep all and show download availability
            parsed_results.append(parsed)
        return parsed_results
    except Exception as e:
        print(f"OpenAlex Search Error: {e}")
        return []

def search_crossref(query, limit, email=None):
    """Searches Crossref API for papers matching query."""
    url = "https://api.crossref.org/works"
    
    params = {
        "query": query,
        "rows": min(limit * 2, 100)
    }
    
    headers = {}
    if email:
        headers["User-Agent"] = f"mailto:{email}"
    else:
        headers["User-Agent"] = "OpenAccessDownloader/1.0 (mailto:open_access_downloader@example.com)"
        
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        items = data.get("message", {}).get("items", [])
        
        parsed_results = []
        for item in items:
            doi = clean_doi(item.get("DOI"))
            title = item.get("title", ["Untitled Document"])[0] if item.get("title") else "Untitled Document"
            
            # Extract authors
            authors_list = []
            for author in item.get("author", []):
                given = author.get("given", "")
                family = author.get("family", "")
                name = f"{given} {family}".strip()
                if name:
                    authors_list.append(name)
            authors = ", ".join(authors_list) if authors_list else "Unknown Author(s)"
            
            # Extract year
            year = None
            for date_field in ["published-print", "published-online", "created"]:
                if date_field in item and "date-parts" in item[date_field]:
                    parts = item[date_field]["date-parts"]
                    if parts and parts[0]:
                        year = parts[0][0]
                        break
            
            source = item.get("container-title", ["Unknown Source"])[0] if item.get("container-title") else "Unknown Source"
            
            # Crossref may have direct PDF links in its response
            pdf_url = None
            links = item.get("link", [])
            for l in links:
                if "pdf" in l.get("content-type", "") or l.get("intended-application") == "similarity-checking":
                    pdf_url = l.get("URL")
                    # If we found a PDF, break
                    if pdf_url and ".pdf" in pdf_url.lower():
                        break
            
            pdf_urls = [pdf_url] if pdf_url else []
            
            # Extract and clean abstract from Crossref JATS XML
            abstract = None
            raw_abstract = item.get("abstract")
            if raw_abstract:
                # Remove JATS XML tags
                abstract = re.sub(r'<[^>]+>', '', raw_abstract)
                # Remove extra spaces/newlines
                abstract = re.sub(r'\s+', ' ', abstract).strip()

            parsed_results.append({
                "doi": doi,
                "title": title,
                "authors": authors,
                "year": year,
                "source": source,
                "pdf_url": pdf_url,
                "pdf_urls": pdf_urls,
                "language": item.get("language"),
                "database": "Crossref",
                "abstract": abstract or "Resumo não disponível."
            })
        return parsed_results
    except Exception as e:
        print(f"Crossref Search Error: {e}")
        return []

def resolve_dois_in_openalex(dois, email=None):
    """Resolves a list of DOIs in OpenAlex to check for OA status and retrieve PDF links in batch."""
    if not dois:
        return {}
        
    url = "https://api.openalex.org/works"
    
    # OpenAlex filter allows up to 50 DOIs at once separated by |
    headers = {}
    if email:
        headers["User-Agent"] = f"mailto:{email}"
    else:
        headers["User-Agent"] = "OpenAccessDownloader/1.0 (mailto:open_access_downloader@example.com)"
        
    resolved_map = {}
    
    # Process in chunks of 50
    chunk_size = 50
    for i in range(0, len(dois), chunk_size):
        chunk = dois[i:i + chunk_size]
        dois_prefixed = [f"https://doi.org/{d}" for d in chunk]
        doi_filter = f"doi:{'|'.join(dois_prefixed)}"
        
        params = {"filter": doi_filter, "per_page": len(chunk)}
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            
            for work in results:
                parsed = parse_openalex_work(work)
                if parsed["doi"]:
                    resolved_map[parsed["doi"]] = parsed
        except Exception as e:
            print(f"OpenAlex Batch Resolve Error: {e}")
            
    return resolved_map

def search_all(query, limit, email=None, language=None):
    """
    Runs search on both OpenAlex and Crossref.
    Checks Crossref results against OpenAlex to verify OA status and obtain PDF links.
    Merges, deduplicates, and limits the final list to works with valid PDF download links.
    """
    # Run searches in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_oa = executor.submit(search_openalex, query, limit, email, language)
        future_cr = executor.submit(search_crossref, query, limit, email)
        
        oa_results = future_oa.result()
        cr_results = future_cr.result()
        
    # We will merge results in a DOI-indexed dictionary
    merged_results = {}
    
    # Process OpenAlex results first (they are already confirmed open-access and language filtered)
    for work in oa_results:
        # Only include works that have a valid pdf_url
        if work["pdf_url"]:
            doi = work["doi"]
            if doi:
                merged_results[doi] = work
            else:
                # If no DOI, use PDF URL as a unique key for deduplication
                merged_results[work["pdf_url"]] = work
                
    # Now, process Crossref results
    # To determine OA status of Crossref results that don't already have a confirmed PDF URL,
    # we collect their DOIs and check them in OpenAlex in batch.
    cr_dois_to_resolve = []
    cr_by_doi = {}
    
    for work in cr_results:
        doi = work["doi"]
        if not doi:
            # If no DOI, but we have a pdf_url from Crossref, we can add it directly
            if work["pdf_url"]:
                if language and work.get("language") != language:
                    continue
                merged_results[work["pdf_url"]] = work
            continue
            
        cr_by_doi[doi] = work
        
        # If it's already in OpenAlex results, update database tag and skip
        if doi in merged_results:
            merged_results[doi]["database"] = "OpenAlex + Crossref"
            continue
            
        # If Crossref didn't give us a direct PDF URL, or we want to confirm OA status,
        # we queue it for resolving in OpenAlex.
        cr_dois_to_resolve.append(doi)
        
    if cr_dois_to_resolve:
        resolved_map = resolve_dois_in_openalex(cr_dois_to_resolve, email)
        for doi in cr_dois_to_resolve:
            if doi in resolved_map:
                oa_resolved = resolved_map[doi]
                # If resolved work has a PDF URL, it's open access and downloadable!
                if oa_resolved["pdf_url"]:
                    # Check language if requested
                    if language and oa_resolved.get("language") != language:
                        continue
                        
                    # Merge metadata, preferring Crossref source if OpenAlex's is generic
                    cr_work = cr_by_doi[doi]
                    merged_results[doi] = {
                        "doi": doi,
                        "title": cr_work["title"] or oa_resolved["title"],
                        "authors": cr_work["authors"] or oa_resolved["authors"],
                        "year": cr_work["year"] or oa_resolved["year"],
                        "source": cr_work["source"] if cr_work["source"] != "Unknown Source" else oa_resolved["source"],
                        "pdf_url": oa_resolved["pdf_url"],
                        "pdf_urls": oa_resolved.get("pdf_urls", [oa_resolved["pdf_url"]]),
                        "language": oa_resolved.get("language"),
                        "database": "Crossref (OA via OpenAlex)",
                        "abstract": cr_work.get("abstract") if cr_work.get("abstract") != "Resumo não disponível." else (oa_resolved.get("abstract") or "Resumo não disponível.")
                    }
            else:
                # If not found in OpenAlex, but Crossref gave us a PDF link, we can keep it as a fallback
                cr_work = cr_by_doi[doi]
                if cr_work["pdf_url"]:
                    if language and cr_work.get("language") != language:
                        continue
                    merged_results[doi] = cr_work
                    
    # Convert back to list and sort/limit
    final_list = list(merged_results.values())
    
    # Sort results by publication year (descending) so user gets newest papers first, or keep order
    # Let's sort by year if present (using 0 as fallback for sorting)
    final_list.sort(key=lambda x: x.get("year") or 0, reverse=True)
    
    # Return limited results
    return final_list[:limit]

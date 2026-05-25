import os
import re
import zipfile
import tempfile
import shutil
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def sanitize_filename(name):
    """Sanitizes a string to be a safe filename across OS platforms."""
    # Replace invalid characters with underscore
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    # Remove non-ascii characters or keep them depending on OS, but simple stripping/replacing is safer
    name = name.strip()
    # Limit length to avoid path length limits
    if len(name) > 100:
        name = name[:100]
    return name

def download_pdf(pdf_url, output_path, headers=None):
    """Downloads a PDF file from a URL to output_path."""
    if not headers:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive"
        }
    try:
        response = requests.get(pdf_url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
        
        # Verify content type to prevent downloading HTML paywalls or login portals
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            return False, "URL returned HTML landing page instead of PDF"
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True, None
    except Exception as e:
        return False, str(e)

def download_and_zip_selected(articles, output_zip_path, progress_callback=None, max_workers=5):
    """
    Downloads selected articles concurrently and packages them into a ZIP archive.
    
    :param articles: List of article dicts to download.
    :param output_zip_path: Target path for the ZIP file.
    :param progress_callback: Function called with (current, total, status_text) to update progress.
    :param max_workers: Number of concurrent downloads.
    """
    total = len(articles)
    if total == 0:
        if progress_callback:
            progress_callback(0, 0, "No articles selected.")
        return False, "No articles selected."

    # Use a temporary directory inside the system temp folder or current workspace
    # Since TemporaryDirectory cleans up automatically when exiting the context block, it is perfect.
    with tempfile.TemporaryDirectory(prefix="oa_downloads_") as temp_dir:
        downloaded_files = []
        downloaded_count = 0
        failed_count = 0
        
        if progress_callback:
            progress_callback(0, total, "Starting downloads...")
            
        def download_task(idx, article):
            # Try multiple PDF source locations in order
            pdf_urls = article.get("pdf_urls") or []
            if not pdf_urls and article.get("pdf_url"):
                pdf_urls = [article.get("pdf_url")]
                
            title = article.get("title", f"article_{idx}")
            year = article.get("year", "unknown_year")
            
            # Format filename: Title (Year).pdf
            safe_title = sanitize_filename(title)
            filename = f"{safe_title} ({year}).pdf"
            dest_path = os.path.join(temp_dir, filename)
            
            # Ensure unique filename if duplicate titles exist
            counter = 1
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(dest_path):
                dest_path = os.path.join(temp_dir, f"{base_name}_{counter}{ext}")
                counter += 1
                
            if not pdf_urls:
                return False, "No download URLs available", dest_path, title
                
            success = False
            errs = []
            
            from urllib.parse import urlparse
            for url in pdf_urls:
                domain = urlparse(url).netloc or "unknown_domain"
                success, err = download_pdf(url, dest_path)
                if success:
                    break
                else:
                    errs.append(f"{domain}: {err}")
                    
            if not success:
                err_msg = "; ".join(errs) if errs else "Download failed"
                return False, err_msg, dest_path, title
                
            return True, None, dest_path, title

        # Run downloads in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_article = {
                executor.submit(download_task, idx, art): art
                for idx, art in enumerate(articles)
            }
            
            for future in as_completed(future_to_article):
                art = future_to_article[future]
                success, err, filepath, title_text = future.result()
                
                downloaded_count += 1
                if success:
                    downloaded_files.append(filepath)
                    status = f"Downloaded ({downloaded_count}/{total}): {title_text[:40]}..."
                else:
                    failed_count += 1
                    status = f"Failed ({downloaded_count}/{total}): {title_text[:40]}... (Error: {err})"
                    
                if progress_callback:
                    progress_callback(downloaded_count, total, status)
                    
        # Now, create the ZIP file if we have any downloaded files
        if not downloaded_files:
            if progress_callback:
                progress_callback(total, total, "All downloads failed.")
            return False, "All downloads failed. No files to package."
            
        if progress_callback:
            progress_callback(total, total, f"Packaging {len(downloaded_files)} files into ZIP archive...")
            
        try:
            # Ensure target directory for zip exists
            zip_dir = os.path.dirname(output_zip_path)
            if zip_dir and not os.path.exists(zip_dir):
                os.makedirs(zip_dir, exist_ok=True)
                
            with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in downloaded_files:
                    # Write file into zip with its basename
                    zip_file.write(file_path, os.path.basename(file_path))
                    
            summary_msg = f"Done! Saved ZIP to {os.path.basename(output_zip_path)}. Successfully downloaded {len(downloaded_files)}/{total} papers."
            if failed_count > 0:
                summary_msg += f" ({failed_count} failed)"
                
            if progress_callback:
                progress_callback(total, total, summary_msg)
            return True, summary_msg
        except Exception as e:
            err_msg = f"Failed to package ZIP archive: {e}"
            if progress_callback:
                progress_callback(total, total, err_msg)
            return False, err_msg

def download_selected_to_folder(articles, output_dir, progress_callback=None, max_workers=5):
    """
    Downloads selected articles concurrently directly to a target output directory.
    """
    total = len(articles)
    if total == 0:
        if progress_callback:
            progress_callback(0, 0, "Nenhum artigo selecionado.")
        return False, "Nenhum artigo selecionado."

    os.makedirs(output_dir, exist_ok=True)
    downloaded_count = 0
    failed_count = 0
    success_files = []
    
    if progress_callback:
        progress_callback(0, total, "Iniciando downloads...")
        
    def download_task(idx, article):
        pdf_urls = article.get("pdf_urls") or []
        if not pdf_urls and article.get("pdf_url"):
            pdf_urls = [article.get("pdf_url")]
            
        title = article.get("title", f"artigo_{idx}")
        year = article.get("year", "ano_desconhecido")
        
        # If target_path is pre-specified (e.g. from conflict resolution), use it
        dest_path = article.get("target_path")
        if not dest_path:
            safe_title = sanitize_filename(title)
            filename = f"{safe_title} ({year}).pdf"
            dest_path = os.path.join(output_dir, filename)
            
            # Ensure unique filename if duplicate titles exist
            counter = 1
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(dest_path):
                dest_path = os.path.join(output_dir, f"{base_name}_{counter}{ext}")
                counter += 1
            
        if not pdf_urls:
            return False, "Nenhum link PDF disponível", dest_path, title
            
        success = False
        errs = []
        
        from urllib.parse import urlparse
        for url in pdf_urls:
            domain = urlparse(url).netloc or "unknown"
            success, err = download_pdf(url, dest_path)
            if success:
                break
            else:
                errs.append(f"{domain}: {err}")
                
        if not success:
            err_msg = "; ".join(errs) if errs else "Falha no download"
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            return False, err_msg, dest_path, title
            
        return True, None, dest_path, title

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_article = {
            executor.submit(download_task, idx, art): art
            for idx, art in enumerate(articles)
        }
        
        for future in as_completed(future_to_article):
            art = future_to_article[future]
            success, err, filepath, title_text = future.result()
            
            downloaded_count += 1
            if success:
                success_files.append(filepath)
                status = f"Baixado ({downloaded_count}/{total}): {title_text[:40]}..."
            else:
                failed_count += 1
                status = f"Falha ({downloaded_count}/{total}): {title_text[:40]}... (Erro: {err})"
                
            if progress_callback:
                progress_callback(downloaded_count, total, status)
                
    summary_msg = f"Concluído! Salvo na pasta 'downloads'. Sucesso: {len(success_files)}/{total}."
    if failed_count > 0:
        summary_msg += f" ({failed_count} falhas)"
        
    if progress_callback:
        progress_callback(total, total, summary_msg)
    return len(success_files) > 0, summary_msg


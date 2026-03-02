#!/usr/bin/env python3
"""
FastAPI route handlers for the CodeWiki web application.
"""

from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import asdict

from traceback import format_exc

from fastapi import Form, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from .models import JobStatus, JobStatusResponse, GenerationOptions
from .github_processor import GitHubRepoProcessor
from .background_worker import BackgroundWorker
from .cache_manager import CacheManager
from .templates import ADMIN_TEMPLATE
from .template_utils import render_template
from .config import WebAppConfig
from codewiki.src.utils import file_manager


class WebRoutes:
    """Handles all web routes for the application."""
    
    def __init__(self, background_worker: BackgroundWorker, cache_manager: CacheManager):
        self.background_worker = background_worker
        self.cache_manager = cache_manager
    
    async def index_get(self, request: Request) -> HTMLResponse:
        """Main page with form for submitting Git repositories."""
        recent_jobs = self._collect_completed_docs()
        
        context = {
            "message": None,
            "message_type": None,
            "repo_url": "",
            "commit_id": "",
            "recent_jobs": recent_jobs
        }
        
        return HTMLResponse(content=render_template(WEB_INTERFACE_TEMPLATE, context))
    
    async def index_post(
        self,
        request: Request,
        repo_url: str = Form(...),
        commit_id: str = Form(""),
    ) -> HTMLResponse:
        """Handle repository submission."""
        # Clean up old jobs before processing
        self.cleanup_old_jobs()
        
        message = None
        message_type = None
        
        repo_url = repo_url.strip()
        commit_id = commit_id.strip() if commit_id else ""
        
        if not repo_url:
            message = "Please enter a Git repository URL"
            message_type = "error"
        elif not GitHubRepoProcessor.is_valid_github_url(repo_url):
            message = "Please enter a valid Git repository URL (GitHub, GitLab, or any Git repository)"
            message_type = "error"
        else:
            # Normalize the repo URL for comparison
            normalized_repo_url = self._normalize_github_url(repo_url)
            
            # Get repo info for job ID generation
            repo_info = GitHubRepoProcessor.get_repo_info(normalized_repo_url)
            job_id = self._repo_full_name_to_job_id(repo_info['full_name'])
            title = GitHubRepoProcessor.generate_title(normalized_repo_url)
            
            # Check if already in queue, processing, or recently failed
            existing_job = self.background_worker.get_job_status(job_id)
            recent_cutoff = datetime.now() - timedelta(minutes=WebAppConfig.RETRY_COOLDOWN_MINUTES)
            
            if existing_job:
                if existing_job.status in ['queued', 'processing']:
                    pass  # Will handle below
                elif existing_job.status == 'failed' and existing_job.created_at > recent_cutoff:
                    pass  # Will handle below
                else:
                    existing_job = None  # Job is old or completed, can reuse
            
            if existing_job:
                if existing_job.status in ['queued', 'processing']:
                    message = f"Repository is already being processed (Job ID: {existing_job.job_id})"
                else:
                    message = f"Repository recently failed processing. Please wait a few minutes before retrying (Job ID: {existing_job.job_id})"
                message_type = "error"
            else:
                # Check cache
                cached_docs = self.cache_manager.get_cached_docs(normalized_repo_url)
                if cached_docs and Path(cached_docs).exists():
                    message = "Documentation found in cache! Redirecting to view..."
                    message_type = "success"
                    # Create a dummy completed job for display
                    job = JobStatus(
                        job_id=job_id,
                        repo_url=normalized_repo_url,  # Use normalized URL
                        title=title,
                        status='completed',
                        created_at=datetime.now(),
                        completed_at=datetime.now(),
                        docs_path=cached_docs,
                        progress="Retrieved from cache",
                        commit_id=commit_id if commit_id else None
                    )
                    self.background_worker.job_status[job_id] = job
                else:
                    # Add to queue
                    try:
                        job = JobStatus(
                            job_id=job_id,
                            repo_url=normalized_repo_url,  # Use normalized URL
                            title=title,
                            status='queued',
                            created_at=datetime.now(),
                            progress="Waiting in queue...",
                            commit_id=commit_id if commit_id else None
                        )
                        
                        self.background_worker.add_job(job_id, job)
                        message = f"Repository added to processing queue! Job ID: {job_id}"
                        message_type = "success"
                        repo_url = ""  # Clear form
                        
                    except Exception as e:
                        message = f"Failed to add repository to queue: {str(e)}\n{format_exc()}"
                        message_type = "error"
        
        recent_jobs = self._collect_completed_docs()
        
        context = {
            "message": message,
            "message_type": message_type,
            "repo_url": repo_url or "",
            "commit_id": commit_id or "",
            "recent_jobs": recent_jobs
        }
        
        return HTMLResponse(content=render_template(WEB_INTERFACE_TEMPLATE, context))
    
    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        """API endpoint to get job status."""
        job = self.background_worker.get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobStatusResponse(**asdict(job))
    
    async def view_docs(self, job_id: str) -> RedirectResponse:
        """View generated documentation."""
        job = self.background_worker.get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != 'completed' or not job.docs_path:
            raise HTTPException(status_code=404, detail="Documentation not available")
        
        docs_path = Path(job.docs_path)
        if not docs_path.exists():
            raise HTTPException(status_code=404, detail="Documentation files not found")
        
        # Redirect to the documentation viewer
        return RedirectResponse(url=f"/static-docs/{job_id}/", status_code=status.HTTP_302_FOUND)
    
    async def serve_generated_docs(self, job_id: str, filename: str = "overview.md") -> HTMLResponse:
        """Serve generated documentation files."""
        job = self.background_worker.get_job_status(job_id)
        docs_path = None
        repo_url = None
        
        if job:
            # Job status exists - use it
            if job.status != 'completed' or not job.docs_path:
                raise HTTPException(status_code=404, detail="Documentation not available")
            docs_path = Path(job.docs_path)
            repo_url = job.repo_url
        else:
            # No job status - try to find documentation in cache by job_id
            # Convert job_id back to repo full name
            repo_full_name = self._job_id_to_repo_full_name(job_id)
            
            # Try multiple URL formats to find cached documentation
            # 1. Try GitHub URL (most common)
            potential_repo_url = f"https://github.com/{repo_full_name}"
            cached_docs = self.cache_manager.get_cached_docs(potential_repo_url)
            
            # 2. If not found, try GitLab URL
            if not cached_docs:
                potential_repo_url = f"https://gitlab.com/{repo_full_name}"
                cached_docs = self.cache_manager.get_cached_docs(potential_repo_url)
            
            # 3. If still not found, search all cache entries for matching full_name
            if not cached_docs:
                for repo_hash, entry in self.cache_manager.cache_index.items():
                    try:
                        entry_repo_info = GitHubRepoProcessor.get_repo_info(entry.repo_url)
                        if entry_repo_info['full_name'] == repo_full_name:
                            cached_docs = entry.docs_path
                            potential_repo_url = entry.repo_url
                            break
                    except Exception:
                        continue
            
            if cached_docs and Path(cached_docs).exists():
                docs_path = Path(cached_docs)
                repo_url = potential_repo_url
                
                # Recreate job status for consistency
                job = JobStatus(
                    job_id=job_id,
                    repo_url=potential_repo_url,
                    status='completed',
                    created_at=datetime.now(),
                    completed_at=datetime.now(),
                    docs_path=cached_docs,
                    progress="Loaded from cache",
                    commit_id=None  # No commit info available from cache
                )
                self.background_worker.job_status[job_id] = job
                self.background_worker.save_job_statuses()
            else:
                raise HTTPException(status_code=404, detail="Documentation not found")
        
        if not docs_path or not docs_path.exists():
            raise HTTPException(status_code=404, detail="Documentation files not found")
        
        # Load module tree
        module_tree = None
        module_tree_file = docs_path / "module_tree.json"
        if module_tree_file.exists():
            try:
                module_tree = file_manager.load_json(module_tree_file)
            except Exception:
                pass
        
        # Load metadata
        metadata = None
        metadata_file = docs_path / "metadata.json"
        if metadata_file.exists():
            try:
                metadata = file_manager.load_json(metadata_file)
            except Exception:
                pass
        
        # Serve the requested file
        file_path = docs_path / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File {filename} not found")
        
        try:
            content = file_manager.load_text(file_path)
            
            # Convert markdown to HTML (reuse from visualise_docs.py)
            from .visualise_docs import markdown_to_html, get_file_title
            from .templates import DOCS_VIEW_TEMPLATE
            
            html_content = markdown_to_html(content)
            title = get_file_title(file_path)
            
            context = {
                "repo_name": repo_url.split("/")[-1],
                "title": title,
                "content": html_content,
                "navigation": module_tree,
                "current_page": filename,
                "job_id": job_id,
                "metadata": metadata
            }
            
            return HTMLResponse(content=render_template(DOCS_VIEW_TEMPLATE, context))
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading {filename}: {e}\n{format_exc()}")
    
    def _normalize_github_url(self, url: str) -> str:
        """Normalize Git repository URL for consistent comparison."""
        try:
            # Get repo info to standardize the URL format
            repo_info = GitHubRepoProcessor.get_repo_info(url)
            # For SSH URLs, use the original URL; for HTTP URLs, use the standard format
            if url.startswith('ssh://') or ('@' in url and ':' in url and not url.startswith('http')):
                return url
            else:
                return f"https://{repo_info['domain']}/{repo_info['full_name']}"
        except Exception:
            # Fallback to basic normalization
            return url.rstrip('/').lower()
    
    def _repo_full_name_to_job_id(self, full_name: str) -> str:
        """Convert repo full name to URL-safe job ID."""
        return full_name.replace('/', '--')
    
    def _job_id_to_repo_full_name(self, job_id: str) -> str:
        """Convert job ID back to repo full name."""
        return job_id.replace('--', '/')
    
    def cleanup_old_jobs(self):
        """Clean up old job status entries."""
        cutoff = datetime.now() - timedelta(hours=WebAppConfig.JOB_CLEANUP_HOURS)
        all_jobs = self.background_worker.get_all_jobs()
        expired_jobs = [
            job_id for job_id, job in all_jobs.items()
            if job.created_at < cutoff and job.status in ['completed', 'failed']
        ]
        
        for job_id in expired_jobs:
            if job_id in self.background_worker.job_status:
                del self.background_worker.job_status[job_id]

    def _collect_completed_docs(self):
        """Collect completed docs from job status and cache index."""
        completed = {}
        
        all_jobs = self.background_worker.get_all_jobs()
        for job in all_jobs.values():
            if job.status == 'completed' and job.docs_path:
                completed[job.job_id] = job
        
        # Add cached docs that aren't tracked in job status
        for entry in self.cache_manager.cache_index.values():
            if not entry.docs_path or not Path(entry.docs_path).exists():
                continue
            try:
                repo_info = GitHubRepoProcessor.get_repo_info(entry.repo_url)
                job_id = self._repo_full_name_to_job_id(repo_info['full_name'])
            except Exception:
                continue
            
            if job_id in completed:
                continue
            
            completed[job_id] = JobStatus(
                job_id=job_id,
                repo_url=entry.repo_url,
                title=GitHubRepoProcessor.generate_title(entry.repo_url),
                status='completed',
                created_at=entry.created_at,
                completed_at=entry.created_at,
                docs_path=entry.docs_path,
                progress="Retrieved from cache",
                commit_id=None
            )
        
        return sorted(
            completed.values(),
            key=lambda x: x.completed_at or x.created_at,
            reverse=True
        )
    
    async def list_tasks(self, status_filter: str = None) -> JSONResponse:
        """API endpoint to list all tasks with optional status filter."""
        all_jobs = self.background_worker.get_all_jobs()
        jobs_list = []
        
        for job_id, job in all_jobs.items():
            if status_filter and job.status != status_filter:
                continue
            jobs_list.append(JobStatusResponse(
                job_id=job.job_id,
                repo_url=job.repo_url,
                title=job.title or GitHubRepoProcessor.generate_title(job.repo_url),
                status=job.status,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                error_message=job.error_message,
                progress=job.progress,
                docs_path=job.docs_path,
                main_model=job.main_model,
                commit_id=job.commit_id,
                priority=job.priority,
                options=job.options
            ))
        
        jobs_list.sort(key=lambda x: x.created_at, reverse=True)
        return JSONResponse(content=jsonable_encoder(jobs_list))
    
    async def create_task_api(
        self,
        repo_url: str,
        commit_id: str = "",
        priority: int = 0,
        output: str = "docs/codewiki",
        create_branch: bool = False,
        github_pages: bool = False,
        no_cache: bool = False,
        include: str = "",
        exclude: str = "",
        focus: str = "",
        doc_type: str = "",
        instructions: str = "",
        max_tokens: str = "",
        max_token_per_module: str = "",
        max_token_per_leaf_module: str = "",
        max_depth: str = "",
        output_lang: str = "",
        agent_cmd: str = "",
        concurrency: int = 4
    ) -> JSONResponse:
        """API endpoint to create a new task."""
        repo_url = repo_url.strip()
        commit_id = commit_id.strip() if commit_id else ""
        
        if not repo_url:
            raise HTTPException(status_code=400, detail="Repository URL is required")
        
        if not GitHubRepoProcessor.is_valid_github_url(repo_url):
            raise HTTPException(status_code=400, detail="Invalid Git repository URL")
        
        normalized_repo_url = self._normalize_github_url(repo_url)
        repo_info = GitHubRepoProcessor.get_repo_info(normalized_repo_url)
        job_id = self._repo_full_name_to_job_id(repo_info['full_name'])
        title = GitHubRepoProcessor.generate_title(normalized_repo_url)
        
        options = GenerationOptions(
            output=output.strip() if output and output.strip() != "docs/codewiki" else None,
            create_branch=create_branch,
            github_pages=github_pages,
            no_cache=no_cache,
            include=include.strip() if include and include.strip() else None,
            exclude=exclude.strip() if exclude and exclude.strip() else None,
            focus=focus.strip() if focus and focus.strip() else None,
            doc_type=doc_type.strip() if doc_type and doc_type.strip() else None,
            instructions=instructions.strip() if instructions and instructions.strip() else None,
            max_tokens=int(max_tokens) if max_tokens and max_tokens.isdigit() else None,
            max_token_per_module=int(max_token_per_module) if max_token_per_module and max_token_per_module.isdigit() else None,
            max_token_per_leaf_module=int(max_token_per_leaf_module) if max_token_per_leaf_module and max_token_per_leaf_module.isdigit() else None,
            max_depth=int(max_depth) if max_depth and max_depth.isdigit() else None,
            output_lang=output_lang.strip() if output_lang and output_lang.strip() else None,
            agent_cmd=agent_cmd.strip() if agent_cmd and agent_cmd.strip() else None,
            concurrency=concurrency
        )
        
        existing_job = self.background_worker.get_job_status(job_id)
        if existing_job and existing_job.status in ['queued', 'processing']:
            raise HTTPException(status_code=409, detail="Task already exists and is in progress")
        
        job = JobStatus(
            job_id=job_id,
            repo_url=normalized_repo_url,
            title=title,
            status='queued',
            created_at=datetime.now(),
            progress="Waiting in queue...",
            commit_id=commit_id if commit_id else None,
            priority=priority,
            options=options
        )
        
        self.background_worker.add_job(job_id, job)
        
        return JSONResponse(content={
            "job_id": job_id,
            "title": title,
            "repo_url": normalized_repo_url,
            "status": "queued",
            "message": "Task created successfully"
        })
    
    async def delete_task(self, job_id: str) -> JSONResponse:
        """API endpoint to delete a task."""
        job = self.background_worker.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if job.status == 'processing':
            raise HTTPException(status_code=400, detail="Cannot delete a task that is currently processing")
        
        if job_id in self.background_worker.job_status:
            del self.background_worker.job_status[job_id]
            self.background_worker.save_job_statuses()
        
        return JSONResponse(content={"message": "Task deleted successfully"})
    
    async def admin_get(self, request: Request) -> HTMLResponse:
        """Admin page for managing tasks."""
        all_jobs = self.background_worker.get_all_jobs()
        jobs_list = sorted(all_jobs.values(), key=lambda x: x.created_at, reverse=True)
        
        queued_count = sum(1 for j in jobs_list if j.status == 'queued')
        processing_count = sum(1 for j in jobs_list if j.status == 'processing')
        completed_count = sum(1 for j in jobs_list if j.status == 'completed')
        failed_count = sum(1 for j in jobs_list if j.status == 'failed')
        
        context = {
            "jobs": jobs_list,
            "queued_count": queued_count,
            "processing_count": processing_count,
            "completed_count": completed_count,
            "failed_count": failed_count,
            "total_count": len(jobs_list)
        }
        
        return HTMLResponse(content=render_template(ADMIN_TEMPLATE, context))
    
    async def admin_post(self, request: Request, 
                         repo_url: str = Form(...), 
                         commit_id: str = Form(""), 
                         priority: int = Form(0),
                         output: str = Form("docs/codewiki"),
                         create_branch: bool = Form(False),
                         github_pages: bool = Form(False),
                         no_cache: bool = Form(False),
                         include: str = Form(""),
                         exclude: str = Form(""),
                         focus: str = Form(""),
                         doc_type: str = Form(""),
                         instructions: str = Form(""),
                         max_tokens: str = Form(""),
                         max_token_per_module: str = Form(""),
                         max_token_per_leaf_module: str = Form(""),
                         max_depth: str = Form(""),
                         output_lang: str = Form(""),
                         agent_cmd: str = Form(""),
                         concurrency: int = Form(4)) -> HTMLResponse:
        """Handle task submission from admin page."""
        repo_url = repo_url.strip()
        commit_id = commit_id.strip() if commit_id else ""
        
        if not repo_url:
            context = {
                "error": "Repository URL is required",
                "jobs": self.background_worker.get_all_jobs().values()
            }
            return HTMLResponse(content=render_template(ADMIN_TEMPLATE, context), status_code=400)
        
        if not GitHubRepoProcessor.is_valid_github_url(repo_url):
            context = {
                "error": "Invalid Git repository URL",
                "jobs": self.background_worker.get_all_jobs().values()
            }
            return HTMLResponse(content=render_template(ADMIN_TEMPLATE, context), status_code=400)
        
        normalized_repo_url = self._normalize_github_url(repo_url)
        repo_info = GitHubRepoProcessor.get_repo_info(normalized_repo_url)
        job_id = self._repo_full_name_to_job_id(repo_info['full_name'])
        title = GitHubRepoProcessor.generate_title(normalized_repo_url)

        options = GenerationOptions(
            output=output.strip() if output and output.strip() != "docs/codewiki" else None,
            create_branch=create_branch,
            github_pages=github_pages,
            no_cache=no_cache,
            include=include.strip() if include and include.strip() else None,
            exclude=exclude.strip() if exclude and exclude.strip() else None,
            focus=focus.strip() if focus and focus.strip() else None,
            doc_type=doc_type.strip() if doc_type and doc_type.strip() else None,
            instructions=instructions.strip() if instructions and instructions.strip() else None,
            max_tokens=int(max_tokens) if max_tokens and max_tokens.isdigit() else None,
            max_token_per_module=int(max_token_per_module) if max_token_per_module and max_token_per_module.isdigit() else None,
            max_token_per_leaf_module=int(max_token_per_leaf_module) if max_token_per_leaf_module and max_token_per_leaf_module.isdigit() else None,
            max_depth=int(max_depth) if max_depth and max_depth.isdigit() else None,
            output_lang=output_lang.strip() if output_lang and output_lang.strip() else None,
            agent_cmd=agent_cmd.strip() if agent_cmd and agent_cmd.strip() else None,
            concurrency=concurrency
        )
        
        existing_job = self.background_worker.get_job_status(job_id)
        if existing_job and existing_job.status in ['queued', 'processing']:
            context = {
                "error": f"Task already exists and is {existing_job.status}",
                "jobs": self.background_worker.get_all_jobs().values()
            }
            return HTMLResponse(content=render_template(ADMIN_TEMPLATE, context), status_code=409)
        
        cached_docs = self.cache_manager.get_cached_docs(normalized_repo_url)
        if cached_docs and Path(cached_docs).exists() and not options.no_cache:
            job = JobStatus(
                job_id=job_id,
                repo_url=normalized_repo_url,
                title=title,
                status='completed',
                created_at=datetime.now(),
                completed_at=datetime.now(),
                docs_path=cached_docs,
                progress="Retrieved from cache",
                commit_id=commit_id if commit_id else None,
                priority=priority,
                options=options
            )
        else:
            job = JobStatus(
                job_id=job_id,
                repo_url=normalized_repo_url,
                title=title,
                status='queued',
                created_at=datetime.now(),
                progress="Waiting in queue...",
                commit_id=commit_id if commit_id else None,
                priority=priority,
                options=options
            )
            self.background_worker.add_job(job_id, job)
        
        self.background_worker.job_status[job_id] = job
        self.background_worker.save_job_statuses()
        
        return await self.admin_get(request)

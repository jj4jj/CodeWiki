#!/usr/bin/env python3
"""
HTML templates for the CodeWiki web application.
"""

# Web interface HTML template
WEB_INTERFACE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeWiki - Repository Documentation Generator</title>
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #f1f5f9;
            --text-color: #334155;
            --border-color: #e2e8f0;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .header {
            background: var(--primary-color);
            color: white;
            padding: 2rem;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .content {
            padding: 2rem;
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: var(--text-color);
        }
        
        .form-group input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 2px solid var(--border-color);
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.2s ease;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        
        .btn {
            display: inline-block;
            padding: 0.75rem 2rem;
            background: var(--primary-color);
            color: white;
            text-decoration: none;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        
        .btn:hover {
            background: #1d4ed8;
            transform: translateY(-1px);
        }
        
        .btn:disabled {
            background: #94a3b8;
            cursor: not-allowed;
            transform: none;
        }
        
        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        .alert-success {
            background: #dcfce7;
            color: #166534;
            border: 1px solid #bbf7d0;
        }
        
        .alert-error {
            background: #fef2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }
        
        .recent-jobs {
            margin-top: 2rem;
            border-top: 1px solid var(--border-color);
            padding-top: 2rem;
        }
        
        .job-item {
            background: var(--secondary-color);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        .job-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .job-url {
            font-weight: 600;
            color: var(--primary-color);
        }
        
        .job-status {
            padding: 0.25rem 0.75rem;
            border-radius: 16px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .status-queued {
            background: #fef3c7;
            color: #92400e;
        }
        
        .status-processing {
            background: #dbeafe;
            color: #1e40af;
        }
        
        .status-completed {
            background: #dcfce7;
            color: #166534;
        }
        
        .status-failed {
            background: #fef2f2;
            color: #991b1b;
        }
        
        .job-progress {
            font-size: 0.875rem;
            color: #64748b;
            margin-top: 0.25rem;
        }
        
        .job-actions {
            margin-top: 0.5rem;
        }
        
        .btn-small {
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 CodeWiki</h1>
            <p>Generate comprehensive documentation for any Git repository</p>
        </div>
        
        <div class="content">
            {% if message %}
            <div class="alert alert-{{ message_type }}">
                {{ message }}
            </div>
            {% endif %}
            
            <form method="POST" action="/">
                <div class="form-group">
                    <label for="repo_url">Repository URL:</label>
                    <input 
                        type="url" 
                        id="repo_url" 
                        name="repo_url" 
                        placeholder="https://github.com/owner/repository or ssh://git@domain.com:port/owner/repo.git"
                        required
                        value="{{ repo_url or '' }}"
                    >
                </div>
                
                <div class="form-group">
                    <label for="commit_id">Commit ID (optional):</label>
                    <input 
                        type="text" 
                        id="commit_id" 
                        name="commit_id" 
                        placeholder="Enter specific commit hash (defaults to latest)"
                        value="{{ commit_id or '' }}"
                        pattern="[a-f0-9]{4,40}"
                        title="Enter a valid commit hash (4-40 characters, hexadecimal)"
                    >
                </div>
                
                <button type="submit" class="btn">Generate Documentation</button>
            </form>
            
            {% if recent_jobs %}
            <div class="recent-jobs">
                <h3>Recent Jobs</h3>
                {% for job in recent_jobs %}
                <div class="job-item">
                    <div class="job-header">
                        <div class="job-url">{{ job.repo_url }}</div>
                        <div class="job-status status-{{ job.status }}">{{ job.status }}</div>
                    </div>
                    <div class="job-progress">{{ job.progress }}</div>
                    {% if job.main_model %}
                    <div class="job-model" style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">
                        Generated with: {{ job.main_model }}
                    </div>
                    {% endif %}
                    <div class="job-actions">
                        <a href="/docs/{{ job.job_id }}" class="btn btn-small">View Documentation</a>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        // Form submission protection
        let isSubmitting = false;
        
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.querySelector('form');
            const submitButton = document.querySelector('button[type="submit"]');
            
            if (form && submitButton) {
                form.addEventListener('submit', function(e) {
                    if (isSubmitting) {
                        e.preventDefault();
                        return false;
                    }
                    
                    isSubmitting = true;
                    submitButton.disabled = true;
                    submitButton.textContent = 'Processing...';
                    
                    // Re-enable after 10 seconds as a failsafe
                    setTimeout(function() {
                        isSubmitting = false;
                        submitButton.disabled = false;
                        submitButton.textContent = 'Generate Documentation';
                    }, 10000);
                });
            }
            
            // Optional: Add manual refresh button instead of auto-refresh
            const refreshButton = document.createElement('button');
            refreshButton.textContent = 'Refresh Status';
            refreshButton.className = 'btn btn-small';
            refreshButton.style.marginTop = '1rem';
            refreshButton.onclick = function() {
                window.location.reload();
            };
            
            const recentJobsSection = document.querySelector('.recent-jobs');
            if (recentJobsSection) {
                recentJobsSection.appendChild(refreshButton);
            }
        });
    </script>
</body>
</html>
"""

# HTML template for the documentation pages
DOCS_VIEW_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11.9.0/dist/mermaid.min.js"></script>
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #f1f5f9;
            --text-color: #334155;
            --border-color: #e2e8f0;
            --hover-color: #f8fafc;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: #ffffff;
        }
        
        .container {
            display: flex;
            min-height: 100vh;
        }
        
        .sidebar {
            width: 300px;
            background-color: var(--secondary-color);
            border-right: 1px solid var(--border-color);
            padding: 20px;
            overflow-y: auto;
            position: fixed;
            height: 100vh;
        }
        
        .content {
            flex: 1;
            margin-left: 300px;
            padding: 40px 60px;
            max-width: calc(100% - 300px);
        }
        
        .logo {
            font-size: 24px;
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: 30px;
            text-decoration: none;
        }
        
        .nav-section {
            margin-bottom: 25px;
        }
        
        .nav-section h3 {
            font-size: 14px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 10px;
        }
        
        .nav-item {
            display: block;
            padding: 8px 12px;
            color: var(--text-color);
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.2s ease;
            margin-bottom: 2px;
        }
        
        .nav-item:hover {
            background-color: var(--hover-color);
            color: var(--primary-color);
        }
        
        .nav-item.active {
            background-color: var(--primary-color);
            color: white;
        }
        
        .nav-subsection {
            margin-left: 15px;
            margin-top: 8px;
        }
        
        .nav-subsection .nav-item {
            font-size: 13px;
            color: #64748b;
        }
        
        .nav-section-header {
            font-size: 14px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 10px;
            padding: 8px 12px;
        }
        
        /* Nested subsection indentation - scalable for any depth */
        .nav-subsection .nav-subsection {
            margin-left: 20px;
        }
        
        .nav-subsection .nav-subsection .nav-item {
            font-size: 12px;
        }
        
        /* Additional nesting levels */
        .nav-subsection .nav-subsection .nav-subsection {
            margin-left: 15px;
        }
        
        .nav-subsection .nav-subsection .nav-subsection .nav-item {
            font-size: 11px;
        }
        
        .markdown-content {
            max-width: none;
        }
        
        .markdown-content h1 {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 1rem;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        
        .markdown-content h2 {
            font-size: 2rem;
            font-weight: 600;
            color: #334155;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        
        .markdown-content h3 {
            font-size: 1.5rem;
            font-weight: 600;
            color: #475569;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
        }
        
        .markdown-content p {
            margin-bottom: 1rem;
            color: #475569;
        }
        
        .markdown-content ul, .markdown-content ol {
            margin-bottom: 1rem;
            padding-left: 1.5rem;
        }
        
        .markdown-content li {
            margin-bottom: 0.5rem;
            color: #475569;
        }
        
        .markdown-content code {
            background-color: #f1f5f9;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.875rem;
        }
        
        .markdown-content pre {
            background-color: #f8fafc;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 1rem;
            overflow-x: auto;
            margin-bottom: 1rem;
        }
        
        .markdown-content pre code {
            background-color: transparent;
            padding: 0;
        }
        
        .markdown-content blockquote {
            border-left: 4px solid var(--primary-color);
            padding-left: 1rem;
            margin-bottom: 1rem;
            font-style: italic;
            color: #64748b;
        }
        
        .markdown-content table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1rem;
        }
        
        .markdown-content th, .markdown-content td {
            border: 1px solid var(--border-color);
            padding: 0.75rem;
            text-align: left;
        }
        
        .markdown-content th {
            background-color: var(--secondary-color);
            font-weight: 600;
        }
        
        .markdown-content a {
            color: var(--primary-color);
            text-decoration: underline;
        }
        
        .markdown-content a:hover {
            text-decoration: none;
        }
        
        @media (max-width: 768px) {
            .sidebar {
                width: 100%;
                position: relative;
                height: auto;
            }
            
            .content {
                margin-left: 0;
                padding: 20px;
                max-width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <nav class="sidebar">
            <a href="/static-docs/{{ job_id }}/overview.md" class="logo">📚 {{ repo_name }}</a>
            
            {% if metadata and metadata.generation_info %}
            <div style="margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                <h4 style="margin: 0 0 10px 0; font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Generation Info</h4>
                <div style="font-size: 11px; color: #475569; line-height: 1.4;">
                    <div style="margin-bottom: 4px;"><strong>Model:</strong> {{ metadata.generation_info.main_model }}</div>
                    <div style="margin-bottom: 4px;"><strong>Generated:</strong> {{ metadata.generation_info.timestamp[:16] }}</div>
                    {% if metadata.generation_info.commit_id %}
                    <div style="margin-bottom: 4px;"><strong>Commit:</strong> {{ metadata.generation_info.commit_id[:8] }}</div>
                    {% endif %}
                    {% if metadata.statistics %}
                    <div><strong>Components:</strong> {{ metadata.statistics.total_components }}</div>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
            {% if navigation %}
            <div class="nav-section">
                <a href="/static-docs/{{ job_id }}/overview.md" class="nav-item {% if current_page == 'overview.md' %}active{% endif %}">
                    Overview
                </a>
            </div>
            
            {% macro render_nav_item(key, data, depth=0) %}
                {% set indent_class = 'nav-subsection' if depth > 0 else '' %}
                {% set indent_style = 'margin-left: ' + (depth * 15)|string + 'px;' if depth > 0 else '' %}
                <div class="{{ indent_class }}" {% if indent_style %}style="{{ indent_style }}"{% endif %}>
                    {% if data.components %}
                        <a href="/static-docs/{{ job_id }}/{{ key }}.md" class="nav-item {% if current_page == key + '.md' %}active{% endif %}">
                            {{ key.replace('_', ' ').title() }}
                        </a>
                    {% else %}
                        <div class="nav-section-header" {% if depth > 0 %}style="font-size: {{ 14 - (depth * 1) }}px; text-transform: none;"{% endif %}>
                            {{ key.replace('_', ' ').title() }}
                        </div>
                    {% endif %}
                    
                    {% if data.children %}
                        {% for child_key, child_data in data.children.items() %}
                            {{ render_nav_item(child_key, child_data, depth + 1) }}
                        {% endfor %}
                    {% endif %}
                </div>
            {% endmacro %}
            
            {% for section_key, section_data in navigation.items() %}
            <div class="nav-section">
                {{ render_nav_item(section_key, section_data) }}
            </div>
            {% endfor %}
            {% endif %}
        </nav>
        
        <main class="content">
            <div class="markdown-content">
                {{ content | safe }}
            </div>
        </main>
    </div>
    
    <script>
        // Initialize mermaid with configuration
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            themeVariables: {
                primaryColor: '#2563eb',
                primaryTextColor: '#334155',
                primaryBorderColor: '#e2e8f0',
                lineColor: '#64748b',
                sectionBkgColor: '#f8fafc',
                altSectionBkgColor: '#f1f5f9',
                gridColor: '#e2e8f0',
                secondaryColor: '#f1f5f9',
                tertiaryColor: '#f8fafc'
            },
            flowchart: {
                htmlLabels: true,
                curve: 'basis'
            },
            sequence: {
                diagramMarginX: 50,
                diagramMarginY: 10,
                actorMargin: 50,
                width: 150,
                height: 65,
                boxMargin: 10,
                boxTextMargin: 5,
                noteMargin: 10,
                messageMargin: 35,
                mirrorActors: true,
                bottomMarginAdj: 1,
                useMaxWidth: true,
                rightAngles: false,
                showSequenceNumbers: false
            }
        });
        
        // Re-render mermaid diagrams after page load
        document.addEventListener('DOMContentLoaded', function() {
            mermaid.init(undefined, document.querySelectorAll('.mermaid'));
        });
    </script>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - CodeWiki Documentation Platform</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #f1f5f9;
            --text-color: #334155;
            --border-color: #e2e8f0;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --info-color: #06b6d4;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            font-size: 2rem;
            color: var(--primary-color);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .header p {
            color: #64748b;
        }
        
        .nav-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .nav-tab {
            padding: 12px 24px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .nav-tab:hover, .nav-tab.active {
            background: var(--primary-color);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .stat-card h3 {
            font-size: 2rem;
            margin-bottom: 0.25rem;
        }
        
        .stat-card p {
            color: #64748b;
            font-size: 0.875rem;
        }
        
        .stat-card.queued h3 { color: var(--warning-color); }
        .stat-card.processing h3 { color: var(--info-color); }
        .stat-card.completed h3 { color: var(--success-color); }
        .stat-card.failed h3 { color: var(--error-color); }
        
        .content-card {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .form-section {
            margin-bottom: 2rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .form-section h2 {
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--text-color);
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 200px 100px auto;
            gap: 15px;
            align-items: end;
        }
        
        .form-group {
            margin-bottom: 0;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            font-size: 0.875rem;
            color: var(--text-color);
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 2px solid var(--border-color);
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.2s ease;
        }
        
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 0.75rem 1.5rem;
            background: var(--primary-color);
            color: white;
            text-decoration: none;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        
        .btn:hover {
            background: #1d4ed8;
            transform: translateY(-1px);
        }
        
        .btn:disabled {
            background: #94a3b8;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-danger {
            background: var(--error-color);
        }
        
        .btn-danger:hover {
            background: #dc2626;
        }
        
        .btn-success {
            background: var(--success-color);
        }
        
        .btn-success:hover {
            background: #059669;
        }
        
        .jobs-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .jobs-table th, .jobs-table td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        .jobs-table th {
            background: var(--secondary-color);
            font-weight: 600;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
        }
        
        .jobs-table tr:hover {
            background: var(--secondary-color);
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 0.25rem 0.75rem;
            border-radius: 16px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-badge.queued {
            background: #fef3c7;
            color: #92400e;
        }
        
        .status-badge.processing {
            background: #dbeafe;
            color: #1e40af;
        }
        
        .status-badge.completed {
            background: #dcfce7;
            color: #166534;
        }
        
        .status-badge.failed {
            background: #fef2f2;
            color: #991b1b;
        }
        
        .job-title {
            font-weight: 600;
            color: var(--primary-color);
        }
        
        .job-url {
            font-size: 0.75rem;
            color: #64748b;
            word-break: break-all;
        }
        
        .actions {
            display: flex;
            gap: 8px;
        }
        
        .btn-small {
            padding: 0.5rem;
            font-size: 0.875rem;
            border-radius: 6px;
        }
        
        .options-details {
            margin: 1rem 0;
            background: #f8fafc;
            border-radius: 8px;
            padding: 0.5rem;
            border: 1px solid #e2e8f0;
        }
        
        .options-details summary {
            cursor: pointer;
            padding: 0.5rem 1rem;
            font-weight: 600;
            color: #475569;
            list-style: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .options-details summary::-webkit-details-marker {
            display: none;
        }
        
        .options-details summary::before {
            content: '\f196';
            font-family: 'Font Awesome 6 Free';
            font-weight: 900;
            color: #64748b;
        }
        
        .options-details[open] summary::before {
            content: '\f147';
        }
        
        .options-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
            padding: 1rem;
            margin-top: 0.5rem;
        }
        
        .form-group-checkbox {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 0;
        }
        
        .form-group-checkbox input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        
        .form-group-checkbox label {
            cursor: pointer;
            color: #475569;
            font-weight: normal;
        }
        
        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        .alert-error {
            background: #fef2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }
        
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #64748b;
        }
        
        .empty-state i {
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }
        
        .back-link {
            color: white;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 20px;
        }
        
        .back-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">
            <i class="fas fa-arrow-left"></i> Back to Home
        </a>
        
        <div class="header">
            <h1>
                <i class="fas fa-cog"></i>
                Admin Panel
            </h1>
            <p>Manage documentation generation tasks</p>
        </div>
        
        <div class="nav-tabs">
            <a href="/" class="nav-tab">
                <i class="fas fa-home"></i> Home
            </a>
            <a href="/admin" class="nav-tab active">
                <i class="fas fa-tasks"></i> Tasks
            </a>
            <a href="/api/tasks" class="nav-tab" target="_blank">
                <i class="fas fa-code"></i> API
            </a>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card queued">
                <h3><i class="fas fa-clock"></i> {{ queued_count }}</h3>
                <p>Queued</p>
            </div>
            <div class="stat-card processing">
                <h3><i class="fas fa-spinner fa-spin"></i> {{ processing_count }}</h3>
                <p>Processing</p>
            </div>
            <div class="stat-card completed">
                <h3><i class="fas fa-check-circle"></i> {{ completed_count }}</h3>
                <p>Completed</p>
            </div>
            <div class="stat-card failed">
                <h3><i class="fas fa-times-circle"></i> {{ failed_count }}</h3>
                <p>Failed</p>
            </div>
        </div>
        
        <div class="content-card">
            <div class="form-section">
                <h2>
                    <i class="fas fa-plus-circle"></i>
                    Submit New Documentation Task
                </h2>
                
                {% if error %}
                <div class="alert alert-error">
                    {{ error }}
                </div>
                {% endif %}
                
                <form method="POST" action="/admin">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="repo_url">
                                <i class="fas fa-code-branch"></i> Repository URL
                            </label>
                            <input 
                                type="url" 
                                id="repo_url" 
                                name="repo_url" 
                                placeholder="https://github.com/owner/repository or ssh://git@domain.com:port/owner/repo.git"
                                required
                            >
                        </div>
                        
                        <div class="form-group">
                            <label for="commit_id">
                                <i class="fas fa-commit"></i> Commit ID
                            </label>
                            <input 
                                type="text" 
                                id="commit_id" 
                                name="commit_id" 
                                placeholder="Optional"
                            >
                        </div>
                        
                        <div class="form-group">
                            <label for="priority">
                                <i class="fas fa-level-up-alt"></i> Priority
                            </label>
                            <select id="priority" name="priority">
                                <option value="0">Normal</option>
                                <option value="1">High</option>
                                <option value="2">Urgent</option>
                            </select>
                        </div>
                    </div>
                    
                    <details class="options-details">
                        <summary><i class="fas fa-cog"></i> Advanced Options</summary>
                        <div class="options-grid">
                            <div class="form-group">
                                <label for="agent_cmd">
                                    <i class="fas fa-robot"></i> Agent Command
                                </label>
                                <input 
                                    type="text" 
                                    id="agent_cmd" 
                                    name="agent_cmd" 
                                    placeholder="e.g., claude -p or opencode"
                                >
                            </div>

                            <div class="form-group">
                                <label for="output">
                                    <i class="fas fa-folder-open"></i> Output Directory
                                </label>
                                <input 
                                    type="text" 
                                    id="output" 
                                    name="output" 
                                    placeholder="e.g., docs/codewiki"
                                >
                            </div>
                            
                            <div class="form-group">
                                <label for="max_depth">
                                    <i class="fas fa-layer-group"></i> Max Depth
                                </label>
                                <input 
                                    type="number" 
                                    id="max_depth" 
                                    name="max_depth" 
                                    placeholder="Default: unlimited"
                                    min="1"
                                    max="10"
                                >
                            </div>
                            
                            <div class="form-group">
                                <label for="concurrency">
                                    <i class="fas fa-tasks"></i> Concurrency
                                </label>
                                <input 
                                    type="number" 
                                    id="concurrency" 
                                    name="concurrency" 
                                    value="4"
                                    min="1"
                                    max="16"
                                >
                            </div>
                            
                            <div class="form-group">
                                <label for="output_lang">
                                    <i class="fas fa-language"></i> Output Language
                                </label>
                                <input 
                                    type="text" 
                                    id="output_lang" 
                                    name="output_lang" 
                                    placeholder="e.g., zh, ja, en"
                                >
                            </div>
                            
                            <div class="form-group">
                                <label for="max_tokens">
                                    <i class="fas fa-coins"></i> Max Tokens
                                </label>
                                <input 
                                    type="number" 
                                    id="max_tokens" 
                                    name="max_tokens" 
                                    placeholder="Max response tokens"
                                >
                            </div>

                            <div class="form-group">
                                <label for="max_token_per_module">
                                    <i class="fas fa-cubes"></i> Max Tokens Per Module
                                </label>
                                <input 
                                    type="number" 
                                    id="max_token_per_module" 
                                    name="max_token_per_module" 
                                    placeholder="Max tokens per module"
                                >
                            </div>

                            <div class="form-group">
                                <label for="max_token_per_leaf_module">
                                    <i class="fas fa-leaf"></i> Max Tokens Per Leaf Module
                                </label>
                                <input 
                                    type="number" 
                                    id="max_token_per_leaf_module" 
                                    name="max_token_per_leaf_module" 
                                    placeholder="Max tokens per leaf module"
                                >
                            </div>
                            
                            <div class="form-group">
                                <label for="include">
                                    <i class="fas fa-file-include"></i> Include Patterns
                                </label>
                                <input 
                                    type="text" 
                                    id="include" 
                                    name="include" 
                                    placeholder="e.g., *.py,*.js"
                                >
                            </div>
                            
                            <div class="form-group">
                                <label for="exclude">
                                    <i class="fas fa-file-exclude"></i> Exclude Patterns
                                </label>
                                <input 
                                    type="text" 
                                    id="exclude" 
                                    name="exclude" 
                                    placeholder="e.g., *test*,*node_modules*"
                                >
                            </div>
                            
                            <div class="form-group">
                                <label for="focus">
                                    <i class="fas fa-bullseye"></i> Focus Paths
                                </label>
                                <input 
                                    type="text" 
                                    id="focus" 
                                    name="focus" 
                                    placeholder="e.g., src/core,src/api"
                                >
                            </div>

                            <div class="form-group">
                                <label for="doc_type">
                                    <i class="fas fa-book"></i> Doc Type
                                </label>
                                <input 
                                    type="text" 
                                    id="doc_type" 
                                    name="doc_type" 
                                    placeholder="e.g., api, architecture, user-guide"
                                >
                            </div>

                            <div class="form-group">
                                <label for="instructions">
                                    <i class="fas fa-pen"></i> Instructions
                                </label>
                                <input 
                                    type="text" 
                                    id="instructions" 
                                    name="instructions" 
                                    placeholder="Custom generation instructions"
                                >
                            </div>
                            
                            <div class="form-group-checkbox">
                                <input type="checkbox" id="github_pages" name="github_pages" value="true">
                                <label for="github_pages">
                                    <i class="fas fa-globe"></i> Generate GitHub Pages (index.html)
                                </label>
                            </div>
                            
                            <div class="form-group-checkbox">
                                <input type="checkbox" id="no_cache" name="no_cache" value="true">
                                <label for="no_cache">
                                    <i class="fas fa-ban"></i> Force Regeneration (Ignore Cache)
                                </label>
                            </div>
                            
                            <div class="form-group-checkbox">
                                <input type="checkbox" id="create_branch" name="create_branch" value="true">
                                <label for="create_branch">
                                    <i class="fas fa-code-branch"></i> Create Git Branch
                                </label>
                            </div>
                        </div>
                    </details>
                    
                    <div class="form-row">
                        <button type="submit" class="btn">
                            <i class="fas fa-rocket"></i> Submit
                        </button>
                    </div>
                </form>
            </div>
            
            <h2 style="margin-bottom: 1rem; display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-list"></i>
                All Tasks ({{ total_count }})
            </h2>
            
            {% if jobs %}
            <table class="jobs-table">
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Status</th>
                        <th>Progress</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for job in jobs %}
                    <tr>
                        <td>
                            <div class="job-title">{{ job.title or job.repo_url }}</div>
                            <div class="job-url">{{ job.repo_url }}</div>
                        </td>
                        <td>
                            <span class="status-badge {{ job.status }}">
                                {% if job.status == 'queued' %}
                                <i class="fas fa-clock"></i>
                                {% elif job.status == 'processing' %}
                                <i class="fas fa-spinner fa-spin"></i>
                                {% elif job.status == 'completed' %}
                                <i class="fas fa-check"></i>
                                {% elif job.status == 'failed' %}
                                <i class="fas fa-times"></i>
                                {% endif %}
                                {{ job.status }}
                            </span>
                        </td>
                        <td>{{ job.progress }}</td>
                        <td>{{ job.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                        <td>
                            <div class="actions">
                                {% if job.status == 'completed' %}
                                <a href="/docs/{{ job.job_id }}" class="btn btn-small btn-success" title="View Documentation">
                                    <i class="fas fa-eye"></i>
                                </a>
                                {% endif %}
                                {% if job.status != 'processing' %}
                                <button class="btn btn-small btn-danger" onclick="deleteTask('{{ job.job_id }}')" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                                {% endif %}
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>No tasks yet. Submit a task above to get started.</p>
            </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        const ADVANCED_STORAGE_KEY = "codewiki_admin_advanced_options";

        function loadAdvancedOptions() {
            try {
                const raw = localStorage.getItem(ADVANCED_STORAGE_KEY);
                if (!raw) return;
                const data = JSON.parse(raw);
                for (const [name, value] of Object.entries(data)) {
                    const el = document.querySelector(`[name="${name}"]`);
                    if (!el) continue;
                    if (el.type === "checkbox") {
                        el.checked = Boolean(value);
                    } else {
                        el.value = value;
                    }
                }
            } catch (err) {
                console.warn("Failed to load advanced options", err);
            }
        }

        function saveAdvancedOptions() {
            const form = document.querySelector('form[action="/admin"]');
            if (!form) return;
            const data = {};
            form.querySelectorAll("input, select, textarea").forEach((el) => {
                if (!el.name) return;
                if (el.type === "checkbox") {
                    data[el.name] = el.checked;
                } else {
                    data[el.name] = el.value;
                }
            });
            try {
                localStorage.setItem(ADVANCED_STORAGE_KEY, JSON.stringify(data));
            } catch (err) {
                console.warn("Failed to save advanced options", err);
            }
        }

        function wireAdvancedOptionsPersistence() {
            const form = document.querySelector('form[action="/admin"]');
            if (!form) return;
            form.addEventListener("input", (e) => {
                if (e.target && e.target.name) {
                    saveAdvancedOptions();
                }
            });
            form.addEventListener("change", (e) => {
                if (e.target && e.target.name) {
                    saveAdvancedOptions();
                }
            });
        }

        document.addEventListener("DOMContentLoaded", () => {
            loadAdvancedOptions();
            wireAdvancedOptionsPersistence();
        });

        async function deleteTask(jobId) {
            if (!confirm('Are you sure you want to delete this task?')) {
                return;
            }
            
            try {
                const response = await fetch('/api/tasks/' + jobId, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    window.location.reload();
                } else {
                    const data = await response.json();
                    alert('Failed to delete task: ' + data.detail);
                }
            } catch (error) {
                alert('Error deleting task: ' + error.message);
            }
        }
        
        // Auto-refresh every 30 seconds
        setInterval(function() {
            window.location.reload();
        }, 30000);
    </script>
</body>
</html>
"""

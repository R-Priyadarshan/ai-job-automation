"""
============================================================
dashboard/app.py — Streamlit Web Dashboard
------------------------------------------------------------
PURPOSE:
    Interactive web dashboard to visualize and control the
    job application automation system.

    Streamlit turns Python scripts into web apps automatically.
    No HTML/CSS/JavaScript needed!

FEATURES:
    📋 Jobs Tab    — View all scraped jobs with filters/search
    📊 Analytics   — Charts showing job sources, ATS scores
    📄 Documents   — View/download generated PDFs
    ✅ Applications — Track application history and status
    ⚙️ Settings    — Quick config overview

HOW TO RUN:
    streamlit run dashboard/app.py

    Opens at: http://localhost:8501

STREAMLIT BASICS:
    - st.title(), st.header() — Headers
    - st.dataframe() — Interactive tables
    - st.metric() — KPI cards
    - st.sidebar — Left sidebar
    - st.columns() — Side-by-side layout
============================================================
"""

import sys
import os
from pathlib import Path
import streamlit as st               # Web dashboard framework
import pandas as pd                  # Data manipulation
import plotly.express as px          # Interactive charts
import plotly.graph_objects as go    # Advanced charts
from datetime import datetime

# Add project root to Python path
# This allows importing from src/ when running from dashboard/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config_loader import load_config
from src.database.db_manager import DatabaseManager


# ============================================================
# PAGE CONFIGURATION
# Must be the FIRST Streamlit command
# ============================================================
st.set_page_config(
    page_title="AI Job Application System",
    page_icon="🤖",
    layout="wide",                   # Use full browser width
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS — Makes the dashboard look professional
# ============================================================
st.markdown("""
<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Apply to all text */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Main background */
.main {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}

/* Sidebar */
.css-1d391kg {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
}

/* Metric cards */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1e1e3f, #2d2d5e);
    border: 1px solid rgba(100, 100, 255, 0.2);
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
    transition: transform 0.2s, box-shadow 0.2s;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

/* Score badges */
.score-excellent { color: #00ff88; font-weight: bold; font-size: 1.1em; }
.score-good { color: #ffdd00; font-weight: bold; font-size: 1.1em; }
.score-fair { color: #ff8800; font-weight: bold; font-size: 1.1em; }
.score-poor { color: #ff4444; font-weight: bold; font-size: 1.1em; }

/* Table styling */
.dataframe {
    border-radius: 10px;
    overflow: hidden;
}

/* Success/Error alerts */
.success-box {
    background: rgba(0, 255, 136, 0.1);
    border: 1px solid #00ff88;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# LOAD CONFIG AND DATABASE
# ============================================================
@st.cache_resource  # Cache so we don't reload on every interaction
def get_config():
    """Loads configuration file. Cached for performance."""
    try:
        return load_config()
    except Exception as e:
        st.error(f"Failed to load config: {e}")
        return {}


@st.cache_resource
def get_db(config):
    """Gets database connection. Cached for performance."""
    db_path = config.get('database', {}).get('path', 'data/jobs.db')
    return DatabaseManager(db_path)


config = get_config()
if config:
    db = get_db(config)


# ============================================================
# SIDEBAR — Navigation and Quick Actions
# ============================================================
with st.sidebar:
    st.markdown("## 🤖 AI Job System")
    st.markdown("---")

    # Navigation menu
    page = st.selectbox(
        "Navigate",
        ["📋 Job Listings", "📊 Analytics", "📄 Documents", "✅ Applications", "📧 Auto-Apply", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Quick action buttons
    st.markdown("### ⚡ Quick Actions")

    if st.button("🕷️ Run Scrapers", use_container_width=True):
        with st.spinner("Scraping jobs..."):
            try:
                import subprocess
                result = subprocess.run(
                    ["python", "main.py", "--scrape-only"],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    st.success("✅ Scraping complete!")
                else:
                    st.error(f"Scraping failed: {result.stderr[:200]}")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("🤖 Run AI Analysis", use_container_width=True):
        with st.spinner("Running AI analysis..."):
            try:
                import subprocess
                result = subprocess.run(
                    ["python", "main.py", "--analyze-only"],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    st.success("✅ Analysis complete!")
                else:
                    st.error(f"Analysis failed: {result.stderr[:200]}")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("🔄 Full Pipeline", use_container_width=True):
        st.info("💡 Run: python main.py in terminal")

    st.markdown("---")
    st.markdown(f"*Last updated: {datetime.now().strftime('%H:%M:%S')}*")


# ============================================================
# MAIN CONTENT AREA
# ============================================================

# ---- OVERVIEW METRICS (shown on every page) ----
if config:
    stats = db.get_statistics()

    st.markdown("### 📊 Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💼 Total Jobs",
            value=stats.get('total_jobs', 0),
            delta="from all sources",
        )
    with col2:
        st.metric(
            label="📝 Applications",
            value=stats.get('total_applications', 0),
        )
    with col3:
        st.metric(
            label="⭐ Avg ATS Score",
            value=f"{stats.get('avg_ats_score', 0):.1f}/100",
        )
    with col4:
        st.metric(
            label="🎯 Min Score",
            value=f"{config.get('ats', {}).get('minimum_score', 60)}/100",
            delta="apply threshold",
        )

    st.markdown("---")


# ============================================================
# PAGE: JOB LISTINGS
# ============================================================
if page == "📋 Job Listings":
    st.markdown("## 📋 Scraped Job Listings")

    if not config:
        st.error("Config not loaded. Check config.yaml")
        st.stop()

    # ---- Filters ----
    col1, col2, col3 = st.columns([3, 2, 2])

    with col1:
        search = st.text_input(
            "🔍 Search jobs",
            placeholder="Search title, company, skills...",
        )

    with col2:
        source_filter = st.multiselect(
            "Source",
            options=["remoteok", "weworkremotely", "internshala", "linkedin", "all"],
            default=["all"],
        )

    with col3:
        min_score_filter = st.slider(
            "Min ATS Score",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
        )

    # ---- Location filter ----
    col4, col5 = st.columns([3, 3])
    with col4:
        location_filter = st.text_input(
            "📍 Location filter",
            placeholder="e.g. India, Remote, USA, Bangalore...",
        )
    with col5:
        job_type_filter = st.selectbox(
            "Job Type",
            ["All", "Internship", "Full-time", "Part-time", "Contract", "Remote"],
        )

    # ---- Fetch Jobs ----
    all_jobs = db.get_all_jobs(limit=200, keyword=search if search else None)

    # Apply source filter
    if source_filter and "all" not in source_filter:
        all_jobs = [j for j in all_jobs if j.get('source') in source_filter]

    # Apply ATS score filter
    if min_score_filter > 0:
        all_jobs = [j for j in all_jobs if (j.get('ats_score') or 0) >= min_score_filter]

    # Apply location filter
    if location_filter:
        loc_lower = location_filter.lower()
        all_jobs = [
            j for j in all_jobs
            if loc_lower in (j.get('location') or '').lower()
            or loc_lower in (j.get('description') or '').lower()
        ]

    # Apply job type filter
    if job_type_filter != "All":
        type_lower = job_type_filter.lower()
        all_jobs = [
            j for j in all_jobs
            if type_lower in (j.get('job_type') or '').lower()
            or type_lower in (j.get('title') or '').lower()
            or type_lower in (j.get('description') or '').lower()
        ]

    st.markdown(f"*Showing {len(all_jobs)} jobs*")

    if not all_jobs:
        st.info(
            "No jobs found. Run the scrapers first:\n\n"
            "```bash\npython main.py --scrape-only\n```"
        )
    else:
        # ---- Display Jobs as Interactive Cards ----
        # Convert to DataFrame for nice display
        df = pd.DataFrame(all_jobs)

        # Select and rename columns for display
        display_cols = {
            'title': 'Job Title',
            'company': 'Company',
            'location': 'Location',
            'source': 'Source',
            'ats_score': 'ATS Score',
            'status': 'Status',
            'posted_date': 'Posted',
            'url': 'URL',
        }

        # Only show columns that exist
        available_cols = [c for c in display_cols.keys() if c in df.columns]
        df_display = df[available_cols].copy()
        df_display.columns = [display_cols[c] for c in available_cols]

        # Fill NaN values
        df_display = df_display.fillna('—')

        # Display interactive table
        st.dataframe(
            df_display,
            use_container_width=True,
            height=400,
            column_config={
                "ATS Score": st.column_config.ProgressColumn(
                    "ATS Score",
                    min_value=0,
                    max_value=100,
                    format="%d/100",
                ),
                "URL": st.column_config.LinkColumn("Link"),
            }
        )

        # ---- Job Detail Viewer ----
        st.markdown("### 🔍 View Job Details")
        if all_jobs:
            job_options = {f"{j['title']} @ {j['company']} (ID:{j['id']})": j for j in all_jobs}
            selected_label = st.selectbox("Select a job:", list(job_options.keys()))
            selected_job = job_options[selected_label]

            with st.expander("📋 Full Job Description", expanded=True):
                col_a, col_b = st.columns(2)

                with col_a:
                    st.markdown(f"**🏢 Company:** {selected_job.get('company')}")
                    st.markdown(f"**📍 Location:** {selected_job.get('location')}")
                    st.markdown(f"**💰 Salary:** {selected_job.get('salary', 'Not specified')}")
                    st.markdown(f"**📅 Posted:** {selected_job.get('posted_date', 'Unknown')}")

                with col_b:
                    ats_score = selected_job.get('ats_score')
                    if ats_score:
                        score_pct = int(ats_score)
                        color = "#00ff88" if score_pct >= 80 else "#ffdd00" if score_pct >= 60 else "#ff4444"
                        st.markdown(
                            f"<h3 style='color:{color}'>ATS Score: {score_pct}/100</h3>",
                            unsafe_allow_html=True
                        )
                    st.markdown(f"**🏷️ Skills:** {selected_job.get('skills', 'Not specified')[:200]}")
                    st.markdown(f"[🔗 View Job Posting]({selected_job.get('url', '#')})")

                st.markdown("**📝 Description:**")
                st.text_area(
                    "Description",
                    value=selected_job.get('description', 'No description available')[:2000],
                    height=200,
                    label_visibility="collapsed",
                )

                # Generate documents button
                if st.button(f"🤖 Generate Resume + Cover Letter for this Job", type="primary"):
                    with st.spinner("Running AI... this may take 1-2 minutes..."):
                        try:
                            import subprocess
                            result = subprocess.run(
                                ["python", "main.py", "--job-id", str(selected_job['id'])],
                                capture_output=True, text=True, timeout=300,
                                cwd=str(Path(__file__).parent.parent)
                            )
                            if result.returncode == 0:
                                st.success("✅ Documents generated! Check the Documents tab.")
                            else:
                                st.error(f"Failed: {result.stderr[:500]}")
                        except Exception as e:
                            st.error(f"Error: {e}")


# ============================================================
# PAGE: ANALYTICS
# ============================================================
elif page == "📊 Analytics":
    st.markdown("## 📊 Analytics Dashboard")

    if not config:
        st.stop()

    stats = db.get_statistics()
    all_jobs = db.get_all_jobs(limit=500)

    if not all_jobs:
        st.info("No data yet. Run scrapers to collect job data.")
        st.stop()

    df = pd.DataFrame(all_jobs)

    col1, col2 = st.columns(2)

    # ---- Chart 1: Jobs by Source ----
    with col1:
        if 'source' in df.columns:
            source_counts = df['source'].value_counts().reset_index()
            source_counts.columns = ['Source', 'Count']

            fig = px.pie(
                source_counts,
                values='Count',
                names='Source',
                title='🕷️ Jobs by Source',
                color_discrete_sequence=px.colors.sequential.Plasma,
                hole=0.3,  # Donut chart
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
            )
            st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 2: ATS Score Distribution ----
    with col2:
        all_scores_data = []
        for job in all_jobs:
            score_row = db.get_ats_score(job.get('id'))
            if score_row and score_row.get('score'):
                all_scores_data.append({
                    'title': job.get('title', '')[:20],
                    'company': job.get('company', ''),
                    'score': score_row['score']
                })

        if all_scores_data:
            df_scores = pd.DataFrame(all_scores_data)
            fig2 = px.histogram(
                df_scores,
                x='score',
                nbins=20,
                title='📊 ATS Score Distribution',
                labels={'score': 'ATS Score', 'count': 'Number of Jobs'},
                color_discrete_sequence=['#667eea'],
            )
            fig2.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No ATS scores yet. Run AI analysis first.")

    # ---- Chart 3: Applications Timeline ----
    applications = db.get_all_applications()
    if applications:
        st.markdown("### 📅 Application Timeline")
        df_apps = pd.DataFrame(applications)

        if 'applied_at' in df_apps.columns:
            df_apps['applied_at'] = pd.to_datetime(df_apps['applied_at'])
            df_apps['date'] = df_apps['applied_at'].dt.date
            daily_counts = df_apps.groupby('date').size().reset_index()
            daily_counts.columns = ['Date', 'Applications']

            fig3 = px.bar(
                daily_counts,
                x='Date',
                y='Applications',
                title='📈 Daily Applications',
                color_discrete_sequence=['#764ba2'],
            )
            fig3.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
            )
            st.plotly_chart(fig3, use_container_width=True)

    # ---- Top Skill Gaps ----
    st.markdown("### 🎯 Most Common Skill Gaps")
    all_missing = []
    for job in all_jobs[:50]:
        ats_data = db.get_ats_score(job.get('id'))
        if ats_data and ats_data.get('missing_skills'):
            skills = [s.strip() for s in ats_data['missing_skills'].split(',')]
            all_missing.extend(skills)

    if all_missing:
        from collections import Counter
        skill_counts = Counter(all_missing).most_common(10)
        df_skills = pd.DataFrame(skill_counts, columns=['Skill', 'Count'])

        fig4 = px.bar(
            df_skills,
            x='Count',
            y='Skill',
            orientation='h',
            title='🔧 Skills You Should Learn',
            color='Count',
            color_continuous_scale='Viridis',
        )
        fig4.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.caption("💡 These are the most common missing skills across job listings. Prioritize learning these!")


# ============================================================
# PAGE: DOCUMENTS
# ============================================================
elif page == "📄 Documents":
    st.markdown("## 📄 Generated Documents")

    pdf_dir = Path("data/pdfs")

    if not pdf_dir.exists():
        st.info("No PDFs generated yet. Run the AI analysis pipeline first.")
    else:
        # List all PDFs
        pdfs = sorted(pdf_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not pdfs:
            st.info(
                "No PDFs found. Run:\n```bash\npython main.py\n```"
            )
        else:
            st.markdown(f"*Found {len(pdfs)} generated documents*")

            # Separate resumes and cover letters
            resumes = [p for p in pdfs if 'resume' in p.name.lower()]
            cover_letters = [p for p in pdfs if 'cover_letter' in p.name.lower()]

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"### 📄 Resumes ({len(resumes)})")
                for pdf in resumes[:10]:
                    st.markdown(f"📋 `{pdf.name}`")
                    with open(pdf, 'rb') as f:
                        st.download_button(
                            label=f"⬇️ Download",
                            data=f.read(),
                            file_name=pdf.name,
                            mime="application/pdf",
                            key=f"dl_resume_{pdf.name}",
                        )
                    st.markdown("---")

            with col2:
                st.markdown(f"### 💌 Cover Letters ({len(cover_letters)})")
                for pdf in cover_letters[:10]:
                    st.markdown(f"📋 `{pdf.name}`")
                    with open(pdf, 'rb') as f:
                        st.download_button(
                            label=f"⬇️ Download",
                            data=f.read(),
                            file_name=pdf.name,
                            mime="application/pdf",
                            key=f"dl_cl_{pdf.name}",
                        )
                    st.markdown("---")


# ============================================================
# PAGE: APPLICATIONS
# ============================================================
elif page == "✅ Applications":
    st.markdown("## ✅ Application Tracker")

    applications = db.get_all_applications()

    if not applications:
        st.info(
            "No applications tracked yet.\n\n"
            "Run the full pipeline to generate applications:\n"
            "```bash\npython main.py\n```"
        )
    else:
        df_apps = pd.DataFrame(applications)

        # ---- Status Summary ----
        if 'status' in df_apps.columns:
            status_counts = df_apps['status'].value_counts()

            cols = st.columns(len(status_counts))
            status_emojis = {
                'pending': '⏳',
                'applied': '✉️',
                'interview': '🎙️',
                'offer': '🎉',
                'rejected': '❌',
            }

            for i, (status, count) in enumerate(status_counts.items()):
                emoji = status_emojis.get(status, '📋')
                with cols[i]:
                    st.metric(f"{emoji} {status.title()}", count)

        st.markdown("---")

        # ---- Applications Table ----
        display_cols = ['title', 'company', 'ats_score', 'status', 'applied_at', 'source']
        available = [c for c in display_cols if c in df_apps.columns]
        df_display = df_apps[available].copy()

        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "ats_score": st.column_config.ProgressColumn(
                    "ATS Score",
                    min_value=0,
                    max_value=100,
                    format="%d/100",
                ),
            }
        )

        # ---- Update Status ----
        st.markdown("### 🔄 Update Application Status")
        app_options = {
            f"{a['title']} @ {a['company']}": a['id']
            for a in applications
        }

        selected_app = st.selectbox("Select Application:", list(app_options.keys()))
        new_status = st.selectbox(
            "New Status:",
            ["pending", "applied", "interview", "offer", "rejected"]
        )

        if st.button("Update Status"):
            app_id = app_options[selected_app]
            db.update_application_status(app_id, new_status)
            st.success(f"✅ Status updated to '{new_status}'!")
            st.rerun()


# ============================================================
# PAGE: AUTO-APPLY (Cold Internship Emails)
# ============================================================
elif page == "📧 Auto-Apply":
    st.markdown("## 📧 Auto-Apply — Cold Internship Emails")

    if not config:
        st.stop()

    # ---- Email Config Status ----
    email_cfg = config.get('email', {})
    sender    = email_cfg.get('sender_email', '')
    auto_send = email_cfg.get('auto_send', False)

    import os
    from dotenv import load_dotenv
    load_dotenv()
    has_password = bool(os.getenv('EMAIL_PASSWORD', ''))

    col1, col2, col3 = st.columns(3)
    with col1:
        if sender:
            st.success(f"✅ Sender: {sender}")
        else:
            st.error("❌ sender_email not set in config.yaml")
    with col2:
        if has_password:
            st.success("✅ App Password: configured")
        else:
            st.error("❌ EMAIL_PASSWORD missing in .env")
    with col3:
        if auto_send:
            st.success("✅ Auto-send: ENABLED")
        else:
            st.warning("⚠️ Auto-send: DISABLED (dry-run only)")

    st.markdown("---")

    # ---- Setup Instructions ----
    if not has_password or not sender:
        with st.expander("📖 Setup Instructions", expanded=True):
            st.markdown("""
**Step 1 — Enable Gmail App Password:**
1. Go to [myaccount.google.com](https://myaccount.google.com) → Security
2. Enable **2-Step Verification** (required)
3. Go to **App Passwords** → Select "Mail" → Generate
4. Copy the 16-character password

**Step 2 — Add to `.env` file** (in project root):
```
EMAIL_PASSWORD=your16charpassword
```

**Step 3 — Update `config.yaml`:**
```yaml
email:
  sender_email: "priyadarshanr01@gmail.com"
  auto_send: true   # set to true when ready to send
```

**Step 4 — Come back here and run!**
            """)

    st.markdown("### 🎯 Pipeline Settings")

    col_a, col_b = st.columns(2)
    with col_a:
        dry_run = st.toggle(
            "🔍 Dry Run (preview only — don't send)",
            value=not auto_send,
            help="Enable to preview emails without sending. Disable to actually send."
        )
        limit = st.slider("Max jobs to process", 1, 50, 10)

    with col_b:
        min_score = config.get('ats', {}).get('minimum_score', 60)
        st.info(f"**ATS Threshold:** {min_score}/100 (only emails jobs above this score)")
        st.info(f"**Daily Limit:** {email_cfg.get('daily_limit', 20)} emails/day")
        st.info(f"**Delay:** {email_cfg.get('delay_seconds', 30)}s between emails")

    st.markdown("---")

    # ---- Run Button ----
    btn_label = "👁️ Preview Cold Emails (Dry Run)" if dry_run else "🚀 Send Cold Emails NOW"
    btn_type  = "secondary" if dry_run else "primary"

    if st.button(btn_label, type=btn_type, use_container_width=True):
        if not dry_run and not has_password:
            st.error("❌ Cannot send — EMAIL_PASSWORD not set in .env file!")
        else:
            with st.spinner("Running auto-apply pipeline... this may take a few minutes..."):
                try:
                    import subprocess
                    cmd = ["python", "main.py", "--auto-apply"]
                    if dry_run:
                        cmd.append("--dry-run")
                    result = subprocess.run(
                        cmd,
                        capture_output=True, text=True, timeout=600,
                        cwd=str(Path(__file__).parent.parent)
                    )
                    if result.returncode == 0:
                        if dry_run:
                            st.success("✅ Preview generated! See output below.")
                        else:
                            st.success("✅ Cold emails sent! Check Applications tab.")
                        st.code(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
                    else:
                        st.error("Pipeline failed:")
                        st.code(result.stderr[-2000:])
                except subprocess.TimeoutExpired:
                    st.error("Timed out after 10 minutes. Try with fewer jobs.")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")

    # ---- Show recent email drafts from DB ----
    st.markdown("### 📬 Recent Email Drafts")
    applications = db.get_all_applications()
    email_apps   = [a for a in applications if a.get('email_draft')]

    if not email_apps:
        st.info("No email drafts yet. Run the pipeline above to generate them.")
    else:
        for app in email_apps[:10]:
            with st.expander(f"📧 {app.get('title')} @ {app.get('company')} — {app.get('status', 'pending')}"):
                draft = app.get('email_draft', '')
                lines = draft.split('\n')
                subject_line = next((l for l in lines if l.startswith('Subject:')), '')
                st.markdown(f"**{subject_line}**")
                st.text_area(
                    "Email Body",
                    value=draft,
                    height=200,
                    key=f"draft_{app.get('id')}",
                    label_visibility="collapsed"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if app.get('resume_path') and Path(app['resume_path']).exists():
                        with open(app['resume_path'], 'rb') as f:
                            st.download_button(
                                "⬇️ Resume PDF",
                                data=f.read(),
                                file_name="resume.pdf",
                                key=f"res_{app.get('id')}"
                            )
                with col2:
                    if app.get('cover_letter_path') and Path(app['cover_letter_path']).exists():
                        with open(app['cover_letter_path'], 'rb') as f:
                            st.download_button(
                                "⬇️ Cover Letter PDF",
                                data=f.read(),
                                file_name="cover_letter.pdf",
                                key=f"cl_{app.get('id')}"
                            )


# ============================================================
# PAGE: SETTINGS
# ============================================================
elif page == "⚙️ Settings":
    st.markdown("## ⚙️ System Settings")

    if not config:
        st.error("Config not loaded")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🤖 AI Settings")
        st.info(f"**Model:** {config.get('ollama', {}).get('model', 'not set')}")
        st.info(f"**Base URL:** {config.get('ollama', {}).get('base_url', 'not set')}")
        st.info(f"**Temperature:** {config.get('ollama', {}).get('temperature', 0.7)}")

        # Check Ollama status
        try:
            from src.ai_engine.ollama_client import OllamaClient
            client = OllamaClient(config)
            if client.is_available():
                models = client.list_models()
                st.success(f"✅ Ollama running. Models: {', '.join(models)}")
            else:
                st.error("❌ Ollama not running. Start: `ollama serve`")
        except Exception:
            st.warning("Cannot check Ollama status")

    with col2:
        st.markdown("### 👤 Your Profile")
        user = config.get('user', {})
        st.info(f"**Name:** {user.get('name', 'Not set')}")
        st.info(f"**Email:** {user.get('email', 'Not set')}")
        st.info(f"**Resume:** {user.get('resume_path', 'Not set')}")

        st.markdown("### 🎯 ATS Thresholds")
        ats_cfg = config.get('ats', {})
        st.info(f"**Minimum Score:** {ats_cfg.get('minimum_score', 60)}/100")
        st.info(f"**High Match:** {ats_cfg.get('high_match_threshold', 80)}/100")

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("""
    **AI Job Application Automation System**
    - Version: 1.0.0
    - AI Engine: Ollama (100% Local)
    - Cost: $0 (Zero Cost)
    - Data: Stored locally in SQLite

    To edit settings, modify `config.yaml` in the project root.
    """)

    # Cron job info
    st.markdown("### ⏰ Automation Schedule")
    sched = config.get('scheduler', {})
    st.code(
        f"# Run full pipeline daily at {sched.get('run_hour', 8):02d}:{sched.get('run_minute', 0):02d}\n"
        f"0 {sched.get('run_hour', 8)} * * * cd /path/to/ai_job_automation && python main.py >> logs/cron.log 2>&1",
        language="bash"
    )

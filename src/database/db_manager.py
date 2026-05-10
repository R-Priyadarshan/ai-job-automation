"""
============================================================
src/database/db_manager.py
------------------------------------------------------------
PURPOSE:
    Manages the SQLite database for storing:
    - Scraped jobs
    - Application history
    - ATS scores
    - Generated resumes and cover letter paths

WHY SQLITE?
    - Zero cost
    - No server needed (just a file)
    - Built into Python (no installation)
    - Perfect for local automation

TABLES:
    1. jobs           — all scraped job listings
    2. applications   — track which jobs were applied to
    3. ats_scores     — ATS match score for each job
    4. generated_docs — paths to generated PDFs
============================================================
"""

import sqlite3                       # Built-in Python SQLite
import os                            # OS operations
from datetime import datetime        # Timestamps
from pathlib import Path             # Path handling
from loguru import logger            # Logging


class DatabaseManager:
    """
    Handles all database operations using SQLite.

    Think of this class as the "filing cabinet" of the system.
    It stores and retrieves all job and application data.
    """

    def __init__(self, db_path: str = "data/jobs.db"):
        """
        Initialize database connection and create tables if they don't exist.

        Args:
            db_path: Path to the SQLite .db file.
                     If it doesn't exist, SQLite creates it automatically.
        """
        # Create parent directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path

        # Connect to SQLite database
        # SQLite creates the file if it doesn't exist
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

        # Enable WAL mode for better concurrent read performance
        self.conn.execute("PRAGMA journal_mode=WAL")

        # Enable foreign key constraints
        self.conn.execute("PRAGMA foreign_keys=ON")

        # Auto-convert row to dict-like objects
        self.conn.row_factory = sqlite3.Row

        # Create the cursor (used to execute SQL queries)
        self.cursor = self.conn.cursor()

        # Create all tables
        self._create_tables()

        logger.info(f"Database initialized at: {db_path}")

    def _create_tables(self):
        """
        Creates all database tables if they don't already exist.
        This is safe to run multiple times — won't duplicate tables.
        """

        # ---- TABLE 1: jobs ----
        # Stores all scraped job listings
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,           -- Job title (e.g., "ML Engineer")
                company     TEXT NOT NULL,           -- Company name
                location    TEXT,                    -- Location or "Remote"
                url         TEXT UNIQUE NOT NULL,    -- UNIQUE prevents duplicates!
                source      TEXT,                    -- Website (remoteok, wwr, etc.)
                description TEXT,                    -- Full job description text
                skills      TEXT,                    -- Comma-separated required skills
                salary      TEXT,                    -- Salary range if shown
                job_type    TEXT,                    -- Full-time / Part-time / Contract
                posted_date TEXT,                    -- When job was posted
                scraped_at  TEXT DEFAULT (datetime('now')),  -- When WE scraped it
                is_active   INTEGER DEFAULT 1        -- 1=active, 0=expired
            )
        """)

        # ---- TABLE 2: applications ----
        # Tracks which jobs we applied to
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id          INTEGER NOT NULL,           -- Links to jobs.id
                applied_at      TEXT DEFAULT (datetime('now')),
                status          TEXT DEFAULT 'pending',    -- pending/applied/rejected/interview
                ats_score       REAL,                      -- ATS match score (0-100)
                notes           TEXT,                      -- Your personal notes
                resume_path     TEXT,                      -- Path to generated resume PDF
                cover_letter_path TEXT,                    -- Path to generated cover letter PDF
                email_draft     TEXT,                      -- Recruiter email draft
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
        """)

        # ---- TABLE 3: ats_scores ----
        # Stores detailed ATS analysis results
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ats_scores (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id          INTEGER NOT NULL,
                score           REAL,                      -- 0 to 100
                matching_skills TEXT,                      -- Skills found in resume
                missing_skills  TEXT,                      -- Skills NOT in resume
                analysis_text   TEXT,                      -- Full AI analysis
                analyzed_at     TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
        """)

        # ---- TABLE 4: generated_docs ----
        # Tracks all generated PDF files
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_docs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id      INTEGER,
                doc_type    TEXT,           -- 'resume' or 'cover_letter'
                file_path   TEXT,           -- Absolute path to the PDF
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
        """)

        # Save changes to disk
        self.conn.commit()
        logger.debug("Database tables created/verified.")

    # =====================================================
    # JOB OPERATIONS
    # =====================================================

    def insert_job(self, job: dict) -> int | None:
        """
        Inserts a new job into the database.
        Automatically skips duplicates (based on URL).

        Args:
            job: Dictionary with job data keys matching column names.

        Returns:
            int: The new job's ID, or None if it was a duplicate.
        """
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO jobs
                    (title, company, location, url, source,
                     description, skills, salary, job_type, posted_date)
                VALUES
                    (:title, :company, :location, :url, :source,
                     :description, :skills, :salary, :job_type, :posted_date)
            """, job)

            self.conn.commit()

            # lastrowid is 0 if INSERT was ignored (duplicate)
            if self.cursor.lastrowid:
                logger.debug(f"Inserted job: {job.get('title')} @ {job.get('company')}")
                return self.cursor.lastrowid
            else:
                logger.debug(f"Duplicate skipped: {job.get('url')}")
                return None

        except sqlite3.Error as e:
            logger.error(f"Failed to insert job: {e}")
            return None

    def get_all_jobs(self, limit: int = 100, keyword: str = None) -> list[dict]:
        """
        Fetches jobs from the database with optional keyword filtering.

        Args:
            limit: Max number of jobs to return.
            keyword: Optional filter (searches title + description).

        Returns:
            List of job dictionaries.
        """
        if keyword:
            # SQL LIKE query for partial matching
            query = """
                SELECT j.*, a.ats_score, a.status
                FROM jobs j
                LEFT JOIN applications a ON j.id = a.job_id
                WHERE j.title LIKE ? OR j.description LIKE ? OR j.skills LIKE ?
                ORDER BY j.scraped_at DESC
                LIMIT ?
            """
            pattern = f"%{keyword}%"
            self.cursor.execute(query, (pattern, pattern, pattern, limit))
        else:
            query = """
                SELECT j.*, a.ats_score, a.status
                FROM jobs j
                LEFT JOIN applications a ON j.id = a.job_id
                ORDER BY j.scraped_at DESC
                LIMIT ?
            """
            self.cursor.execute(query, (limit,))

        # Convert sqlite3.Row objects to plain dictionaries
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_job_by_id(self, job_id: int) -> dict | None:
        """
        Fetches a single job by its database ID.

        Args:
            job_id: The integer ID from the jobs table.

        Returns:
            Job as a dictionary, or None if not found.
        """
        self.cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_unapplied_jobs(self, min_score: float = 0.0) -> list[dict]:
        """
        Returns jobs that haven't been applied to yet.
        Optionally filter by minimum ATS score.

        Args:
            min_score: Minimum ATS score required (0-100).

        Returns:
            List of job dictionaries.
        """
        query = """
            SELECT j.*
            FROM jobs j
            WHERE j.id NOT IN (SELECT job_id FROM applications)
            ORDER BY j.scraped_at DESC
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def count_jobs(self) -> int:
        """Returns total number of jobs in the database."""
        self.cursor.execute("SELECT COUNT(*) FROM jobs")
        return self.cursor.fetchone()[0]

    # =====================================================
    # APPLICATION OPERATIONS
    # =====================================================

    def record_application(self, application: dict) -> int:
        """
        Records that we applied to a job.

        Args:
            application: Dict with job_id, ats_score, resume_path, etc.

        Returns:
            New application ID.
        """
        self.cursor.execute("""
            INSERT INTO applications
                (job_id, ats_score, notes, resume_path, cover_letter_path, email_draft)
            VALUES
                (:job_id, :ats_score, :notes, :resume_path, :cover_letter_path, :email_draft)
        """, application)

        self.conn.commit()
        logger.info(f"Application recorded for job_id: {application.get('job_id')}")
        return self.cursor.lastrowid

    def update_application_status(self, app_id: int, status: str):
        """
        Updates the status of an application.

        Args:
            app_id: Application ID to update.
            status: New status (applied/interview/rejected/offer).
        """
        self.cursor.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status, app_id)
        )
        self.conn.commit()

    def get_all_applications(self) -> list[dict]:
        """
        Returns all applications with job details joined in.

        Returns:
            List of application dictionaries with job data merged.
        """
        self.cursor.execute("""
            SELECT a.*, j.title, j.company, j.url, j.location, j.source
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            ORDER BY a.applied_at DESC
        """)
        return [dict(row) for row in self.cursor.fetchall()]

    def count_applications(self) -> int:
        """Returns total number of applications made."""
        self.cursor.execute("SELECT COUNT(*) FROM applications")
        return self.cursor.fetchone()[0]

    # =====================================================
    # ATS SCORE OPERATIONS
    # =====================================================

    def save_ats_score(self, ats_data: dict):
        """
        Saves ATS analysis results to the database.

        Args:
            ats_data: Dict with job_id, score, matching_skills,
                      missing_skills, analysis_text.
        """
        self.cursor.execute("""
            INSERT OR REPLACE INTO ats_scores
                (job_id, score, matching_skills, missing_skills, analysis_text)
            VALUES
                (:job_id, :score, :matching_skills, :missing_skills, :analysis_text)
        """, ats_data)
        self.conn.commit()

    def get_ats_score(self, job_id: int) -> dict | None:
        """
        Gets the ATS score for a specific job.

        Args:
            job_id: The job's database ID.

        Returns:
            ATS data dict or None.
        """
        self.cursor.execute(
            "SELECT * FROM ats_scores WHERE job_id = ?",
            (job_id,)
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    # =====================================================
    # GENERATED DOCS OPERATIONS
    # =====================================================

    def save_generated_doc(self, job_id: int, doc_type: str, file_path: str):
        """
        Records a generated PDF (resume or cover letter).

        Args:
            job_id: The job's database ID.
            doc_type: 'resume' or 'cover_letter'
            file_path: Path to the generated PDF file.
        """
        self.cursor.execute("""
            INSERT INTO generated_docs (job_id, doc_type, file_path)
            VALUES (?, ?, ?)
        """, (job_id, doc_type, file_path))
        self.conn.commit()

    def get_generated_docs(self, job_id: int) -> list[dict]:
        """
        Returns all generated documents for a specific job.

        Args:
            job_id: The job's database ID.

        Returns:
            List of generated doc dicts with doc_type and file_path.
        """
        self.cursor.execute(
            "SELECT * FROM generated_docs WHERE job_id = ?",
            (job_id,)
        )
        return [dict(row) for row in self.cursor.fetchall()]

    # =====================================================
    # STATISTICS
    # =====================================================

    def get_statistics(self) -> dict:
        """
        Returns summary statistics for the dashboard.

        Returns:
            Dict with counts and averages.
        """
        stats = {}

        # Total jobs scraped
        stats['total_jobs'] = self.count_jobs()

        # Total applications
        stats['total_applications'] = self.count_applications()

        # Average ATS score
        self.cursor.execute("SELECT AVG(score) FROM ats_scores")
        avg = self.cursor.fetchone()[0]
        stats['avg_ats_score'] = round(avg, 1) if avg else 0

        # Jobs by source
        self.cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM jobs GROUP BY source
        """)
        stats['jobs_by_source'] = {row[0]: row[1] for row in self.cursor.fetchall()}

        # Applications by status
        self.cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM applications GROUP BY status
        """)
        stats['apps_by_status'] = {row[0]: row[1] for row in self.cursor.fetchall()}

        return stats

    def close(self):
        """Closes the database connection cleanly."""
        self.conn.close()
        logger.debug("Database connection closed.")

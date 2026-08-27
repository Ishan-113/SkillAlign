"""Data ingestion package.

Scheduled background ingestion supplies the application with automatically
updating job and curriculum data, sourced from legitimate APIs/providers with a
graceful fallback so the system keeps working when an external source fails.
"""

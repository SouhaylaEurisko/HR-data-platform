"""
Service layer for DataSource operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.candidate import DataSource


def get_or_create_data_source(
    db: Session,
    source_file: str,
    source_sheet: str,
    source_table_index: int,
) -> DataSource:
    """
    Get an existing DataSource or create a new one.
    
    Args:
        db: Database session
        source_file: Name of the source file
        source_sheet: Name of the sheet
        source_table_index: Index of the table within the sheet
        
    Returns:
        DataSource instance
    """
    # Truncate to 255 characters to match database column size
    source_file_truncated = source_file[:255] if len(source_file) > 255 else source_file
    source_sheet_truncated = source_sheet[:255] if len(source_sheet) > 255 else source_sheet
    
    # Try to find existing DataSource
    stmt = select(DataSource).where(
        DataSource.source_file == source_file_truncated,
        DataSource.source_sheet == source_sheet_truncated,
        DataSource.source_table_index == source_table_index,
    )
    existing = db.scalar(stmt)
    
    if existing:
        return existing
    
    # Create new DataSource
    data_source = DataSource(
        source_file=source_file_truncated,
        source_sheet=source_sheet_truncated,
        source_table_index=source_table_index,
    )
    db.add(data_source)
    db.flush()  # Flush to get the ID without committing
    
    return data_source

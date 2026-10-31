"""Business and domain logic services for StudySphere.

Modules in this package handle:
- Curriculum loading and validation (CurriculumLoader)
- Knowledge gap analysis and graph algorithms (DFS/topological ordering)
- OCR document extraction
- LLM interaction for automated question generation and note summarization
- Scoring and attempt processing
"""

from app.services.curriculum_loader import (
    CurriculumLoader,
    CurriculumSummary,
    CurriculumLoaderError,
    CurriculumValidationError,
    MissingDataFileError,
    load_curriculum,
)
from app.services.notes_loader import (
    NotesLoader,
    NotesSummary,
    NotesLoaderError,
    NotesValidationError,
    MissingNotesDirectoryError,
    ParsedNote,
    SubjectNotesStatus,
    OverallNotesStatus,
    load_notes,
    get_notes_status,
)
from app.services.markdown_renderer import render_markdown

__all__: list[str] = [
    "CurriculumLoader",
    "CurriculumSummary",
    "CurriculumLoaderError",
    "CurriculumValidationError",
    "MissingDataFileError",
    "load_curriculum",
    "NotesLoader",
    "NotesSummary",
    "NotesLoaderError",
    "NotesValidationError",
    "MissingNotesDirectoryError",
    "ParsedNote",
    "SubjectNotesStatus",
    "OverallNotesStatus",
    "load_notes",
    "get_notes_status",
    "render_markdown",
]

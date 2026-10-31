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
from app.services.markdown_renderer import (
    render_markdown,
    render_topic_markdown,
    get_cached_topic_markdown,
    clear_topic_markdown_cache,
    calculate_reading_time,
)
from app.services.recommendation_service import (
    get_recommender,
    reset_recommender,
    get_recommendations,
    get_related_topics,
    get_db_state_key,
)
from app.services.quiz_engine import (
    QuestionResultDetail,
    QuizScoreResult,
    evaluate_single_answer,
    score_quiz,
    get_topic_quiz_questions,
)
from app.services.question_loader import (
    QuestionLoader,
    QuestionsSummary,
    QuestionLoaderError,
    QuestionsValidationError,
    MissingQuestionsFileError,
    load_questions,
)

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
    "render_topic_markdown",
    "get_cached_topic_markdown",
    "clear_topic_markdown_cache",
    "calculate_reading_time",
    "get_recommender",
    "reset_recommender",
    "get_recommendations",
    "get_related_topics",
    "get_db_state_key",
    "QuestionResultDetail",
    "QuizScoreResult",
    "evaluate_single_answer",
    "score_quiz",
    "get_topic_quiz_questions",
    "QuestionLoader",
    "QuestionsSummary",
    "QuestionLoaderError",
    "QuestionsValidationError",
    "MissingQuestionsFileError",
    "load_questions",
]

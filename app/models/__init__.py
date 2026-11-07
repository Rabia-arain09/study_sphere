"""Model package exporting all SQLAlchemy entities for StudySphere."""

from app.models.user import User
from app.models.course import Course, CoursePrerequisite
from app.models.topic import Topic, ContentSource
from app.models.prerequisite import Prerequisite
from app.models.resource import Resource, ResourceType
from app.models.question import Question, QuestionType, QuestionSource
from app.models.attempt import Attempt, MasteryLabel
from app.models.attempt_answer import AttemptAnswer, SelfRating
from app.models.upload import Upload, UploadSourceType
from app.models.chat_message import ChatMessage

__all__: list[str] = [
    "User",
    "Course",
    "CoursePrerequisite",
    "Topic",
    "ContentSource",
    "Prerequisite",
    "Resource",
    "ResourceType",
    "Question",
    "QuestionType",
    "QuestionSource",
    "Attempt",
    "MasteryLabel",
    "AttemptAnswer",
    "SelfRating",
    "Upload",
    "UploadSourceType",
    "ChatMessage",
]

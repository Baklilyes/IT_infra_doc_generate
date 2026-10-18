from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.project import ProjectStatus


class WorkflowDecisionResponse(BaseModel):
    id: str
    project_id: str
    action: str
    from_status: str
    to_status: str
    version: str
    comment: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowStatusResponse(BaseModel):
    project_id: str
    reference: str
    name: str
    version: str
    status: ProjectStatus
    is_locked: bool
    can_publish: bool
    blocking_issues_count: int
    allowed_actions: List[str]
    last_decision: Optional[WorkflowDecisionResponse] = None


class WorkflowActionRequest(BaseModel):
    comment: Optional[str] = Field(None, description="Commentaire optionnel pour la décision de validation")


class WorkflowRejectRequest(BaseModel):
    comment: str = Field(
        ...,
        min_length=5,
        description="Motif explicite et argumenté du renvoi pour correction (obligatoire, min 5 caractères)"
    )


class BranchVersionRequest(BaseModel):
    new_version: Optional[str] = Field(
        None,
        max_length=20,
        description="Numéro explicite de la nouvelle version (ex: '1.1', '2.0'). Si non fourni, auto-incrémentation."
    )
    version_bump: str = Field(
        "minor",
        pattern="^(minor|major)$",
        description="Type d'incrément automatique : 'minor' (1.0 -> 1.1) ou 'major' (1.0 -> 2.0)"
    )
    comment: Optional[str] = Field(
        None,
        description="Notes ou objectifs pour cette nouvelle version de travail"
    )

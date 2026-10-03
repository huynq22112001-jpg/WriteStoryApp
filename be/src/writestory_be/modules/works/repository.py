from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from writestory_be.infrastructure.db.models.works import Project, StyleProfile, Work


class WorkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, work_id: str, *, include_deleted: bool = False) -> Work | None:
        query = select(Work).where(Work.id == work_id)
        if not include_deleted:
            query = query.where(Work.deleted_at.is_(None))
        return await self.session.scalar(query)

    async def get_style(self, work_id: str) -> StyleProfile | None:
        return await self.session.scalar(
            select(StyleProfile).where(StyleProfile.work_id == work_id)
        )

    async def default_project_id(self) -> str:
        project_id = await self.session.scalar(
            select(Project.id).order_by(Project.created_at).limit(1)
        )
        if project_id is None:
            raise RuntimeError("Migration F05 must seed the default project")
        return project_id

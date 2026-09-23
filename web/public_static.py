"""Only public web assets belong in this mount; private downloads use auth routes."""
from pathlib import PurePosixPath
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles


class PublicStaticFiles(StaticFiles):
    blocked_suffixes = frozenset({
        '.pdf', '.csv', '.xls', '.xlsx', '.doc', '.docx', '.sql', '.db',
        '.sqlite', '.sqlite3', '.env', '.log', '.bak', '.zip', '.pem', '.key',
    })

    async def get_response(self, path, scope):
        name = PurePosixPath(path)
        if (any(part.startswith('.') and part not in {'.', '..'} for part in name.parts)
                or name.suffix.lower() in self.blocked_suffixes):
            raise HTTPException(status_code=404, detail='Not Found')
        return await super().get_response(path, scope)

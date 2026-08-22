"""Application assembly.

Three jobs: create the app, turn domain errors into HTTP responses, and serve
the built frontend when there is one.

The mapping from error code to HTTP status lives here and nowhere else. It is a
transport concern, and putting it on the exception classes would have given
`core/` an opinion about HTTP, which constitution I forbids.
"""

from __future__ import annotations

import pathlib

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .core.errors import CoreError
from .schemas import Health

VERSION = "0.1.0"

#: Anything not listed is a 422: the request was well formed as JSON but the
#: data or settings in it cannot produce a result. That is the common case, and
#: it is not a server fault.
_STATUS_BY_CODE: dict[str, int] = {
    "JOB_NOT_FOUND": 404,
    "EXAMPLE_NOT_FOUND": 404,
    "INTERNAL": 500,
}
_DEFAULT_STATUS = 422

#: Where the production image puts the built frontend. Absent during backend
#: development, which is why its absence is not an error.
STATIC_DIR = pathlib.Path(__file__).resolve().parents[1] / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nodeless SC Gap Extractor API",
        version=VERSION,
        description=(
            "Extracts the London penetration depth and the single-band nodeless "
            "superconducting gap from self-field transport critical current "
            "density measured as a function of temperature."
        ),
    )

    @app.exception_handler(CoreError)
    async def handle_core_error(_: Request, exc: CoreError) -> JSONResponse:
        """Every domain failure leaves as {"code", "params"} (constitution IV).

        No sentence for a human reader is ever produced here; rendering the code
        into Korean is the frontend's job, and keeping that boundary sharp is
        what stops display text from scattering through English source.
        """
        return JSONResponse(
            status_code=_STATUS_BY_CODE.get(exc.code, _DEFAULT_STATUS),
            content=exc.payload(),
        )

    @app.get("/api/health", response_model=Health, tags=["health"])
    def health() -> Health:
        """Liveness probe, used by the container health check."""
        return Health(version=VERSION)

    app.include_router(router)
    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built single-page frontend, if it has been built.

    In development the Vite dev server serves the frontend itself and proxies
    /api here, so this does nothing. In the production image the build output is
    copied to static/ and this is what the browser talks to: one port, one
    container, no CORS configuration.
    """
    if not STATIC_DIR.is_dir():
        return

    assets = STATIC_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = STATIC_DIR / "index.html"

    # response_model=None because the return type is a union of Response
    # subclasses, which FastAPI would otherwise try to interpret as a Pydantic
    # response model and refuse.
    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def spa(full_path: str) -> FileResponse | JSONResponse:
        """Anything not matched above is a frontend route, so serve the page.

        A single-page application handles its own routing in the browser, so the
        server must answer every unknown path with the same document rather than
        a 404 -- otherwise a reload on any inner page breaks.
        """
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "params": {}})


app = create_app()

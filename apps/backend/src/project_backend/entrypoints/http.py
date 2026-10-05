"""HTTP entrypoint:  uvicorn project_backend.entrypoints.http:app"""

from project_backend.bootstrap.app import create_app
from project_backend.platform.config.settings import Settings

app = create_app(Settings())


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

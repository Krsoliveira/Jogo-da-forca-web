"""Ponto de entrada: `gunicorn app:app` (produção) ou `python app.py` (local)."""

import os

from forca import create_app

app = create_app()

if __name__ == "__main__":
    from waitress import serve

    # Em container é preciso escutar em todas as interfaces; o proxy do Railway faz a exposição.
    serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))  # noqa: S104 # nosec B104

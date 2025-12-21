"""
This file is to customize the OpenAPI documentation interface.
It serves Scalar at /api/docs.

Scalara Docs: https://github.com/scalar/scalar <br/>
Approach: https://github.com/fastapi/fastapi/issues/1198#issuecomment-609019113
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


router = APIRouter()


@router.get("/api/docs", response_class=HTMLResponse, include_in_schema=False)
async def scalar(request: Request):
    return """
<!doctype html>
<html>
  <head>
    <title>%s</title>
    <meta charset="utf-8" />
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1" />
  </head>

  <body>
    <div id="app"></div>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    <script>
      Scalar.createApiReference("#app", {
        url: "%s",
        "theme": "solarized",
        persistAuth: true,
      })
    </script>
  </body>
</html>
    """ % (request.app.title, request.app.openapi_url)

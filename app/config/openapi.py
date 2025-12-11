"""
This file is to customize the OpenAPI documentation interface.
It serves RapiDoc at /api/docs with custom theming.
This serves as an alternative to the default Swagger UI or ReDoc.

RapiDoc Docs: https://rapidocweb.com <br/>
Approach: https://github.com/fastapi/fastapi/issues/1198#issuecomment-609019113
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.config.settings import SettingsDep

router = APIRouter()


@router.get("/api/docs", response_class=HTMLResponse, include_in_schema=False)
async def rapidoc(request: Request, settings: SettingsDep):
    return f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>{request.app.title}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script type="module" src="https://unpkg.com/rapidoc/dist/rapidoc-min.js"></script>
  </head>
  <body>
    <rapi-doc
      spec-url="{request.app.openapi_url}"
      persist-auth="true"
      fill-request-fields-with-example="false"
      theme="light"
      show-method-in-nav-bar="as-colored-block"
      use-path-in-nav-bar="true"
      show-header="false"
      nav-bg-color="{settings.theme_color_background}"
      primary-color="{settings.theme_color_primary}"
    >
    </rapi-doc>
  </body>
</html>
    """

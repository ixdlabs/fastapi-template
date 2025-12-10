from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


# Serve RapiDoc at /api/docs
# https://github.com/fastapi/fastapi/issues/1198
@router.get("/api/docs", response_class=HTMLResponse, include_in_schema=False)
async def rapidoc(request: Request):
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
      nav-bg-color="#111827"
      primary-color="#61A60A"
    >
    </rapi-doc>
  </body>
</html>
    """

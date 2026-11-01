# auth: every /v1 request must carry the shared secret from Laravel:
#   Authorization: Bearer <IMAGE_SERVICE_TOKEN>
import hmac

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .settings import service_token

# HTTPBearer also adds an "Authorize" button to the /docs page
bearer = HTTPBearer(auto_error=False, description='The shared secret IMAGE_SERVICE_TOKEN from the service .env')


def require_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    expected = service_token()
    if not expected:
        # refuse everything rather than run unprotected by accident
        raise HTTPException(503, 'IMAGE_SERVICE_TOKEN is not set on the image service')
    token = credentials.credentials.strip() if credentials else ''
    if token.lower().startswith('bearer '):
        # "Bearer <token>" typed into the /docs Authorize box, which adds its own "Bearer"
        token = token[len('bearer '):].strip()
    # compare_digest takes the same time whether the token is close or not (safer)
    if not token or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(401, 'Missing or wrong token. Send "Authorization: Bearer <IMAGE_SERVICE_TOKEN>". '
                                 'In /docs, click Authorize and paste only the token.',
                            headers={'WWW-Authenticate': 'Bearer'})

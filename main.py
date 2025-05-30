import uvicorn
from config import PORT
import api  # noqa: F401

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=PORT, reload=True)

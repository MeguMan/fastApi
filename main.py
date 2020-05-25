import uvicorn
import redis
import json

from functools import lru_cache

from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.responses import FileResponse

from pydantic import IPvAnyAddress, BaseSettings

from datetime import datetime, timedelta


class Settings(BaseSettings):
    MASK: int = None
    LIMIT: int = None
    TIMEOUT: int = None
    INTERVAL: int = None

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


app = FastAPI()
r = redis.Redis()


@app.get("/")
async def get_text(X_Forwarded_For: IPvAnyAddress = Header(None), settings: Settings = Depends(get_settings)):
    ip = X_Forwarded_For
    net = f'{ip}/{settings.MASK}'
    net_obj = r.get(net)

    if net_obj:
        net_obj = json.loads(net_obj)

        if datetime.now() > datetime.fromtimestamp(net_obj['first_req']) + timedelta(seconds=settings.INTERVAL):
            create_obj(net)

        elif net_obj['req_count'] < settings.LIMIT:
            net_obj['req_count'] += 1
            r.set(net, json.dumps(net_obj))

        else:
            timeout = datetime.now() + timedelta(seconds=settings.TIMEOUT)
            net_obj['timeout'] = timeout.timestamp()
            r.set(net, json.dumps(net_obj))
            raise HTTPException(status_code=429, detail='Too many requests')

    else:
        create_obj(net)

    return FileResponse('static/hello.txt')


def create_obj(net):
    r.set(net, json.dumps({
        'first_req': datetime.now().timestamp(),
        'req_count': 1,
        'timeout': datetime.now().timestamp(),
    }))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


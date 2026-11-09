import logging

from fastapi import FastAPI

from app.api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Crypto Payment Service",
    version="1.0.0",
    description="Takes payments from a client's crypto wallet (Bitcoin Core, regtest).",
)
app.include_router(router)

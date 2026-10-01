from fastapi import FastAPI

from app.routers import auth, cars, categories, locations, users

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(locations.router)
app.include_router(cars.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

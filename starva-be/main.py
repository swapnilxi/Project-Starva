import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Pulse Backend")
print("Hello from starva-be!")

@app.get("/")
async def root():
    return {"message": "St backend running"}

def main():
    print("Starting starva-be backend...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
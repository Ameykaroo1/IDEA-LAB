"""
CRYSTAL-X Backend Application.
Generative AI-Based Novel Crystal Material Discovery for Advanced Energy Applications.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.api.rag_routes import rag_router

app = FastAPI(
    title="CRYSTAL-X Material Discovery Platform",
    description=(
        "Computational research prototype for generative crystal material discovery, "
        "structural validation with pymatgen, property screening, and downstream DFT preparation."
    ),
    version="1.0.0"
)

# CORS middleware for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(rag_router)


@app.get("/")
def root():
    return {
        "platform": "CRYSTAL-X",
        "tagline": "Generative AI-Based Crystal Material Discovery for Advanced Energy Applications",
        "workflow": "Natural Language -> NLP -> Confirmation -> Generation -> Structural Validation -> Screening -> Ranking -> 3D Visualization -> CIF Export -> DFT Queue",
        "scientific_disclaimer": (
            "AI-generated candidates are computational proposals. Structural validity and ML "
            "predictions do not constitute proof of thermodynamic stability, synthesizability, or "
            "experimental performance. High-priority candidates require higher-fidelity computational and experimental validation."
        ),
        "docs_url": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from agent import github_card_agent
from google.genai.types import Content, Part

app = FastAPI(title="GitHub Dev Card Generator API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ADK Services and Runner
session_service = InMemorySessionService()
runner = Runner(
    agent=github_card_agent,
    app_name="github_card_generator",
    session_service=session_service,
)


# Ensure static directories exist
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CARDS_DIR = os.path.join(STATIC_DIR, "cards")
os.makedirs(CARDS_DIR, exist_ok=True)

# Serve generated cards as static files
app.mount("/cards", StaticFiles(directory=CARDS_DIR), name="cards")


class GenerateRequest(BaseModel):
    username: str


# @app.post("/generate")
# async def generate_card(request: GenerateRequest):
#     """
#     Triggers the ADK agent to scrape, analyze, and generate a GitHub card.
#     """
#     username = request.username.strip()
#     if not username:
#         raise HTTPException(status_code=400, detail="Username is required")

#     # Use username as session_id to maintain context per user if needed
#     session_id = f"session_{username}"
#     prompt = f"Generate a dev card for {username}"

#     try:
#         await session_service.create_session(
#             app_name="github_card_generator",
#             user_id="user",
#             session_id=session_id,
#         )
#     except Exception:
#         pass  # Session already exists, reuse it

#     try:
#         # Run the agent and gather the response
#         # In a real streaming scenario, we'd use a StreamingResponse
#         # For this implementation, we'll collect the final output
#         response_content = ""
#         async for event in runner.run_async(
#             user_id="user",
#             session_id=session_id,
#             new_message=Content(parts=[Part(text=prompt)], role="user"),
#         ):
#             if event.content and event.content.parts:
#                 for part in event.content.parts:
#                     if part.text:
#                         response_content += part.text

#         # The agent is instructed to call save_card, which returns the path
#         # We assume the agent's final response or tool output contains the info
#         card_url = f"/cards/{username}.html"

#         return {
#             "status": "success",
#             "username": username,
#             "card_url": card_url,
#             "agent_response": response_content,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate_card(request: GenerateRequest):
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    try:
        from mcp_server import (
            scrape_github,
            analyze_profile,
            generate_card_html,
            save_card,
        )

        github_data = scrape_github(username)
        if "error" in github_data:
            raise HTTPException(status_code=404, detail=github_data["error"])

        analysis = analyze_profile(github_data)
        html = generate_card_html(username, github_data, analysis)
        card_url = save_card(username, html)

        return {
            "status": "success",
            "username": username,
            "card_url": card_url,
            "agent_response": analysis.get("developer_vibe", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Cloud Run health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)

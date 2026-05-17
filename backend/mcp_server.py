import os
import requests
import json
from mcp.server.fastmcp import FastMCP

# google.generativeai is deprecated; use google.genai instead
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

mcp = FastMCP("GitHub-Dev-Card-Generator")

# Initialize Gemini client using API key from environment
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


@mcp.tool()
def scrape_github(username: str) -> dict:
    """Fetch GitHub statistics for a given username using the REST API."""
    headers = {}
    # Use GitHub token if available to avoid rate limiting
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    # User Profile
    user_url = f"https://api.github.com/users/{username}"
    user_resp = requests.get(user_url, headers=headers)
    if user_resp.status_code != 200:
        return {"error": f"User {username} not found."}

    user_data = user_resp.json()

    # Repositories - fetch up to 100 sorted by recently updated
    repos_url = (
        f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100"
    )
    repos_resp = requests.get(repos_url, headers=headers)
    repos_data = repos_resp.json() if repos_resp.status_code == 200 else []

    # Top 6 Repos by star count
    top_repos = sorted(
        repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True
    )[:6]
    top_repos_list = [
        {
            "name": r["name"],
            "stars": r["stargazers_count"],
            "language": r["language"],
            "description": r["description"],
        }
        for r in top_repos
    ]

    # Language Aggregation - count repos per language
    languages = {}
    for r in repos_data:
        lang = r.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    return {
        "name": user_data.get("name") or username,
        "avatar_url": user_data.get("avatar_url"),
        "bio": user_data.get("bio"),
        "location": user_data.get("location"),
        "public_repos": user_data.get("public_repos"),
        "followers": user_data.get("followers"),
        "top_repos": top_repos_list,
        # Top 5 languages sorted by usage
        "languages": dict(
            sorted(languages.items(), key=lambda item: item[1], reverse=True)[:5]
        ),
    }


@mcp.tool()
def analyze_profile(github_data: dict) -> dict:
    """Analyze GitHub data with Gemini to determine developer vibe and theme."""
    prompt = f"""
    Analyze this GitHub profile data and return a JSON object.
    Data: {json.dumps(github_data)}

    Return ONLY a valid JSON object with no markdown, no backticks, no explanation:
    {{
        "developer_vibe": "1 sentence personality",
        "top_skills": ["skill1", "skill2", "skill3"],
        "fun_fact": "something clever inferred from their repos",
        "card_theme": "one of: hacker, builder, researcher, designer, open-source-hero"
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite", contents=prompt
        )
        # Strip markdown code fences if Gemini wraps the JSON in them
        clean_text = response.text.replace("```json", "").replace("```", "").strip()

        return json.loads(clean_text)

    except Exception:
        # Fallback defaults if Gemini call or JSON parsing fails
        return {
            "developer_vibe": "A dedicated code enthusiast.",
            "top_skills": ["Python", "Git", "Problem Solving"],
            "fun_fact": "Has a secret love for clean commits.",
            "card_theme": "builder",
        }


@mcp.tool()
def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Generate a self-contained HTML string for a beautiful dev card."""
    theme = analysis.get("card_theme", "builder")
    # Tailwind class sets per theme
    themes = {
        "hacker": "bg-black text-green-500 font-mono border-green-500",
        "builder": "bg-blue-900 text-white font-sans border-blue-400",
        "researcher": "bg-gray-100 text-gray-800 font-serif border-gray-400",
        "designer": "bg-pink-100 text-pink-900 font-sans border-pink-300",
        "open-source-hero": "bg-orange-500 text-white font-sans border-orange-200",
    }
    theme_class = themes.get(theme, themes["builder"])

    skills_html = "".join(
        [
            f'<span class="px-2 py-1 rounded-full text-xs border border-current mr-2">{s}</span>'
            for s in analysis.get("top_skills", [])
        ]
    )
    # Show only top 3 repos on the card to keep it compact
    repos_html = "".join(
        [
            f'<div class="mb-2"><strong>{r["name"]}</strong> ★{r["stars"]} <span class="text-xs">({r["language"]})</span></div>'
            for r in github_data.get("top_repos", [])[:3]
        ]
    )

    html = f"""
    <div class="p-6 rounded-2xl border-2 shadow-2xl max-w-md {theme_class}">
        <div class="flex items-center mb-4">
            <img src="{github_data.get('avatar_url')}" class="w-20 h-20 rounded-full border-2 border-current mr-4" />
            <div>
                <h2 class="text-2xl font-bold">{github_data.get('name')}</h2>
                <p class="text-sm italic">@{username}</p>
            </div>
        </div>
        <p class="mb-4 text-lg">"{analysis.get('developer_vibe')}"</p>
        <div class="mb-4">{skills_html}</div>
        <div class="grid grid-cols-2 gap-4 mb-4 text-center">
            <div class="p-2 border border-current rounded">
                <div class="text-xl font-bold">{github_data.get('public_repos')}</div>
                <div class="text-xs uppercase">Repos</div>
            </div>
            <div class="p-2 border border-current rounded">
                <div class="text-xl font-bold">{github_data.get('followers')}</div>
                <div class="text-xs uppercase">Followers</div>
            </div>
        </div>
        <div class="mb-4">
            <h3 class="text-sm font-bold uppercase mb-2 border-b border-current">Top Projects</h3>
            {repos_html}
        </div>
        <div class="text-[10px] opacity-75">
            <strong>Fun Fact:</strong> {analysis.get('fun_fact')}
        </div>
    </div>
    """
    return html


@mcp.tool()
def save_card(username: str, html: str) -> str:
    """Save the HTML to static/cards/{username}.html and return the path."""
    path = f"static/cards/{username}.html"
    full_path = os.path.join(os.path.dirname(__file__), path)

    # Wrap the card HTML in a full page template with Tailwind and centered layout
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #1a202c; }}</style>
</head>
<body>
    {html}
</body>
</html>"""

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    # Return the URL path for the frontend to load the card via iframe
    return f"/cards/{username}.html"


if __name__ == "__main__":
    mcp.run()

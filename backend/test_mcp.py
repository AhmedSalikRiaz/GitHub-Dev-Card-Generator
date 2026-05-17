import os
import json
from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


def test_workflow(username: str):
    print(f"--- Testing Workflow for: {username} ---")

    # 1. Scrape GitHub
    print("Step 1: Scraping GitHub...")
    github_data = scrape_github(username)
    if "error" in github_data:
        print(f"FAILED: scrape_github - {github_data['error']}")
        return

    # 2. Analyze Profile
    print("Step 2: Analyzing Profile with Gemini...")
    analysis = analyze_profile(github_data)
    if not analysis or "developer_vibe" not in analysis:
        print(f"FAILED: analyze_profile - Received: {analysis}")
        return

    # 3. Generate HTML
    print("Step 3: Generating HTML Card...")
    html = generate_card_html(username, github_data, analysis)
    if not html:
        print("FAILED: generate_card_html")
        return

    # 4. Results
    print("\n--- RESULTS ---")
    print(f"Developer Vibe: {analysis.get('developer_vibe')}")
    print(f"Card Theme: {analysis.get('card_theme')}")

    # Bonus: Save Card
    card_url = save_card(username, html)
    print(f"Card saved to: {card_url}")
    print("----------------")


if __name__ == "__main__":
    test_workflow("HarshvardhanSingh-13")

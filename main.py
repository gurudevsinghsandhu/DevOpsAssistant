import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize FastAPI
app = FastAPI()

# Mount templates and static folders
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def load_prompt():
    """Load the base system prompt."""
    with open("prompts/resource_estimation.txt", "r") as f:
        return f.read()


def estimate_resources(user_input: str) -> str:
    """Send user input to OpenAI and get a text response."""
    system_prompt = load_prompt()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main input page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/estimate", response_class=HTMLResponse)
async def estimate(request: Request, user_input: str = Form(...)):
    """Handle form submission and show AI response."""
    result_text = estimate_resources(user_input)
    return templates.TemplateResponse(
        "result.html",
        {"request": request, "user_input": user_input, "result": result_text}
    )

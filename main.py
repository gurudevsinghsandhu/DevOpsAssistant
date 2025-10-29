import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from openai import OpenAI

# Load env variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()

# Static & Templates setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load your system prompt
def load_prompt():
    with open("prompts/resource_estimation.txt", "r") as f:
        return f.read()

def estimate_resources(user_input: str):
    system_prompt = load_prompt()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/estimate", response_class=HTMLResponse)
async def estimate(request: Request, app_description: str = Form(...)):
    ai_result = estimate_resources(app_description)
    return templates.TemplateResponse("result.html", {
        "request": request,
        "ai_result": ai_result,
        "user_input": app_description
    })

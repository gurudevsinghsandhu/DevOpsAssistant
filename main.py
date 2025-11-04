import os
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from openai import OpenAI
from passlib.hash import bcrypt
from models import Base, User
from database import engine, SessionLocal
from models import Base, User
from sqlalchemy.orm import Session
from database import Base
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from models import ChatHistory


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize DB
Base.metadata.create_all(bind=engine)

# Load env variables
load_dotenv()

# OpenAI setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# FastAPI app
app = FastAPI()

# Static & Templates setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ------------------------------
# 🔹 Utility Functions
# ------------------------------
def load_prompt():
    """Load the system prompt for resource estimation"""
    with open("prompts/resource_estimation.txt", "r") as f:
        return f.read()


def estimate_resources(user_input: str):
    """Send app description to OpenAI and get resource estimation"""
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


# ------------------------------
# 🌌 Routes
# ------------------------------

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


# ------------------------------
# 👤 Authentication Routes
# ------------------------------

@app.get("/signin", response_class=HTMLResponse)
async def signin_page(request: Request):
    return templates.TemplateResponse("signin.html", {"request": request})


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup", response_class=HTMLResponse)
async def signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    db = SessionLocal()
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return templates.TemplateResponse(
            "signup.html", {"request": request, "error": "⚠️ User already exists!"}
        )

    hashed_pw = bcrypt.hash(password)
    new_user = User(name=name, email=email, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()

    return RedirectResponse(url="/signin", status_code=303)



# Make sure this is added once in your main.py
app.add_middleware(SessionMiddleware, secret_key="63f4945d921d599f27ae4fdf5bada3f1")

@app.post("/signin", response_class=HTMLResponse)
async def signin(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()

    # ❌ Invalid user or password
    if not user or not bcrypt.verify(password, user.password):
        db.close()
        return templates.TemplateResponse(
            "signin.html", {"request": request, "error": "❌ Invalid email or password."}
        )

    # ✅ Store session info
    request.session["user_id"] = user.id

    db.close()

    # ✅ Redirect to dashboard
    return RedirectResponse(url=f"/dashboard/{user.id}", status_code=303)


@app.get("/dashboard/{user_id}", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return RedirectResponse(url="/signin", status_code=303)

        # ✅ Fetch chat history for this user
        chats = (
            db.query(ChatHistory)
            .filter(ChatHistory.user_id == user.id)
            .order_by(ChatHistory.id.desc())
            .all()
        )

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "username": user.name,
                "user_id": user.id,
                "history": chats,  # ✅ Pass real chat history to template
            }
        )
    finally:
        db.close()


@app.post("/chat")
async def chat(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    query = data.get("query")

    if not query:
        return JSONResponse({"error": "Query required"}, status_code=400)

    ai_response = estimate_resources(query)

    # Save chat (temporary: hardcoded user_id=1)
    chat = ChatHistory(user_id=1, query=query, response=ai_response)
    db.add(chat)
    db.commit()
    db.refresh(chat)

    return {"response": ai_response}

@app.get("/chat-history/{user_id}")
def get_chat_history(user_id: int, db: Session = Depends(get_db)):
    chats = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.id.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "query": c.query,
            "response": c.response,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for c in chats
    ]
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()   # ✅ clears the current session
    return RedirectResponse(url="/", status_code=303)
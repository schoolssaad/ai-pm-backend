from fastapi import FastAPI, Depends, HTTPException, Header
from supabase import create_client
import openai
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")

# Middleware: Verify Supabase JWT
async def verify_user(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        user = supabase.auth.get_user(token)
        return user.user.id
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/ai/generate-tasks")
async def generate_tasks(prompt: str, user_id: str = Depends(verify_user)):
    # AI: Break prompt into Agile tasks
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an Agile project manager. Break the user's goal into 5-8 actionable tasks using Scrum/Kanban methodology. Output as JSON list: [{\"title\": \"...\", \"description\": \"...\", \"priority\": \"high/medium/low\"}]"},
            {"role": "user", "content": prompt}
        ]
    )
    tasks = eval(response.choices[0].message['content'])
    return {"tasks": tasks}

@app.post("/trello/create-card")
async def create_trello_card(board_id: str, list_id: str, task: dict, user_id: str = Depends(verify_user)):
    # Get user's Trello token from Supabase
    conn = supabase.table("user_connections").select("trello_token").eq("user_id", user_id).execute()
    if not conn.data:
        raise HTTPException(400, "Connect Trello first")
    
    token = conn.data[0]["trello_token"]
    api_key = os.getenv("TRELLO_API_KEY")
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.trello.com/1/cards",
            params={
                "key": api_key,
                "token": token,
                "idList": list_id,
                "name": task["title"],
                "desc": task["description"]
            }
        )
    return resp.json()

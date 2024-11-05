# main.py
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import asyncio
import os
import uuid
from typing import List, Dict
import json

app = FastAPI()

# In-memory storage (consider using a database in production)
sessions: Dict[str, Dict] = {}

# Pydantic models
class ProcessRequest(BaseModel):
    video_url: str
    prompt: str
    num_generations: int = 3  # Default to 3

class PromptResponse(BaseModel):
    id: int
    name: str
    content: str

class ProcessResponse(BaseModel):
    session_id: str

class StatusResponse(BaseModel):
    status: str

class ResultResponse(BaseModel):
    summaries: Dict
    transcription: str

class SearchRequest(BaseModel):
    search_term: str

class SearchResponse(BaseModel):
    matching_lines: List[str]

class FinalSummaryRequest(BaseModel):
    final_summary: str

# Placeholder functions for actual implementations
async def download_video_temp(video_url):
    # Simulate downloading and converting video to audio
    # await asyncio.sleep(2)
    audio_path = f"audio/{uuid.uuid4()}.mp3"
    video_title = "Sample Video Title"
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    with open(audio_path, "w") as f:
        f.write("Simulated audio content")
    return audio_path, video_title

async def transcribe_audio(audio_path, video_title):
    # Simulate transcription
    # await asyncio.sleep(5)
    transcription = "Transcribed text of the audio."
    return transcription

async def generate_summaries(transcription, prompt, num_generations):
    # Simulate summary generation
    # await asyncio.sleep(2)
    summaries = {f"Summary {i+1}": f"{prompt} applied to the transcription." for i in range(3)}
    return summaries

@app.post("/process_video", response_model=ProcessResponse)
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"status": "processing"}
    background_tasks.add_task(
        processing_task,
        session_id,
        request.video_url,
        request.prompt,
        request.num_generations,
    )
    return ProcessResponse(session_id=session_id)

async def processing_task(session_id, video_url, prompt, num_generations):
    try:
        audio_path, video_title = await download_video_temp(video_url)
        transcription = await transcribe_audio(audio_path, video_title)
        summaries = await generate_summaries(transcription, prompt, num_generations)
        sessions[session_id] = {
            "status": "completed",
            "transcription": transcription,
            "summaries": summaries,
            "final_summary": "",
        }

        # Clean up
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        sessions[session_id] = {"status": "error"}
        print(f"Error in processing task: {e}")

@app.get("/get_status/{session_id}", response_model=StatusResponse)
async def get_status(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return StatusResponse(status=session["status"])

@app.get("/get_results/{session_id}", response_model=ResultResponse)
async def get_results(session_id: str):
    session = sessions.get(session_id)
    if not session or session["status"] != "completed":
        raise HTTPException(status_code=404, detail="Results not available")
    return ResultResponse(
        summaries=session["summaries"],
        transcription=session["transcription"],
    )

@app.post("/search_transcription/{session_id}", response_model=SearchResponse)
async def search_transcription(session_id: str, request: SearchRequest):
    session = sessions.get(session_id)
    if not session or session["status"] != "completed":
        raise HTTPException(status_code=404, detail="Session not found")
    transcription = session["transcription"]
    matching_lines = [
        line for line in transcription.split('\n')
        if request.search_term.lower() in line.lower()
    ]
    return SearchResponse(matching_lines=matching_lines)


@app.get("/get_prompts", response_model=list[PromptResponse])
async def get_prompts():
    with open("prompts.json", "r") as f:
        data = json.load(f)
    return data

@app.post("/save_final_summary/{session_id}", response_model=StatusResponse)
async def save_final_summary(session_id: str, request: FinalSummaryRequest):
    session = sessions.get(session_id)
    if not session or session["status"] != "completed":
        raise HTTPException(status_code=404, detail="Session not found")
    session["final_summary"] = request.final_summary
    return StatusResponse(status="saved")

# CORS middleware to allow requests from the frontend
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend's URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
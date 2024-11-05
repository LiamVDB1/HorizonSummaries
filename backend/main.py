# main.py
from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
import asyncio
import os
import uuid
import json
from typing import List

# Placeholder functions for demonstration purposes
async def download_video_temp(video_url):
    await asyncio.sleep(2)
    audio_path = f"audio/{uuid.uuid4()}.mp3"
    video_title = "Sample Video Title"
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    with open(audio_path, "w") as f:
        f.write("Simulated audio content")
    return audio_path, video_title

async def transcribe_audio(audio_path, video_title):
    await asyncio.sleep(5)
    transcription = "Transcribed text of the audio."
    return transcription

async def generate_summaries(transcription, prompt, num_generations):
    await asyncio.sleep(2)
    summaries = [f"Summary {i+1}: {prompt} applied to the transcription." for i in range(num_generations)]
    return summaries

app = FastAPI()

# Pydantic models
class ProcessRequest(BaseModel):
    video_url: str
    prompt: str
    num_generations: int

class ProcessResponse(BaseModel):
    session_id: str

class StatusResponse(BaseModel):
    status: str

class ResultResponse(BaseModel):
    summaries: List[str]
    transcription: str

class SearchRequest(BaseModel):
    session_id: str
    search_term: str

class SearchResponse(BaseModel):
    matching_lines: List[str]

class FinalSummaryRequest(BaseModel):
    session_id: str
    final_summary: str

# In-memory storage for demonstration (consider using a database in production)
processing_sessions = {}

@app.post("/process_video", response_model=ProcessResponse)
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid.uuid4())
    processing_sessions[session_id] = "processing"
    background_tasks.add_task(processing_task, session_id, request.video_url, request.prompt, request.num_generations)
    return ProcessResponse(session_id=session_id)

async def processing_task(session_id, video_url, prompt, num_generations):
    try:
        audio_path, video_title = await download_video_temp(video_url)
        transcription = await transcribe_audio(audio_path, video_title)
        summaries = await generate_summaries(transcription, prompt, num_generations)

        # Save results in memory (or database)
        processing_sessions[session_id] = {
            "transcription": transcription,
            "summaries": summaries,
            "final_summary": ""
        }

        # Clean up
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        processing_sessions[session_id] = "error"

@app.get("/get_status/{session_id}", response_model=StatusResponse)
async def get_status(session_id: str):
    status = processing_sessions.get(session_id, None)
    if status == "processing":
        return StatusResponse(status="processing")
    elif status == "error":
        return StatusResponse(status="error")
    elif status is not None:
        return StatusResponse(status="completed")
    else:
        return StatusResponse(status="not_found")

@app.get("/get_results/{session_id}", response_model=ResultResponse)
async def get_results(session_id: str):
    data = processing_sessions.get(session_id, None)
    if data and isinstance(data, dict):
        return ResultResponse(
            summaries=data["summaries"],
            transcription=data["transcription"]
        )
    else:
        return {"detail": "Results not found"}, 404

@app.post("/search_transcription", response_model=SearchResponse)
async def search_transcription(request: SearchRequest):
    data = processing_sessions.get(request.session_id, None)
    if data and isinstance(data, dict):
        transcription = data["transcription"]
        matching_lines = [line for line in transcription.split('\n') if request.search_term.lower() in line.lower()]
        return SearchResponse(matching_lines=matching_lines)
    else:
        return {"detail": "Session not found"}, 404

@app.post("/save_final_summary", response_model=StatusResponse)
async def save_final_summary(request: FinalSummaryRequest):
    data = processing_sessions.get(request.session_id, None)
    if data and isinstance(data, dict):
        data["final_summary"] = request.final_summary
        return StatusResponse(status="saved")
    else:
        return {"detail": "Session not found"}, 404

@app.get("/get_prompts")
async def get_prompts():
    with open("prompts.json", "r") as f:
        data = json.load(f)
    return data["prompts"]

@app.post("/add_prompt")
async def add_prompt(prompt: str):
    with open("prompts.json", "r") as f:
        data = json.load(f)
    data["prompts"].append(prompt)
    with open("prompts.json", "w") as f:
        json.dump(data, f, indent=4)
    return {"status": "prompt added"}

# Include CORS middleware to allow cross-origin requests from the React frontend
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend's domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
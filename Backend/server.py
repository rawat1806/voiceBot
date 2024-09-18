# fastapi_server.py
from fastapi import FastAPI
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict
import uvicorn
import os
from transformers import pipeline, AutoTokenizer
import torch
import re
from parler_tts import ParlerTTSForConditionalGeneration #git install or clone 
import soundfile as sf


app = FastAPI()
UPLOAD_DIR = "./"
pipe = pipeline("automatic-speech-recognition", model="openai/whisper-tiny.en")
pipe2 = pipeline("text-generation", model="TinyLlama/TinyLlama-1.1B-Chat-v1.0", torch_dtype=torch.bfloat16)
default_prompt_to_llm_text = "You are a support agent. Your task is to take details from the user and keep him calm. Limit your response to 10 words."
default_prompt_to_llm_voice = "A female speaker delivers with a moderate speed and pitch, with a very close recording that almost has no background noise."



class Input(BaseModel):
    input: str


def audio_to_text(file_path):
    # Use the Hugging Face pipeline to transcribe the audio
    text = pipe(file_path)
    return text

def extract_assistant_response(text):
    # Regex to find the assistant's response
    match = re.search(r'\n<\|assistant\|>\n(.*)', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return "No assistant response found."


@app.post("/chat")
async def assistant_response(input: Input):
    messages = [
        {
            "role": "system",
            "content": default_prompt_to_llm_text,
        },
        {
            "role": "user",
            "content": input.input,
        },
    ]

    prompt = pipe2.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    outputs = pipe2(prompt, max_new_tokens=256, do_sample=True, temperature=0.7, top_k=50, top_p=0.95)
    assitantResponse = outputs[0]["generated_text"]
    response = extract_assistant_response(assitantResponse)
    return {"text": response}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        # Save the uploaded file to the UPLOAD_DIR
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as f:
            f.write(await file.read())
        response = audio_to_text(file_location)    
        # Return success response
        return {"text": response}
    except Exception as e:
        return JSONResponse(content={"message": f"Error occurred: Transcribe failed"}, status_code=500)


@app.post("/audio")
async def audio(input: Input):
    text = input.input
    device = "cpu" # "cuda:0" if torch.cuda.is_available() else "cpu" -- for GPU usage
    try:
        model = ParlerTTSForConditionalGeneration.from_pretrained("parler-tts/parler-tts-mini-v1").to(device)
        tokenizer = AutoTokenizer.from_pretrained("parler-tts/parler-tts-mini-v1")
        input_ids = tokenizer(default_prompt_to_llm_voice, return_tensors="pt").input_ids.to(device)
        prompt_input_ids = tokenizer(text, return_tensors="pt").input_ids.to(device)
        generation = model.generate(input_ids=input_ids, prompt_input_ids=prompt_input_ids)
        audio_arr = generation.cpu().numpy().squeeze()
        audio_file_path = UPLOAD_DIR + "audiofile.mp3"
        sf.write(audio_file_path, audio_arr, model.config.sampling_rate)
        return FileResponse(audio_file_path, media_type='audio/mpeg', filename="audiofile.mp3")
    except Exception as e:
        return JSONResponse(content={"message": f"Error occurred: Text to audio failed"}, status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

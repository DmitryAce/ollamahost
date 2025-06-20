import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any  # Updated import
import httpx
import uvicorn

app = FastAPI()

# Загрузка конфигурации
try:
    with open("config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    raise RuntimeError("Config file not found")
except json.JSONDecodeError:
    raise RuntimeError("Invalid config file")

# Константы для управления ресурсами
GLOBAL_MAX_LENGTH = 500
INPUT_MAX_LENGTH = 1000
TIMEOUT = 30

class GenerateRequest(BaseModel):
    text: str
    mode: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None  # Fixed type hint

@app.post("/generate")
async def generate(request: GenerateRequest):
    if len(request.text) > INPUT_MAX_LENGTH:
        raise HTTPException(status_code=400, detail="Input text too long")
    
    # Определение настроек
    if request.mode:
        if request.mode in config["modes"]:
            settings = config["modes"][request.mode].copy()
        else:
            raise HTTPException(status_code=400, detail="Mode not found")
    else:
        settings = config["default"].copy()
    
    # Переопределение настроек из запроса
    if request.settings:
        settings.update(request.settings)
    
    # Ограничение максимальной длины ответа
    if "max_length" in settings:
        settings["max_length"] = min(settings["max_length"], GLOBAL_MAX_LENGTH)
    else:
        settings["max_length"] = GLOBAL_MAX_LENGTH
    
    # Подготовка данных для Ollama
    ollama_data = {
        "prompt": request.text,
        **settings
    }
    
    # Отправка запроса к Ollama
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("http://localhost:11434/generate", json=ollama_data, timeout=TIMEOUT)
            response.raise_for_status()
            result = response.json()
            return {"response": result["text"]}
        except httpx.HTTPStatusError:
            raise HTTPException(status_code=500, detail="Error communicating with Ollama")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request to Ollama timed out")
        
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8434)
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
import openai
import os

# класс с типами данных параметров 
class Item(BaseModel): 
    text: str

# создаем объект приложения
app = FastAPI()

client = openai.OpenAI()

# настройки для работы запросов
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def gen_questions (self, system:str, assistant:str, user:str):
        '''Асинхронная функция получения ответа от chatgpt
        '''
       
        messages = [
            {"role": "system", "content": system},
            {"role": "assistant", "content": assistant},
            {"role": "user", "content": user}
            ]

        # получение ответа от chatgpt
        completion = await openai.ChatCompletion.acreate(model="gpt-4o",
                                                  messages=messages,
                                                  temperature=0.1)
        
        return completion.choices[0].message.content



# асинхронная функция обработки post запроса + декоратор 
@app.post("/api/get_answer_async")
async def gen_questions(question: Item): #ДОБАВИТЬ ПАРАМЕТРЫ
    answer = await gen_questions(query=question.text) #ДОБАВИТЬ ПАРАМЕТРЫ
    return {"message": answer}


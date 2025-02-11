import requests
import os
from dotenv import dotenv_values
from langchain.agents import AgentExecutor
from langchain.agents import create_openai_functions_agent
import os
from langchain import hub
from langchain_openai import ChatOpenAI
from PyPDF2 import PdfReader

env_path = os.path.join(os.path.dirname(__file__), '.env')
config = dotenv_values(env_path)
        
        # Get API keys directly from the config
elevenlabs_api_key = config.get("ELEVENLABS_API_KEY")
openai_api_key = config.get("OPENAI_API_KEY")

voice_ids = {"woman" : "21m00Tcm4TlvDq8ikWAM", "man" : "pqHfZKP75CvOlQylNhV4"}

def synthesize_text_to_speech(gender: str, text: str, output_filename: str = "output.mp3", 
                                stability: float = 0.75, similarity_boost: float = 0.75) -> None:
    """
    Synthesize speech from text using the ElevenLabs API and save it as an MP3 file.

    Parameters:
        api_key (str): Your ElevenLabs API key.
        voice_id (str): The ID of the voice to use.
        text (str): The text to convert to speech.
        output_filename (str): The file name to save the audio to (default is "output.mp3").
        stability (float): Stability setting for voice synthesis.
        similarity_boost (float): Similarity boost setting for voice synthesis.
    """
    voice_id = voice_ids[gender]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "xi-api-key": elevenlabs_api_key,
        "Content-Type": "application/json"
    }
    
    data = {
        "text": text,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()  # Raise an exception if the request failed
    
    with open(output_filename, "wb") as file:
        file.write(response.content)
    
    print(f"Audio saved to {output_filename}")

# Example usage:
#synthesize_text_to_speech("man", "Hello, how are you today?")

from openai import OpenAI

def transcribe() :
    client = OpenAI(api_key=openai_api_key)

    audio_file = open("./input.mp3", "rb")
    transcription = client.audio.translations.create(
        model="whisper-1", 
        file=audio_file
    )

    print(transcription.text)

    return transcription.text

from langchain.agents import Tool
# Import your TextVectorStore class from your module
from vector_index import TextVectorStore

# Initialize the vector store globally (so it persists across calls)
text_store = TextVectorStore()

# Pre-load the vector store with a sample document (if not already loaded)

def vector_store_query(query: str) -> str:
    """
    Query the vector store for the given query and return a formatted result string.
    """
    results = text_store.query(query)
    if not results:
        return "No relevant documents found."
    
    output = ""
    for doc in results:
        output += f"Result: {doc.page_content}\n"
        output += f"Title: {doc.metadata.get('title', 'N/A')}\n"
        output += f"Link: {doc.metadata.get('link', 'N/A')}\n"
        output += f"Source: {doc.metadata.get('source', 'N/A')}\n"
        output += f"Author: {doc.metadata.get('author', 'N/A')}\n\n"
    return output

# Wrap the function as a LangChain Tool
vector_store_tool = Tool(
    name="VectorStoreQuery",
    func=vector_store_query,
    description="Queries the text vector store and returns relevant document excerpts along with metadata (title, link, source, author)."
)

# Example usage:
if __name__ == "__main__":
    query = "What is machine learning?"
    result_text = vector_store_tool.func(query)
    print(result_text)


def run_agent(input: str) :
    tools = [vector_store_tool]

    prompt = hub.pull("hwchase17/openai-functions-agent")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


    response = agent_executor.invoke({"input":f""" You are an helpful AI medical agent called MedSync. 
                        You have been provided patient education material endpoint to get information for actual cancer patients, as well as an email endpoint. 
                        answer the user query to the best of your ability.  Since you are a conversational agent keep you answer's very concise so it feels like a conversation. dont make bullet points or use ** for markdown, just simple paragraphs as we are using Text To Speech tech.
                        User query : {input}"""})
    print(response["output"])
    return response["output"]

async def run_agent_voice(gender: str) -> None:
    """Async wrapper for the agent voice processing"""
    text = transcribe()
    response = run_agent(text)
    synthesize_text_to_speech(gender=gender, text=response)

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
import shutil
import os

app = FastAPI()

@app.post("/process-audio")
async def process_audio(
    audio: UploadFile = File(...),
    gender: str = Form(...)
):
    try:
        # Save the uploaded audio file as input.mp3
        with open("input.mp3", "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        
        # Run the agent voice processing
        await run_agent_voice(gender)
        
        # Return the output.mp3 file
        if os.path.exists("output.mp3"):
            return FileResponse(
                "output.mp3",
                media_type="audio/mpeg",
                filename="response.mp3"
            )
        else:
            return {"error": "Failed to generate response audio"}
            
    except Exception as e:
        print(f"Error processing request: {str(e)}")  # Add logging
        return {"error": str(e)}
    finally:
        # Clean up the input file
        if os.path.exists("input.mp3"):
            os.remove("input.mp3")

@app.post("/process-pdf")
async def process_pdf(
    pdf: UploadFile = File(...),
    title: str = Form(""),
    link: str = Form(""),
    source: str = Form("")
):
    """
    Endpoint to process a PDF file.
    - Extracts text from the uploaded PDF.
    - Uses the TextVectorStore to process and add the extracted text to the vector database.
    - Expects additional metadata: title, link, and source.
    """
    try:
        # Use PyPDF2 to read the PDF from the file object
        pdf_reader = PdfReader(pdf.file)
        extracted_text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text + "\n"
        
        if not extracted_text:
            return {"error": "No text could be extracted from the PDF."}
        
        # Initialize TextVectorStore and process the extracted text
        text_store = TextVectorStore()
        metadata = {"title": title, "link": link, "source": source}
        success = text_store.process_text(extracted_text, metadata)
        if success:
            return {"message": "PDF processed successfully and added to vector store"}
        else:
            return {"error": "Failed to process PDF text into the vector database"}
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return {"error": str(e)}

# Optional: Add a health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main_llm:app", host="0.0.0.0", port=8000, reload=True)


# for config in sample_api_configs :


import json
import sys
import time
from collections import deque
import io
from PIL import Image
import os
from dotenv import load_dotenv
import openai
from openai import AzureOpenAI
import numpy as np
import imagehash
import av
import azure.cognitiveservices.speech as speechsdk
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
import subprocess
import threading
import requests
import tiktoken
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    VectorSearch,
    SearchField,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    HnswParameters,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile
)
from azure.search.documents.models import (
    VectorizedQuery
)

tokenizer = tiktoken.get_encoding("cl100k_base")
load_dotenv('./keys.env')
client = AzureOpenAI(
         azure_endpoint = os.getenv('azure_endpoint'), 
         api_key=os.getenv('OPENAI_API_KEY'),  
         api_version=os.getenv('api_version')
         )

"""
Preamble: The following code handles the backend logic for a tool that addresses a problem in education using AI. During a professor's lecture, students have limited ways to address conceptual misunderstandings. 
They could raise their hand and ask the professor a question, but this method becomes problematic in a lecture hall filled with hundreds of students. Furthermore, students might be intimidated to interupt the lecturer to ask a question.
In an ideal world, each student could have a personal tutor that is an expert of the course and understands what the professor is currently talking about during lecture to answer real-time questions. Unfortunately, 
it is unlikely that colleges can provide this support. This is a problem in education that can be solved with AI. The code below formulates an AI chatbot that has access to the course notes and real time video and audio lecture data. 
First, the student question is given to multiple keyword search vector indices that retrieve the relevent lecture video, lecturer audio, and course notes context. The most recent audio and video chunks from the lecture livestream are also computed.
This information is prompt engineered and then given to an LLM to provide the student with an answer. This code currently works for local livestreams and the next goal is to have this work for livestreamed and in-person lectures.
"""

def delete_existing_index():

    """Deletes the audio and video indices from Azure if they exist."""
    
    try:
        index_client.get_index(audio_index_lec) #checks if there is an index with this name stored
        index_client.delete_index(audio_index_lec) #deletes index
    except Exception:
        pass

    try:
        index_client.get_index(video_index_lec) #checks if there is an index with this name stored
        index_client.delete_index(video_index_lec) #deletes index
    except Exception:
        pass

def handle_transcription(evt):
    """
    Processes transcriptions generated from an audio stream, extracts words from the transcription, stores them in a buffer, and uploads the transcription to Azure Search index.

    Parameters:
        evt: Event object from Azure's speech recognition service.

    """
    global transcription_counter #tracks counter across multiple function calls
    transcription = evt.result.text #extracts the transcription text from the event.
    words = transcription.split() #splits the transcription into individual words (by spaces)
    with index_lock:  #ensures that multiple items can be uploaded to the same index without causing conflicts
        word_buffer.extend(words) #appends words in transcript to the total of words spoken so far
    update_vector_index(transcription, f"transcription-{transcription_counter}", audio_search_client, audio_index_lec)
    transcription_counter += 1

# def handle_transcription(evt, start_time):
#     """
#     Processes transcriptions generated from an audio stream, extracts words from the transcription,
#     stores them in a buffer, and uploads the transcription to Azure Search index.
#
#     Parameters:
#         evt: Event object from Azure's speech recognition service.
#         start_time: The time when the script started running.
#     """
#     global transcription_counter
#     transcription = evt.result.text
#     words = transcription.split()
#     elapsed_time = time.time() - start_time  # Calculate elapsed time since script start
#
#     if not transcription:
#         print("[DEBUG] Empty transcription received")
#         return
#
#     print(f"[DEBUG] Transcription received: '{transcription}'")
#
#     with index_lock:
#         word_buffer.extend(words)
#
#         # Save transcription with timestamp
#     audio_snippets.append({"timestamp": elapsed_time, "text": transcription})
#
#     update_vector_index(transcription, f"transcription-{transcription_counter}", audio_search_client,
#                         audio_index_lec)
#     transcription_counter += 1

def generate_embeddings(texts):
    try:
        chunks = chunk_text(texts)
        response = client.embeddings.create(
            input = chunks,
            model= "text-embedding-ada-002"
        )
        embeddings = [data.embedding for data in response.data]
        return embeddings
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None

def create_vector_index():
    try:
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="text", type=SearchFieldDataType.String),
            SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=1536,
            vector_search_profile_name="my-vector-config")
        ]
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="my-hnsw",
                    kind=VectorSearchAlgorithmKind.HNSW,
                    parameters=HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric=VectorSearchAlgorithmMetric.COSINE,
                    ),
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="my-vector-config",
                    algorithm_configuration_name="my-hnsw",
                )
            ],
        )
        audio_index = SearchIndex(name=audio_index_lec, fields=fields, vector_search=vector_search)
        video_index = SearchIndex(name=video_index_lec, fields=fields, vector_search=vector_search)
        index_client.create_or_update_index(video_index)
        index_client.create_or_update_index(audio_index)
        print(f"Index '{audio_index_lec}' created successfully.")
        print(f"Index '{video_index_lec}' created successfully.")
    except Exception as e:
        print(f"Vector Index creation failed: {e}")

def chunk_text(texts, max_tokens=int(os.getenv('max_tokens'))):
    chunks = []
    current_chunk = []
    current_token_count = 0

    for text in texts:
        tokens = tokenizer.encode(text)
        token_length = len(tokens)

        if current_token_count + token_length > max_tokens:
            if current_chunk:
                chunks.append("".join(current_chunk))
            current_chunk = [text]
            current_token_count = token_length
        else:
            current_chunk.append(text)
            current_token_count += token_length

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks

def update_vector_index(transcription, transcription_id, search_client, client_name):
    try:
        with index_lock:
            chunks = chunk_text(transcription)
            for chunk in chunks:
                embeddings = generate_embeddings(chunk)
                for embedding in embeddings:
                    document = {
                        "embedding": embedding,
                        "text": chunk,
                        "id": transcription_id

                    }
                    search_client.upload_documents(documents=document)
            print(f"successfully uploaded to {client_name} index")
            # print(chunk)
    except Exception as e:
        print(f"Failed to upload transcription: {e}")

def generate_gpt_response(prompt, max_retries=5, wait_time=10):

    """
    Sends a prompt to a GPT LLM hosted on Azure and retrieves the model's response.

    Parameters:
        prompt: A list of messages (that are dictionaries) forming the conversation history and user input.

    Returns: GPT LLM response (string).

    """

    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv('OPENAI_API_KEY')
    }
    payload = {
        "messages": prompt,
        "temperature": 0.1,
        "top_p": 0.95,
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(os.getenv('OPENAI_ENDPOINT'), headers=headers, json=payload)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']

        except requests.exceptions.RequestException as e:
            if response.status_code == 429:  # Rate limit exceeded
                if attempt < max_retries - 1:
                    print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    wait_time *= 2  # Exponential backoff
                else:
                    raise RuntimeError("Max retries reached. Failed to get a response from GPT.")
            else:
                raise e #extracts and returns the model's response

def summarize_conversation(history):

    """
    Takes a conversation history and generates a summary of it using a GPT LLM.

    Parameters:
        history: String containing the conversation to be summarized.

    Returns: Summary of inputted conversation (string).

    """

    summary_prompt = [
        {"role": "system", "content": "You are a summarization assistant."},
        {"role": "user", "content": f"Summarize the following conversation:\n\n{history}"}
    ]
    try:
        return generate_gpt_response(summary_prompt) #prompts LLM to summarize conversation
    except Exception as e:
        print(f"Error generating conversation summary: {e}")
        return ""

def retrieve_top_search_results(query):

    """
    Queries multiple Azure Search indices (audio, notes, and video) and retrieves the top search results for a given query. Performs keyword-based searches across these indices and return the most relevant content.

    Parameters:
        query: String containing the search term or query.

    Returns: A list of the most relevent audio context segments, list of the most relevent course note segments, and a list of the most relevent video segments (tuple of 3 lists of strings).

    """

    try:
        tokens = tokenizer.encode(query)
        if(len(tokens) > int(os.getenv('max_tokens'))):
            raise ValueError("query cannot exceed max token length")
        vector_query = VectorizedQuery(vector=generate_embeddings(query)[0], k_nearest_neighbors=2, fields="embedding")
        audio_results = audio_search_client.search(
            search_text=None,
            vector_queries= [vector_query],
            select=["text"]
        )
        audio_rag = [audio['text'] for audio in audio_results]
        video_results = video_search_client.search(
            search_text=None,
            vector_queries= [vector_query],
            select=["text"]
        )
        video_rag = [video['text'] for video in video_results]

        notes_results = notes_search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            select=["text"]
        )
        notes_rag = [notes['text'] for notes in notes_results]
        # return texts
        # audio_results = audio_search_client.search(query, top=3) #retrieves the top 3 most relevent audio segments
        # notes_results = notes_search_client.search(query, top=3) #retrieves the top 3 most relevent course note segments
        #video_results = video_search_client.search(query, top=2) #retrieves the top 2 most relevent video segments
        return audio_rag, notes_rag, video_rag
    except Exception as e:
        print(f"Query failed: {e}")
        return [], [], []

def image_to_stream(pil_image):
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

def perform_ocr(frame_pil):

    """
    Uses Azure Cognitive Services' Computer Vision API to perform Optical Character Recognition (OCR) on a given image.

    Parameters:
        frame_pil: Image in Pillow format (PIL.Image object).

    Returns: Extracted OCR text from given image (string).

    """

    image_stream = image_to_stream(frame_pil) #image is converted into a binary stream
    read_response = computervision_client.read_in_stream(image_stream, raw=True) #image stream is sent to Azure Computer Vision's Read API for OCR processing
    read_operation_location = read_response.headers["Operation-Location"] #gets URL for operation status
    operation_id = read_operation_location.split("/")[-1] #extracts the operation ID from this URL

    while True: #exits loop once OCR is complete or failed
        read_result = computervision_client.get_read_result(operation_id) #gets status of operation
        if read_result.status not in ['notStarted', 'running']:
            break
        time.sleep(1) #adds time between calls to avoid reaching request limit
    extracted_text = ""
    if read_result.status == OperationStatusCodes.succeeded:
        for text_result in read_result.analyze_result.read_results: #concatenates the entire result into a string
            for line in text_result.lines:
                extracted_text += line.text + "\n"
    return extracted_text

def process_video_stream(stream_url, hash_threshold=2, n=5):

    """
    Processes a video stream frame by frame, extracts text from unique frames using OCR, and uploads the extracted text to an Azure Search index.

    Parameters:
        stream_url: The URL of the video stream to be processed.
        hash_threshold: Threshold value used to determine whether two frames are considered similar.
        n: Maximum number of unique frame hashes to keep in memory.

    """

    saved_frame_hashes = [] #stores perceptual hashes of processed frames
    try:
        container = av.open(stream_url) #opens stream and prepares it for decoding
        counter = 0
        for frame in container.decode(video=0): #iterates through all the video frames from a live stream
            counter += 1
            if counter % 120 == 0: #processes a frame every 4 seconds
                frame_array = frame.to_ndarray(format="rgb24") #converts video frame to an array of pixel data
                frame_pil = Image.fromarray(frame_array) #converts frame to PIL format
                frame_hash = imagehash.phash(frame_pil) #calculates perceptual hash to determine if the current frame is similar to previously processed frames
                is_unique = True

                for saved_hash in saved_frame_hashes:
                    if abs(frame_hash - saved_hash) < hash_threshold: #if the difference between hashes is less than hash_threshold then the frame is not unique
                        is_unique = False
                        break

                if is_unique:
                    extracted_text = perform_ocr(frame_pil) #extracts text from the frame using OCR
                    update_vector_index(extracted_text, f"frame-{counter}", video_search_client, video_index_lec)
                    saved_frame_hashes.append(frame_hash) #adds the frame’s hash to saved_frame_hashes

                    elapsed_time = time.time() - start_time  # Calculate elapsed time since script start

                    # Save video snippet with timestamp
                    video_snippets.append({"timestamp": elapsed_time, "text": extracted_text})

                    video_buffer.append(extracted_text)
                    # video_buffer.append(extracted_text) #appends extracted text to entire OCR text from video stream

                    if len(saved_frame_hashes) > n: #limits the comparison of perceptual hashes to only the most recent n video frames
                        saved_frame_hashes.pop(0)
    except av.AVError as e:
        print(f"Failed to process stream: {e}")


def process_audio_stream():

    """Processes an audio stream by reading chunks of audio data from a live feed and writing it to a push audio stream to be uploaded to an Azure Search index in the future."""

    try:
        while not stop_event.is_set():
            chunk = ffmpeg_proc.stdout.read(4096) #continuously reads audio data in chunks of 4096 bytes
            if not chunk:
                break
            push_stream.write(chunk) #writes chunk to push_stream
    except KeyboardInterrupt:
        stop_event.set()
    finally: #releases all resources used during audio processing
        recognizer.stop_continuous_recognition() #stops the speech recognition process
        push_stream.close() #closes the push audio stream to free resources
        ffmpeg_proc.terminate() #stops the FFmpeg process that is providing the audio data

def user_input_thread(user_input=None):

    """
    Handles user interactions with the Askademia bot. It processes user input, retrieves relevant contextual information, formats a prompt for the LLM model, and generates a response.

    Parameters:
        user_input: A string containing the user's question.

    """

    #print('=' * 50)

    if not user_input: #initially encourages the user to ask a question
        question = input("Enter your question (or 'new' to start a new conversation, 'exit' to quit): ").strip()
    else:
        question = user_input

    with index_lock: #ensures safe access to shared resources (word_buffer and video_buffer) in this multi-threaded environment
        recent_audio = " ".join(word_buffer)  #combines the rolling window of recent audio transcriptions (word_buffer) into a single string
        recent_video = "\n".join(video_buffer) #combines the rolling window of recent video OCR results (video_buffer) into a single string

    formatted_history = "\t"+"\n\t".join( #formats recent conversation history into a readable string for inclusion in the prompt
        f'User: "{h["user"]}"\n\tAssistant: "{h["assistant"]}"' for h in list(conversation_history)
    )

    audio_vector, notes_vector, video_vector = retrieve_top_search_results(question) #searches the audio, notes, and video indices for context relevant to the user's question
    audio_vector, notes_vector, video_vector = '\n'.join(audio_vector), '\n'.join(notes_vector), '\n'.join(video_vector) #combines the retrieved results into single strings for inclusion in the prompt

    system_message = (
        "You are an AI assistant helping students understand lectures. "
        "Please use the provided context from the lecture to answer the student's question. "
        "Any 'video' context refers to information displayed on the screen. This is important. "
        "Please answer the question in the context of the conversation history provided, if any. "
        "Please limit your response to a maximum of 4 sentences."
    )

    response_json = {
        "Conversation History": formatted_history,
        "Retrieved Notes": notes_vector,
        "Retrieved Audio": audio_vector,
        "Retrieved Video": video_vector,
        "Recent Audio": recent_audio,
        "Recent Video": recent_video
    }

    formatted_prompt = "\n\n".join(f"{key}:\n{value}" for key, value in response_json.items())

    prompt = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"Context: {formatted_prompt}\n\nQuestion: {question}"},
    ]

    #print(formatted_prompt)

    response_json['GPT Response'] = generate_gpt_response(prompt)

    return response_json

# def save_audio_snippets():
#     """
#     Periodically saves the collected audio snippets with timestamps to a JSON file.
#     """
#     while not stop_event.is_set():
#         time.sleep(10)  # Save every 10 seconds
#         with open(f"fa24_timestamped/audio{lecture_number}.json", "w", encoding="utf-8") as f:
#             json.dump(audio_snippets, f, indent=4)
#
#
# def save_video_snippets():
#     """
#     Periodically saves the collected video snippets with timestamps to a JSON file.
#     """
#     while not stop_event.is_set():
#         time.sleep(10)  # Save every 10 seconds
#         with open(f"fa24_timestamped/video{lecture_number}.json", "w", encoding="utf-8") as f:
#             json.dump(video_snippets, f, indent=4)
#
#
# lecture_number = 6 #os.getenv("LECTURE_NUMBER", "")
audio_index_lec = os.getenv('AUDIO_INDEX_NAME') #+ str(int(lecture_number) % 7)
video_index_lec = os.getenv('VIDEO_INDEX_NAME') #+ str(int(lecture_number) % 7)

speech_config = speechsdk.SpeechConfig(subscription=os.getenv('speech_key'), region=os.getenv('service_region'))

EMBEDDING_MODEL_DIMENSIONS = 1536
index_client = SearchIndexClient(os.getenv('SEARCH_ENDPOINT'), AzureKeyCredential(os.getenv('SEARCH_KEY')))

print("message before")
computervision_client = ComputerVisionClient(os.getenv('endpoint'), CognitiveServicesCredentials(os.getenv('subscription_key')))
audio_search_client = SearchClient(os.getenv('SEARCH_ENDPOINT'), audio_index_lec, AzureKeyCredential(os.getenv('SEARCH_KEY')))
notes_search_client = SearchClient(os.getenv('SEARCH_ENDPOINT'), os.getenv('NOTES_INDEX_NAME'), AzureKeyCredential(os.getenv('SEARCH_KEY')))
video_search_client = SearchClient(os.getenv('SEARCH_ENDPOINT'), video_index_lec, AzureKeyCredential(os.getenv('SEARCH_KEY')))
print('message after')
#initializes storage devices
audio_snippets = []  # List to store transcriptions with timestamps
video_snippets = []  # List to store transcriptions with timestamps
start_time = time.time()
index_lock = threading.Lock() #for multiple threading
word_buffer = deque(maxlen=256) #stores rolling audio transcription
video_buffer = deque(maxlen=2) #stores rolling video frame OCR
conversation_history = deque(maxlen=5) #chatbot and user conversation history

delete_existing_index()
create_vector_index()

#initializes audio transcription streaming devices
push_stream = speechsdk.audio.PushAudioInputStream()
audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

#streaming info
ffmpeg_cmd = [
    "ffmpeg",
    "-i", f"rtmp://localhost/live/my_stream",
    "-vn",
    "-ar", "16000",
    "-ac", "1",
    "-f", "wav",
    "pipe:1"
]
ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

transcription_counter = 1

recognizer.recognized.connect(handle_transcription)
# recognizer.recognized.connect(lambda evt: handle_transcription(evt, start_time))
stop_event = threading.Event()

recognizer.start_continuous_recognition()

stream_url = f"rtmp://localhost/live/my_stream"
saved_frame_hashes = []
hash_threshold = 2
n = 5

video_thread = threading.Thread(target=process_video_stream, args=(stream_url,), daemon=True)
audio_thread = threading.Thread(target=process_audio_stream, daemon=True)
# audio_save_thread = threading.Thread(target=save_audio_snippets, daemon=True)
# video_save_thread = threading.Thread(target=save_video_snippets, daemon=True)

video_thread.start()
audio_thread.start()
# audio_save_thread.start()
# video_save_thread.start()

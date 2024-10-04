import os
from chromadb.utils import embedding_functions

def get_chroma_openai_embedding_fn():
    return embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ['OPENAI_API_KEY'].strip(),
            model_name=os.environ["OPENAI_API_EMBED_MODEL"].strip(),
        )
import streamlit as st
import tiktoken
from loguru import logger

from langchain.chains import ConversationalRetrievalChain

from langchain.document_loaders import PyPDFLoader
from langchain.document_loaders import Docx2txtLoader
from langchain.document_loaders import UnstructuredPowerPointLoader

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings

from langchain.memory import ConversationBufferMemory
from langchain.vectorstores import FAISS

from langchain.memory import StreamlitChatMessageHistory

from langchain_google_genai import ChatGoogleGenerativeAI
import os

def main():
    
    st.set_page_config(
    page_title="Streamlit_Rag",
    page_icon=":books:")
    
    st.title("_Private Data :red[Q/A chat]_ :books:")
    
    if "conversation" not in st.session_state:
        st.session_state.conversation = None  
        
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
        
    if "processComplete" not in st.session_state:
        st.session_state.processComplete = None
    
    with st.sidebar:  # 오타 수정: slidebar -> sidebar
        uploaded_files = st.file_uploader("Upload you file", type=['pdf', 'docx'],accept_multiple_files=True)
        google_api_key = st.text_input("Google API Key", key="chatbot_api_key", type="password")
        process = st.button("Process")
        
    if process:
        if not google_api_key:
            st.info("Please add your OpenAI API key to continue.")
            st.stop()
        files_text = get_text(uploaded_files)
        text_chunks = get_text_chunks(files_text)
        vectorstore = get_vectorstore(text_chunks)  
        
        st.session_state.conversation = get_conversation_chain(vectorstore)  
        
        st.session_state.processComplete = True
        
    if 'messages' not in st.session_state:
        st.session_state['messages'] = [{"role": "assistant", "content": "안녕하세요! 주어진 문서에 대해 궁금하신것이 있으면 언제든 물어봐주세요"}]
            
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    StreamlitChatMessageHistory(key="chat messages")
    
    # Chat logic
    if query := st.chat_input("질문을 입력해주세요"):
        st.session_state.messages.append({"role": "user", "content": query})
        
        with st.chat_message("user"):
            st.markdown(query)
            
        with st.chat_message("assistant"):
            chain = st.session_state.conversation  
            
            with st.spinner("Thinking..."):
                result = chain({"question": query})
                st.session_state.chat_history = result['chat_history']
                response = result['answer']
                source_documents = result['source_documents']
                
                st.markdown(response)
                with st.expander("참고 문서 확인"):
                    st.markdown(source_documents[0].metadata['source'], help = source_documents[0].page_content)
                    st.markdown(source_documents[1].metadata['source'], help = source_documents[1].page_content)
                    st.markdown(source_documents[2].metadata['source'], help = source_documents[2].page_content)
                    
            st.session_state.messages.append({"role" : "assistant", "content": response})

def tiktoken_len(text):
    tokenizer = tiktoken.get_encoding("cl100k_base")
    tokens = tokenizer.encode(text)
    return len(tokens)

def get_text(docs):
    
    doc_list = []
    
    for doc in docs:
        file_name = doc.name
        with open(file_name, "wb") as file:
            file.write(doc.getvalue())
            logger.info(f"Uploaded {file_name}")
        if '.pdf' in doc.name:
            loader = PyPDFLoader(file_name)
            documents = loader.load_and_split()
        elif '.docx' in doc.name:
            loader = Docx2txtLoader(file_name)
            documents = loader.load_and_split()
        elif '.pptx' in doc.name:
            loader = UnstructuredPowerPointLoader(file_name)  
            documents = loader.load_and_split()

        doc_list.extend(documents)
    return doc_list

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 900,
        chunk_overlap= 100,
        length_function=tiktoken_len
    )
    chunks = text_splitter.split_documents(text)
    return chunks

def get_vectorstore(text_chunks):
    embeddings = HuggingFaceEmbeddings(
                                        model_name="jhgan/ko-sroberta-multitask",
                                        model_kwargs={'device': 'cpu'},
                                        encode_kwargs={'normalize_embeddings': True}
                                        )
    vectordb = FAISS.from_documents(text_chunks, embeddings)
    
    return vectordb

def get_conversation_chain(vectorstore):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0, google_api_key=st.session_state.chatbot_api_key)
    conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_type = "mmr", verbose=True),
            memory=ConversationBufferMemory(memory_key='chat_history', return_messages=True, output_key='answer'),
            get_chat_history=lambda h: h,
            return_source_documents=True,
            verbose = True
    )
    return conversation_chain

if __name__ == '__main__':
    main()
        
        
        
        
        
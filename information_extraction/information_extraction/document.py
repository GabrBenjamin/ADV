from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as DocumentLangchain
from information_extraction.static_information import StaticInformation
from langchain_openai import ChatOpenAI
import chromadb
from uuid import uuid4
from chromadb.config import Settings

STATIC_INFORMATION = StaticInformation()


class Document:
    def __init__(self):
        self.pages = []
        self.name = ""
        self.summary = ""
        self.file_page_start = None
        self.file_page_finish = None
        self.document_type = ""
        self.reference_date = None
        self.key_information = {
            "Partes_Envolvidas": {"descrição": "Nomes e papéis de todas as partes mencionadas no documento legal. Como resposta, apenas retorne os nomes das partes que encontrar, pessoas físicas ou jurídicas (não inclua como resposta referências indiretas a cargos ou títulos como resposta). E retorne como contexto o uma breve explicação de quem esta parte é.", "conteúdo": {}},
            "Datas_Importantes": {"descrição": f"Datas significativas sobre este documento relevantes para o assunto legal dentro das seguintes categorias:\n{STATIC_INFORMATION.return_text_content('date_types')}\n\n A resposta deve carregar somente a data no formato DD.MM.AAAA - NOME_DA_CATEGORIA_DA_DATA, e no contexto seu racional para a data especificada", "conteúdo": {}},
        }
        
        self.retriever_chain = None
    
    def assign_reference_date(self, model=ChatOpenAI(model="gpt-4o", temperature=0)):
        model=ChatOpenAI(model="gpt-4o", temperature=0)
        dates_extracted = str(self.key_information["Datas_Importantes"]["conteúdo"].items())
        dates_hierarchy = STATIC_INFORMATION.return_text_content('date_types')
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", f"Com base nas datas extraidas do documento:\n {dates_extracted}\n\n ajude o usuário"),
                ("user", f"Dada a hierarquia de datas abaixo em ordem da mais importante para a menos importante, retorne da lista de datas extraidas a data mais importante no seguinte formato: YYYY-MM-DD\n\nHierarquia de datas (em cima a mais importante até em baixo, a menos importante): {dates_hierarchy}.\n\n Responda para mim SOMENTE a data no formato pedido")
            ]
        )
        chain = prompt_template | model | StrOutputParser()
        self.reference_date = chain.invoke({})
        
    def structure_output(self, model, command, outputs):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "Foi dado o comando: {command}. Agora ajude o usuário com o que ele pedir em seguida"),
                ("user", "Depois de rodar o comando multiplas vezes, recebemos os seguintes resultados: {outputs}.\n\n Preciso que retorne todas as informaçoes formatadas como especificado no comando, mas eliminando duplicatas.")
            ]
        )
        chain = prompt_template | model | StrOutputParser()
        response = chain.invoke({"command": command, "outputs": outputs})

        return response
    
    def return_txt_content(self, initial_page=None, final_page=None):
        content = ""
        pages = self.pages[initial_page:final_page]
        for i, page in enumerate(self.pages):
            if page in pages:
                content = content + f"\n\nPage number {i}\n\n" + page.text_content
        return content
    
    def create_retriever_chain(self, model=ChatOpenAI(model="gpt-4o", temperature=0)):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "Dado o contexto abaixo, faça: {command}\n\nContexto:\n{context}"),
                ("user", "Seja direto e preciso."),
            ]
        )
        
        documents = [
            DocumentLangchain(
                page_content=self.return_txt_content(),
            )
        ]
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)
        
        collection_name = str(self.file_page_start) + "_" + str(self.file_page_finish)
        persist_directory = f"./chroma_store"
        print(f"THIS IS THE PERSIST DIRECTORY: {persist_directory}, collection {collection_name}")
        # client = chromadb.Client(settings={"allow_reset": True, "allow_in_memory_db": True})

        # Initialize the Chroma vectorstore in memory
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=OpenAIEmbeddings(),
            collection_name=collection_name,
            persist_directory=persist_directory 
        )
        # ids = [str(id+1) for id in range(len(splits))]
        
        
        # persistent_client = chromadb.PersistentClient(persist_directory)
        # collection = persistent_client.get_or_create_collection(collection_name)
        
        
        # collection.add(ids=ids, documents=splits)

        # vectorstore = Chroma(
        #     client=persistent_client,
        #     collection_name=collection_name,
        #     embedding_function=OpenAIEmbeddings(),
        # )
        # client = chromadb.Client(Settings())
        # tenant = client.get_or_create_tenant("default_tenant")

        # vectorstore = Chroma(
        #     collection_name=collection_name,
        #     embedding_function=OpenAIEmbeddings(),
        #     persist_directory=persist_directory,  # Where to save data locally, remove if not necessary
        # )
        
        # uuids = [str(uuid4()) for _ in range(len(splits))]
        
        # vectorstore.add_documents(documents=splits, ids=uuids)
        
        num_splits = len(splits)
        k_value = min(num_splits, 20)
        
        retriever = MultiQueryRetriever.from_llm(
            retriever=vectorstore.as_retriever(search_kwargs={"k": k_value}), llm=model
            )
        
        # retriever = vectorstore.as_retriever(search_kwargs={"k": k_value})
        self.retriever_chain = ({"context": retriever, "command": RunnablePassthrough()} | prompt_template | model | StrOutputParser())
        
    def summarize(self):
        command = "return a quick summary of the document, and if you find, also provide the name of the current document, as written in the actual document"
        result = self.retrieve_information(command)
        self.summary = result

    def get_name_and_type(self, model=ChatOpenAI(model="gpt-4o", temperature=0)):
        model=ChatOpenAI(model="gpt-4o", temperature=0)
        document_types_display = STATIC_INFORMATION.return_text_content("document_types")
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", f"Com base no resumo de documento abaixo, nomeie o documento e depois forneça o tipo de documento de acordo com os critérios:\n {document_types_display}\n\n A resposta deve estar no formato: Nome do documento: <nome>; Tipo de documento: <tipo de documento>.\n Para a classificação: Como se trata de uma classificação, escolha apenas um tipo de documento da lista provida, usando as descrições de cada documento como critério de classificação. A sua resposta deve ser somente o nome e subnome do tipo do documento, sem descrição"),
                ("user", f"Este é o resumo: {self.summary}")
            ]
        )
        chain = prompt_template | model | StrOutputParser()
        result = chain.invoke({})

        try:
            result = "Nome do documento:" + result.split("Nome do documento:")[1]
            parsed_result = result.split(";")
            name_part = parsed_result[0].replace("Nome do documento:", "").strip()
            type_part = parsed_result[1].replace("Tipo de documento:", "").strip()
            self.name = name_part
            self.document_type = type_part
        except IndexError:
            pass  # Handle parsing errors if necessary

    def gather_key_info(self):
        command_base = (
            "Reúna as informações do tópico solicitado. Pode haver mais de uma resposta.\n"
            "Retorne cada uma no seguinte formato:\n"
            "Conteúdo: <conteúdo>; Contexto: <contexto>\n"
            "Se houver várias respostas, separe-as seguindo esse formato para cada uma. Se não houver repostas ou se todas as informaçoes já foram extraidas, retorne as respostas já obtidas\n"
            "Tópico:\n"
        )
        # Identificar as chaves que ainda não possuem conteúdo extraído
        missing_keys = [(k, v) for k, v in self.key_information.items() if v['conteúdo'] == {}]
        if not missing_keys:
            return  # Pular se não houver chaves faltando
        
        for missing_key, missing_value in missing_keys:
            # Preparar o comando com o nome da chave faltante e a descrição
            command_with_keys = command_base + missing_key + "  " + str(missing_value['descrição'])
            result_information = ""
            result_information = self.retrieve_information(command_with_keys)
            outputs = result_information
            command_with_keys = command_with_keys + f"\n\nestas são as informações já achadas, inclua-as na sua resposta também: \n\n" + result_information
            for _ in range(3):
                
                result_information = self.retrieve_information(command_with_keys)
                outputs = outputs + '\n\n' + result_information
                # print(f"this is the result_information: {result_information}")
                command_with_keys = command_with_keys + result_information
                
            result_information = self.structure_output(ChatOpenAI(model="gpt-4o", temperature=0), str(command_base), str(outputs))
            # Validar se o resultado está no formato esperado
            if 'Conteúdo:' not in result_information or 'Contexto:' not in result_information:
                continue
            # print(f"this is the FINAL result_information: {result_information}")
            # Separar os resultados com base em 'Conteúdo: ' e 'Contexto:'
            result_entries = result_information.split('Conteúdo:')
            # print(f"these are the result_entries: {result_entries}")
            # Processar cada resultado extraído
            for entry in result_entries[1:]:
                try:
                    content_part, context_part = entry.split('Contexto:')
                    extracted_content = content_part.strip()
                    context_description = context_part.strip()
                    
                    # Verificar se já existe uma entrada para o conteúdo extraído
                    if extracted_content not in self.key_information[missing_key]['conteúdo']:
                        # Atualizar o dicionário com o conteúdo extraído e seu contexto
                        self.key_information[missing_key]['conteúdo'][extracted_content.replace(";", "\n")] = context_description
                
                except ValueError:
                    continue
    
    def retrieve_information(self, command):
        if self.retriever_chain is None:
            self.create_retriever_chain(model=ChatOpenAI(model="gpt-4o", temperature=0))
        # print(f"running command: {command}")
        result = self.retriever_chain.invoke(command)
        # context_retrieved = self.retriever_chain['context'].retrieve(command)
        # print(f"Retrieved context: {context_retrieved}")
        # verification_command = result + f"\n\no texto acima é uma resposta ao comando {command} no contexto do documento resumido abaixo:\n\nResumo: {self.summary}\n\n verifique que esta resposta está correta. Caso esteja, retorne apenas VERDADEIRO. Caso contrário, retorne orientações sobre o que fazer para encontrar a resposta correta baseado no erro."
        # verification_result = self.retriever_chain.invoke(verification_command)
        # if "verdadeiro" not in verification_result.lower():
        #     new_command = f"faça o seguinte, seguindo as orientações: {command}\n\n Orientações {verification_result}"
        #     result = self.retriever_chain.invoke(new_command)
                
        return result
    
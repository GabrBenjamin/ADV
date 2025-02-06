from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from pdf2image import convert_from_bytes
from urllib.parse import urlparse
import requests
import io
import os

from concurrent.futures import ThreadPoolExecutor

from information_extraction.static_information import StaticInformation
from information_extraction.page import Page
from information_extraction.document import Document

STATIC_INFORMATION = StaticInformation()

class BruteForceStrategy:
    def __init__(self):
        self.pages = []
        self.info_documents = []
        self.model = ChatOpenAI(model="gpt-4o", temperature=0)
        self.output_parser = StrOutputParser()
        self.concurrent_prompts = 700
        
    def run(self, pdf_file_path):
        self.pages = self.get_pages_from_pdf(pdf_file_path)
        self.process_pages()
        self.create_documents()
        self.process_documents()
        return self.info_documents
    
    def get_pages_from_pdf(self, pdf_file_path, max_number_of_pages=None):
        pdf_file_data = self._create_buffer_from_path_or_url(
            os.environ.get('FIS_ENDPOINT') + pdf_file_path
        )
        images = convert_from_bytes(pdf_file_data.read(), fmt="jpeg")
        if max_number_of_pages:
            images = images[:max_number_of_pages]
        pages = []
        for index, image in enumerate(images):
            page = Page()
            page.set_image(image)  
            page.page_number = index + 1
            pages.append(page)
        return pages
            
    def _create_buffer_from_path_or_url(self, path):
        if self.is_url(path):
            # If it's a URL, download and store in memory
            response = requests.get(path)
            if response.status_code == 200:
                return io.BytesIO(response.content)
            else:
                raise Exception(f"Failed to download file from {path}")
        else:
            # If it's a local file path, read the file into memory
            with open(path, 'rb') as f:
                return io.BytesIO(f.read())

    def is_url(self, path):
        try:
            result = urlparse(path)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False
        
    def process_documents(self):
        """Process each document to extract summaries, names, types, and key information, using multithreading."""
        print(f"processing documents")
        def process_single_document(document):
            document.create_retriever_chain()
            document.summarize()
            document.get_name_and_type(self.model)
            document.gather_key_info()
            document.assign_reference_date(self.model)

        with ThreadPoolExecutor(max_workers=self.concurrent_prompts) as executor:
            futures = [executor.submit(process_single_document, document) for document in self.info_documents]

            for future in futures:
                future.result()
    
    def process_pages(self):
        """Extract text content from each page using the Page class method, with multithreading."""
        with ThreadPoolExecutor(max_workers=self.concurrent_prompts) as executor:
            futures = [executor.submit(page.extract_text_content, self.model, self.output_parser) for page in self.pages]

            for future in futures:
                future.result()
            
    def create_documents(self):
        batch_results = []
        to_batch_send = []
        
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "Você é um advogado especializado em documentos jurídicos. Para fazer bem o que se pede, é necessário focar no texto designado como 'PAGINA ATUAL', e comparar com a 'PAGINA ANTERIOR'. Atente-se aos pontos que podem trazer facilidades: o nome do documento pode estar registrado proximo ao titulo, se este nome divergir nestas duas páginas é possível que sejam dois documentos diferentes."),
                ("user", "Retorne -VERDADEIRO- se a 'PAGINA ATUAL' for o texto que continue o que está sendo dito na 'PAGINA ANTERIOR', e -FALSO- caso a página atual marque o começo de um novo documento \n\n EXEMPLO:\n{example}\n\n Responda tomando o exemplo como base, e responda apenas com -VERDADEIRO- ou -FALSO-\n\nPAGINA ANTERIOR: {before_page}\n\nPAGINA ATUAL: {current_page}"),
            ]
        )
        
        base_chain = prompt_template | self.model | self.output_parser
        
        to_batch_send = []
        for i, page in enumerate(self.pages):
            if i != 0:
                current_page = self.pages[i]
                before_page = self.pages[i - 1]
                example = STATIC_INFORMATION.get_example("next_doc", number_of_examples=1)
                to_batch_send.append({"current_page": current_page.text_content, "before_page": before_page.text_content, "example": example})
        
        batch_results = base_chain.batch(to_batch_send, config={"max_concurrency": 700})
        batch_results = ['First page'] + batch_results  # First page doesn't have a previous page
        
        first_document = True
        current_document = None
        document_index = -1
        for i, (page, batch_result) in enumerate(zip(self.pages, batch_results)):
            if '-falso-' in batch_result.lower() or first_document:
                current_document = Document()
                current_document.pages.append(page)
                current_document.file_page_start = page.page_number
                current_document.file_page_finish = page.page_number
                self.info_documents.append(current_document)
                first_document = False
                document_index += 1
            elif '-verdadeiro-' in batch_result.lower():
                current_document.pages.append(page)
                current_document.file_page_finish = page.page_number
                self.info_documents[document_index] = current_document

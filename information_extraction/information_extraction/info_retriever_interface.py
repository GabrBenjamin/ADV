import os
from information_extraction.BF_strategy_27_09_2024.brute_force_strategy_27_09_2024 import BruteForceStrategy


class InfoRetrieverInterface(BruteForceStrategy):
    def __init__(self):
        super().__init__()

    def extract_info(self, pdf_file_path):
        info_documents = self.run(pdf_file_path)
        print(f"finished information extraction")
        return info_documents
    
    def log_results(self):
        # For the next versions, insert here the logic to log the results and other stuff
        pass

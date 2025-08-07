import concurrent.futures
from config.config_manager import ConfigManager

def process_files_parallel(file_list, processing_function):
    config = ConfigManager.get_instance()
    max_workers = config.getint('FINGERPRINT', 'parallel_workers')
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(processing_function, file): file 
            for file in file_list
        }
        
        results = {}
        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            try:
                results[file] = future.result()
            except Exception as e:
                results[file] = {'error': str(e)}
                
        return results

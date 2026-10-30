import pandas as pd 

def pandas_preview(filepath):
    if filepath.split(".")[-1] == "csv":
        df = pd.read_csv(filepath)
        
    elif filepath.split(".")[-1] == "parquet":
        df = pd.read_parquet(filepath)
        
    elif filepath.split(".")[-1] == "json":
        try:
            try:
                df = pd.read_json(filepath, lines=True)
            except Exception as e:
                print(f"Exception is {e}")
                df = pd.read_json(filepath)
        except:
            pass
        
    elif filepath.split(".")[-1] == "xlsx" or filepath.split(".")[-1] == "xls":
        df = pd.read_excel(filepath)
        
    return df.head()
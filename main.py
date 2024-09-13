import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from script import process_cin_batch

def read_cin_from_excel(file_path):
    df = pd.read_excel(file_path)
    return df['CIN'].head(10).tolist()

def process_all_cins(cins, batch_size=10):
    all_data = pd.DataFrame()
    with ProcessPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(0, len(cins), batch_size):
            batch = cins[i:i+batch_size]
            futures.append(executor.submit(process_cin_batch, batch))
        
        for future in as_completed(futures):
            batch_data = future.result()
            all_data = pd.concat([all_data, batch_data], ignore_index=True)
    
    return all_data

def main():
    input_file = "input_file.xlsx"
    cin_values = read_cin_from_excel(input_file)
    
    all_data = process_all_cins(cin_values)
    
    output_file = "output.xlsx"
    all_data.to_excel(output_file, index=False)
    print(f"All data saved to {output_file}")

if __name__ == "__main__":
    main()
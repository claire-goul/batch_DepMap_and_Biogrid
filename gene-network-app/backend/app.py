# app.py with updated BioGrid processing
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import io
import requests
from io import BytesIO
importpathlib

app = FastAPI()

# Initialize global variables
links_filtered = None
biogrid_df = None

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_correlations_edgelist(genes, links_filtered, threshold, corrpos, num):
    links_filtered_newfinal = pd.merge(links_filtered, genes, on=['Gene'])
    if corrpos:
        links_filtered_newfinal = links_filtered_newfinal[links_filtered_newfinal['corrscore'] >= threshold]
        grouped = links_filtered_newfinal.groupby('Gene')
        toplargestdf = pd.DataFrame()
        for var1, subdict in grouped:
            sub = subdict[subdict['corrscore'] > 0]
            sublargest = sub.nlargest(n=num, columns='corrscore')
            toplargestdf = pd.concat([toplargestdf, sublargest])
    else:
        links_filtered_newfinal = links_filtered_newfinal[links_filtered_newfinal['corrscore'] <= threshold]
        grouped = links_filtered_newfinal.groupby('Gene')
        toplargestdf = pd.DataFrame()
        for var1, subdict in grouped:
            sub = subdict[subdict['corrscore'] < 0]
            sublargest = sub.nlargest(n=num, columns='corrscore')
            toplargestdf = pd.concat([toplargestdf, sublargest])
    corr = (toplargestdf.reset_index()).drop(['index'], axis=1)
    return corr

def get_biogrid_edgelist(genes, bg, filters, numcitations):
    """
    Updated function to handle mitab format
    Mitab columns of interest:
    - ID Interactor A
    - ID Interactor B
    - Alt IDs Interactor A
    - Alt IDs Interactor B
    - Alias IDs Interactor A
    - Alias IDs Interactor B
    - Interaction Detection Method
    - Publication Identifier(s)
    """
    print("Processing BioGrid data...")
    
    # Function to extract gene symbols from ID fields
    def extract_gene_symbols(row, interactor='A'):
        symbols = set()
        
        # Check official IDs
        id_col = f'Alt. ID Interactor {interactor}'
        if pd.notnull(row[id_col]):
            for id_entry in str(row[id_col]).split('|'):
                if 'hgnc:' in id_entry.lower():
                    gene = id_entry.split('(')[0].split(':')[-1]
                    symbols.add(gene)
        
        # Check aliases
        alias_col = f'Alias(es) interactor {interactor}'
        if pd.notnull(row[alias_col]):
            for alias in str(row[alias_col]).split('|'):
                if 'hgnc:' in alias.lower():
                    gene = alias.split('(')[0].split(':')[-1]
                    symbols.add(gene)
        
        return list(symbols)

    # Create edge list
    edges = []
    genes_list = set(genes['Gene'].str.upper())
    
    print(f"Processing {len(bg)} interactions...")
    
    # Process each interaction
    for _, row in bg.iterrows():
        genes_a = extract_gene_symbols(row, 'A')
        genes_b = extract_gene_symbols(row, 'B')
        
        # Check if any gene from A matches our genes of interest
        for gene_a in genes_a:
            if gene_a.upper() in genes_list:
                for gene_b in genes_b:
                    if gene_b.upper() != gene_a.upper():  # Avoid self-loops
                        edges.append((gene_a, gene_b))
        
        # Check if any gene from B matches our genes of interest
        for gene_b in genes_b:
            if gene_b.upper() in genes_list:
                for gene_a in genes_a:
                    if gene_a.upper() != gene_b.upper():  # Avoid self-loops
                        edges.append((gene_b, gene_a))
    
    print(f"Found {len(edges)} potential interactions")
    
    # Convert to DataFrame
    if edges:
        edgelist_biogrid = pd.DataFrame(edges, columns=['Gene', 'Gene1'])
        
        # Count occurrences to filter by citation count
        edge_counts = edgelist_biogrid.groupby(['Gene', 'Gene1']).size().reset_index(name='count')
        edge_counts = edge_counts[edge_counts['count'] >= numcitations]
        
        # Create final edge list
        edgelist_biogrid_final = edge_counts.drop(columns=['count'])
        edgelist_biogrid_final['bg'] = 'yes'
        
        print(f"Final interaction count: {len(edgelist_biogrid_final)}")
        return edgelist_biogrid_final
    else:
        return pd.DataFrame(columns=['Gene', 'Gene1', 'bg'])

import subprocess



@app.on_event("startup")
async def startup_event():
    """Load the large files when the server starts"""
    global links_filtered, biogrid_df
    
    try:
        # Print current working directory and list files
        current_dir = os.getcwd()
        print(f"Current working directory: {current_dir}")
        print("Files in current directory:")
        print(os.listdir(current_dir))
        
        # Try to read links file
        links_path = os.path.join(current_dir, 'data', 'links_achilles.xlsx')
        print(f"Attempting to read links file from: {links_path}")
        
        # Check if file exists and print its size
        if os.path.exists(links_path):
            file_size = os.path.getsize(links_path)
            print(f"Links file exists, size: {file_size} bytes")
            
            # Try reading with different engines
            try:
                links_filtered = pd.read_excel(
                    links_path,
                    engine='openpyxl',
                    storage_options={'engine': 'openpyxl'}
                )
            except Exception as e:
                print(f"Failed with openpyxl: {str(e)}")
                try:
                    links_filtered = pd.read_excel(
                        links_path,
                        engine='xlrd'
                    )
                except Exception as e:
                    print(f"Failed with xlrd: {str(e)}")
                    # Try reading as CSV as last resort
                    links_filtered = pd.read_csv(links_path)
                    
            print(f"Links file loaded successfully: {len(links_filtered)} rows")
        else:
            print(f"Links file not found at {links_path}")
            print("Contents of data directory:")
            data_dir = os.path.join(current_dir, 'data')
            if os.path.exists(data_dir):
                print(os.listdir(data_dir))
            else:
                print("Data directory not found")
            raise FileNotFoundError(f"Links file not found at {links_path}")

        # Similar process for BioGrid file
        biogrid_path = os.path.join(current_dir, 'data', 'biogrid_human_processed_4_4_212.xlsx')
        print(f"Attempting to read BioGrid file from: {biogrid_path}")
        
        if os.path.exists(biogrid_path):
            file_size = os.path.getsize(biogrid_path)
            print(f"BioGrid file exists, size: {file_size} bytes")
            
            try:
                biogrid_df = pd.read_excel(
                    biogrid_path,
                    engine='openpyxl',
                    storage_options={'engine': 'openpyxl'}
                )
            except Exception as e:
                print(f"Failed with openpyxl: {str(e)}")
                try:
                    biogrid_df = pd.read_excel(
                        biogrid_path,
                        engine='xlrd'
                    )
                except Exception as e:
                    print(f"Failed with xlrd: {str(e)}")
                    # Try reading as CSV as last resort
                    biogrid_df = pd.read_csv(biogrid_path)
                    
            print(f"BioGrid file loaded successfully: {len(biogrid_df)} rows")
        else:
            print(f"BioGrid file not found at {biogrid_path}")
            raise FileNotFoundError(f"BioGrid file not found at {biogrid_path}")

    except Exception as e:
        print(f"Error loading files: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise e

@app.get("/")
async def root():
    return {"message": "Gene Network API is running"}

@app.get("/status/")
async def get_status():
    """Get status of loaded files and additional information"""
    try:
        return {
            "links_file_loaded": links_filtered is not None,
            "biogrid_file_loaded": biogrid_df is not None,
            "links_file_rows": len(links_filtered) if links_filtered is not None else 0,
            "biogrid_file_rows": len(biogrid_df) if biogrid_df is not None else 0,
            "server_status": "running"
        }
    except Exception as e:
        return {
            "links_file_loaded": False,
            "biogrid_file_loaded": False,
            "links_file_rows": 0,
            "biogrid_file_rows": 0,
            "server_status": "running",
            "error": str(e)
        }

@app.post("/upload/")
async def process_network(genes_file: UploadFile = File(...)):
    global links_filtered, biogrid_df
    
    # Check if required files are loaded
    if links_filtered is None or biogrid_df is None:
        raise HTTPException(
            status_code=503, 
            detail="Server is not ready. Required files are not loaded."
        )
    
    try:
        # Read the genes file
        genes_df = pd.read_excel(io.BytesIO(await genes_file.read()), engine='openpyxl')

        # Process using pre-loaded data
        corr = get_correlations_edgelist(
            genes=genes_df,
            links_filtered=links_filtered,
            threshold=0.2,
            corrpos=True,
            num=3
        )

        edgelist_biogrid = get_biogrid_edgelist(
            genes=genes_df,
            bg=biogrid_df,
            filters=['psi-mi:"MI:0915"(physical association)'],
            numcitations=2
        )

        # Combine results
        corrwithbgforcorr = pd.merge(
            corr, 
            edgelist_biogrid,  
            how='left', 
            left_on=['Gene','Gene1'], 
            right_on=['Gene','Gene1']
        )

        # Convert to network format
        network_data = {
            "nodes": [],
            "edges": []
        }

        # Create unique node list
        unique_nodes = set()
        for _, row in corrwithbgforcorr.iterrows():
            unique_nodes.add(row['Gene'])
            unique_nodes.add(row['Gene1'])

        # Add nodes
        genes_list = set(genes_df['Gene'].tolist())
        network_data["nodes"] = [
            {"id": node, "isInterest": node in genes_list}
            for node in unique_nodes
        ]

        # Add edges
        network_data["edges"] = [
            {
                "source": row['Gene'],
                "target": row['Gene1'],
                "value": float(row['corrscore']) if 'corrscore' in row else 0,
                "isBiogrid": row.get('bg') == 'yes'
            }
            for _, row in corrwithbgforcorr.iterrows()
        ]

        return network_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

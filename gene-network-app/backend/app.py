from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
import io
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://batchnetwork.netlify.app").split(',')


# Initialize global variables
links_filtered = None
biogrid_df = None

# CORS configuration - make sure this is BEFORE any routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://batchnetwork.netlify.app"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
    max_age=600,
)
    
def get_correlations_edgelist(genes, links_filtered, threshold, corrpos, num):
    logger.info("Starting correlation analysis...")
    
    # Convert genes list to set for faster lookup
    genes_set = set(genes['Gene'])
    
    # Filter links first to reduce merge size
    links_subset = links_filtered[links_filtered['Gene'].isin(genes_set)]
    
    if corrpos:
        # Filter by threshold first
        links_subset = links_subset[links_subset['corrscore'] >= threshold]
    else:
        links_subset = links_subset[links_subset['corrscore'] <= threshold]
    
    # Group and process
    result_dfs = []
    for gene in genes_set:
        gene_data = links_subset[links_subset['Gene'] == gene]
        if corrpos:
            gene_data = gene_data[gene_data['corrscore'] > 0]
        else:
            gene_data = gene_data[gene_data['corrscore'] < 0]
        
        result_dfs.append(gene_data.nlargest(n=num, columns='corrscore'))
    
    # Combine results
    corr = pd.concat(result_dfs, ignore_index=True)
    
    logger.info(f"Correlation analysis complete. Found {len(corr)} correlations.")
    return corr

def get_biogrid_edgelist(genes, bg, filters, numcitations):
    logger.info("Processing BioGrid data...")
    
    # Convert genes list to set for faster lookup
    genes_list = set(genes['Gene'].str.upper())
    
    # Pre-process gene symbols for all rows at once
    def extract_gene_symbols_batch(df, interactor='A'):
        alias_col = f'Aliases Interactor {interactor}'
        alt_id_col = f'Alt IDs Interactor {interactor}'
        
        symbols = []
        for _, row in df.iterrows():
            row_symbols = set()
            
            if pd.notnull(row[alias_col]):
                aliases = str(row[alias_col]).split('|')
                for alias in aliases:
                    if 'entrez gene/locuslink:' in alias.lower():
                        gene = alias.split('(')[0].split(':')[-1].strip()
                        row_symbols.add(gene)
            
            if pd.notnull(row[alt_id_col]):
                alt_ids = str(row[alt_id_col]).split('|')
                for alt_id in alt_ids:
                    if 'entrez gene/locuslink:' in alt_id.lower():
                        gene = alt_id.split('|')[0].split(':')[-1].strip()
                        row_symbols.add(gene)
            
            symbols.append(list(row_symbols))
        
        return symbols
    
    # Process both interactors at once
    logger.info("Extracting gene symbols...")
    genes_a = extract_gene_symbols_batch(bg, 'A')
    genes_b = extract_gene_symbols_batch(bg, 'B')
    
    # Create edges more efficiently
    edges = set()  # Use set for faster duplicate removal
    logger.info("Creating edges...")
    
    for i in range(len(bg)):
        for gene_a in genes_a[i]:
            gene_a_upper = gene_a.upper()
            if gene_a_upper in genes_list:
                for gene_b in genes_b[i]:
                    gene_b_upper = gene_b.upper()
                    if gene_b_upper != gene_a_upper:
                        edges.add((gene_a, gene_b))
        
        for gene_b in genes_b[i]:
            gene_b_upper = gene_b.upper()
            if gene_b_upper in genes_list:
                for gene_a in genes_a[i]:
                    gene_a_upper = gene_a.upper()
                    if gene_a_upper != gene_b_upper:
                        edges.add((gene_b, gene_a))
    
    logger.info(f"Found {len(edges)} potential interactions")
    
    # Convert to DataFrame
    if edges:
        edgelist_biogrid = pd.DataFrame(list(edges), columns=['Gene', 'Gene1'])
        
        # Count occurrences to filter by citation count
        edge_counts = edgelist_biogrid.groupby(['Gene', 'Gene1']).size().reset_index(name='count')
        edge_counts = edge_counts[edge_counts['count'] >= numcitations]
        
        # Create final edge list
        edgelist_biogrid_final = edge_counts[['Gene', 'Gene1']].copy()
        edgelist_biogrid_final['bg'] = 'yes'
        
        logger.info(f"Final interaction count: {len(edgelist_biogrid_final)}")
        return edgelist_biogrid_final
    else:
        return pd.DataFrame(columns=['Gene', 'Gene1', 'bg'])
        

@app.on_event("startup")
async def startup_event():
    """Load the large files when the server starts"""
    global links_filtered, biogrid_df
    
    try:
        # Load links file
        logger.info("Loading links file...")
        links_path = os.path.join('data', 'links_achilles.xlsx')
        if not os.path.exists(links_path):
            logger.error(f"Links file not found at {links_path}")
            raise FileNotFoundError(f"Links file not found at {links_path}")
        
        # Check file size
        file_size = os.path.getsize(links_path)
        logger.info(f"Links file size: {file_size} bytes")
        if file_size == 0:
            raise ValueError("Links file is empty")
            
        # Load with error checking
        try:
            links_filtered = pd.read_excel(
                links_path, 
                engine='openpyxl'
            )
            if links_filtered.empty:
                raise ValueError("Links file loaded but contains no data")
            logger.info(f"Links file loaded successfully: {len(links_filtered)} rows")
            logger.info(f"Links file columns: {list(links_filtered.columns)}")
        except Exception as e:
            logger.error(f"Error reading links file: {str(e)}")
            raise

        # Load BioGrid file
        logger.info("Loading BioGrid file...")
        biogrid_path = os.path.join('data', 'biogrid_human_processed_4_4_212.xlsx')
        if not os.path.exists(biogrid_path):
            logger.error(f"BioGrid file not found at {biogrid_path}")
            raise FileNotFoundError(f"BioGrid file not found at {biogrid_path}")
        
        # Check file size
        file_size = os.path.getsize(biogrid_path)
        logger.info(f"BioGrid file size: {file_size} bytes")
        if file_size == 0:
            raise ValueError("BioGrid file is empty")
            
        # Load with error checking
        try:
            biogrid_df = pd.read_excel(
                biogrid_path,
                engine='openpyxl'
            )
            if biogrid_df.empty:
                raise ValueError("BioGrid file loaded but contains no data")
            logger.info(f"BioGrid file loaded successfully: {len(biogrid_df)} rows")
            logger.info(f"BioGrid file columns: {list(biogrid_df.columns)}")
        except Exception as e:
            logger.error(f"Error reading BioGrid file: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Error loading files: {str(e)}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Files in current directory: {os.listdir()}")
        if os.path.exists('data'):
            logger.error(f"Files in data directory: {os.listdir('data')}")
        else:
            logger.error("Data directory not found")
        raise e

@app.get("/")
async def root():
    return {"message": "Gene Network API is running"}

@app.get("/status/")
async def get_status():
    """Get status of loaded files and additional information"""
    return {
        "links_file_loaded": links_filtered is not None,
        "biogrid_file_loaded": biogrid_df is not None,
        "links_file_rows": len(links_filtered) if links_filtered is not None else 0,
        "biogrid_file_rows": len(biogrid_df) if biogrid_df is not None else 0,
        "server_status": "running"
    }
    
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"""
    --- Incoming Request ---
    Method: {request.method}
    URL: {request.url}
    Headers: {request.headers}
    """)
    
    response = await call_next(request)
    
    logger.info(f"""
    --- Outgoing Response ---
    Status: {response.status_code}
    Headers: {response.headers}
    """)
    
    return response
    
@app.post("/upload/")
async def process_network(genes_file: UploadFile = File(...)):
    global links_filtered, biogrid_df
    logger.info("Upload endpoint called")
    logger.info(f"Request headers: {genes_file.headers}")
    
    # Check if required files are loaded
    if links_filtered is None or biogrid_df is None:
        raise HTTPException(
            status_code=503, 
            detail="Server is not ready. Required files are not loaded."
        )
    
    try:
        logger.info(f"Processing uploaded file: {genes_file.filename}")
        
        # Read the genes file
        genes_df = pd.read_excel(io.BytesIO(await genes_file.read()), engine='openpyxl')
        logger.info(f"Uploaded file contains {len(genes_df)} genes")

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
        logger.info(f"Combined results contain {len(corrwithbgforcorr)} interactions")

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

        logger.info(f"Network contains {len(network_data['nodes'])} nodes and {len(network_data['edges'])} edges")
        return network_data

    except Exception as e:
        logger.error(f"Error processing network: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
import io
import os
import logging
import json

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

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://batchnetwork.netlify.app"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
    max_age=600,
)

def get_correlations_edgelist(genes, links_filtered, threshold, corrpos, num):
    logger.info(f"Starting correlation analysis with parameters: threshold={threshold}, corrpos={corrpos}, num={num}")
    
    # Convert genes list to set for faster lookup
    genes_set = set(genes['Gene'])
    logger.info(f"Processing {len(genes_set)} genes")
    
    # Filter links first to reduce merge size
    links_subset = links_filtered[links_filtered['Gene'].isin(genes_set)]
    logger.info(f"Initial links subset size: {len(links_subset)}")
    
    if corrpos:
        links_subset = links_subset[links_subset['corrscore'] >= threshold]
    else:
        links_subset = links_subset[links_subset['corrscore'] <= threshold]
    
    # Group and process
    result_dfs = []
    for gene in genes_set:
        gene_data = links_subset[links_subset['Gene'] == gene]
        if len(gene_data) > 0:
            if corrpos:
                gene_data = gene_data[gene_data['corrscore'] > 0]
            else:
                gene_data = gene_data[gene_data['corrscore'] < 0]
            
            result_dfs.append(gene_data.nlargest(n=num, columns='corrscore'))
    
    # Combine results
    corr = pd.concat(result_dfs, ignore_index=True)
    logger.info(f"Final correlation results: {len(corr)} pairs")
    logger.info(f"Sample correlations:\n{corr.head()}")
    return corr

def get_biogrid_edgelist(genes, bg, filters, numcitations):
    logger.info(f"Processing BioGrid data with parameters: numcitations={numcitations}")
    
    # Convert genes list to set for faster lookup
    genes_list = set(genes['Gene'].str.upper())
    logger.info(f"Processing {len(genes_list)} genes")
    
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
    
    logger.info("Extracting gene symbols...")
    genes_a = extract_gene_symbols_batch(bg, 'A')
    genes_b = extract_gene_symbols_batch(bg, 'B')
    
    edges = set()
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
    
    if edges:
        edgelist_biogrid = pd.DataFrame(list(edges), columns=['Gene', 'Gene1'])
        
        # Count occurrences to filter by citation count
        edge_counts = edgelist_biogrid.groupby(['Gene', 'Gene1']).size().reset_index(name='count')
        edge_counts = edge_counts[edge_counts['count'] >= numcitations]
        
        # Create final edge list with explicit boolean for bg column
        edgelist_biogrid_final = edge_counts[['Gene', 'Gene1']].copy()
        edgelist_biogrid_final['bg'] = True  # Using boolean True
        
        logger.info(f"Final BioGrid interactions: {len(edgelist_biogrid_final)}")
        logger.info(f"Sample BioGrid edges:\n{edgelist_biogrid_final.head()}")
        return edgelist_biogrid_final
    else:
        logger.warning("No BioGrid edges found")
        return pd.DataFrame(columns=['Gene', 'Gene1', 'bg'])

@app.post("/upload/")
async def process_network(genes_file: UploadFile = File(...)):
    global links_filtered, biogrid_df
    logger.info("Upload endpoint called")
    
    try:
        # Read the genes file
        genes_df = pd.read_excel(io.BytesIO(await genes_file.read()), engine='openpyxl')
        logger.info(f"Processing {len(genes_df)} genes")
        logger.info(f"Sample genes:\n{genes_df.head()}")

        # Get correlations
        corr = get_correlations_edgelist(
            genes=genes_df,
            links_filtered=links_filtered,
            threshold=0.2,
            corrpos=True,
            num=3
        )
        # Add bg column to correlations with False
        corr['bg'] = False
        logger.info(f"Correlation edges shape: {corr.shape}")
        logger.info(f"Sample correlations:\n{corr.head()}")

        # Get BioGrid edges
        edgelist_biogrid = get_biogrid_edgelist(
            genes=genes_df,
            bg=biogrid_df,
            filters=['psi-mi:"MI:0915"(physical association)'],
            numcitations=2
        )
        logger.info(f"BioGrid edges shape: {edgelist_biogrid.shape}")
        logger.info(f"Sample BioGrid edges:\n{edgelist_biogrid.head()}")

        # Combine edges from both sources
        all_edges = pd.concat([corr, edgelist_biogrid], ignore_index=True)
        logger.info(f"Combined edges shape: {all_edges.shape}")
        logger.info(f"Sample combined edges:\n{all_edges.head()}")
        
        # Create unique node list
        unique_nodes = set(all_edges['Gene'].unique()) | set(all_edges['Gene1'].unique())
        logger.info(f"Found {len(unique_nodes)} unique nodes")

        # Create network data
        network_data = {
            "nodes": [{"id": node, "isInterest": node in genes_df['Gene'].tolist()} for node in unique_nodes],
            "edges": []
        }

        # Create edges with explicit type handling
        for _, row in all_edges.iterrows():
            edge = {
                "source": row['Gene'],
                "target": row['Gene1'],
                "value": float(row['corrscore']) if pd.notnull(row.get('corrscore')) else 0,
                "isBiogrid": bool(row['bg']) if pd.notnull(row.get('bg')) else False
            }
            network_data["edges"].append(edge)

        # Log final statistics
        biogrid_count = sum(1 for e in network_data["edges"] if e["isBiogrid"])
        logger.info(f"Network statistics:")
        logger.info(f"Total nodes: {len(network_data['nodes'])}")
        logger.info(f"Total edges: {len(network_data['edges'])}")
        logger.info(f"BioGrid edges: {biogrid_count}")
        
        # Log sample edges for verification
        logger.info("Sample network edges:")
        for edge in network_data['edges'][:5]:
            logger.info(json.dumps(edge))

        return network_data

    except Exception as e:
        logger.error(f"Error processing network: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        file_size = os.path.getsize(links_path)
        logger.info(f"Links file size: {file_size} bytes")
        
        links_filtered = pd.read_excel(links_path, engine='openpyxl')
        logger.info(f"Links file loaded: {len(links_filtered)} rows")
        logger.info(f"Links file columns: {links_filtered.columns.tolist()}")

        # Load BioGrid file
        logger.info("Loading BioGrid file...")
        biogrid_path = os.path.join('data', 'biogrid_human_processed_4_4_212.xlsx')
        if not os.path.exists(biogrid_path):
            logger.error(f"BioGrid file not found at {biogrid_path}")
            raise FileNotFoundError(f"BioGrid file not found at {biogrid_path}")
        
        file_size = os.path.getsize(biogrid_path)
        logger.info(f"BioGrid file size: {file_size} bytes")
        
        biogrid_df = pd.read_excel(biogrid_path, engine='openpyxl')
        logger.info(f"BioGrid file loaded: {len(biogrid_df)} rows")
        logger.info(f"BioGrid file columns: {biogrid_df.columns.tolist()}")

    except Exception as e:
        logger.error(f"Error loading files: {str(e)}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Files in current directory: {os.listdir()}")
        if os.path.exists('data'):
            logger.error(f"Files in data directory: {os.listdir('data')}")
        else:
            logger.error("Data directory not found")
        raise e
